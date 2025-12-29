import time
import yaml
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from julep import Julep
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import os
from google.oauth2 import id_token
from google.auth.transport import requests
import speech_recognition as sr
from pydub import AudioSegment
import io
from io import BytesIO
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'Software0923!'  # Replace with a secure random string

# Load environment variables
load_dotenv()

# Initialize Julep client with API key from environment variable
client = Julep(api_key=os.getenv("JULEP_API_KEY"))

# Create the agent once at the start
try:
    agent = client.agents.create(
        name="Meeting Summarizer",
        model="gpt-4o",
        about="You summarize meetings and extract key action items."
    )
    print("Agent created successfully.")
except Exception as e:
    print(f"Error creating agent: {str(e)}")
    agent = None

SCOPES = ['https://www.googleapis.com/auth/keep']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/summarizer')
def summarizer():
    return render_template('summarizer.html')

@app.route('/summarize', methods=['POST'])
def summarize_meeting():
    if agent is None:
        return jsonify({'error': 'Agent not created'}), 500

    data = request.json
    transcript = data.get('transcript')

    if not transcript:
        return jsonify({'error': 'No transcript provided'}), 400

    # Escape and format the transcript for YAML
    escaped_transcript = transcript.replace('"', '\\"').replace('\n', '\\n')

    # Create a task for the agent
    task_yaml = f"""
    name: Meeting Summarizer Task
    description: Summarize a meeting transcript and generate action items.

    tools: []

    main:
      - prompt:
          - role: system
            content: You are {{agent.name}}. {{agent.about}}
          - role: user
            content: >
              Here is the transcript of a meeting: "{escaped_transcript}"

              Please summarize the key points and generate action items.
              For each action item, include the assignee's name and a due date.
              Return your output in the following structure:

              ```yaml
              summary: "<string>"
              action_items:
              - task: "<string>"
                assignee: "<string>"
                due_date: "<YYYY-MM-DD>"
              ```
        unwrap: true

      - evaluate:
          result: load_yaml(_.split('```yaml')[1].split('```')[0].strip())
    """

    # Ensure all indentation is using spaces, not tabs
    task_yaml = task_yaml.replace('\t', '    ')

    try:
        task = client.tasks.create(
            agent_id=agent.id,
            **yaml.safe_load(task_yaml)
        )
        print("Task created successfully.")
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {str(e)}")
        return jsonify({'error': f'YAML parsing error: {str(e)}'}), 500
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        return jsonify({'error': f'Error creating task: {str(e)}'}), 500

    # Execute the task
    try:
        execution = client.executions.create(
            task_id=task.id,
            input={"transcript": transcript}
        )
        print("Execution started successfully.")
    except Exception as e:
        print(f"Error during execution creation: {str(e)}")
        return jsonify({'error': f'Error during execution creation: {str(e)}'}), 500

    # Wait for the result
    while True:
        try:
            result = client.executions.get(execution.id)
            print(f"Execution status: {result.status}")
            if result.status in ['succeeded', 'failed']:
                break
            time.sleep(1)
        except Exception as e:
            print(f"Error retrieving execution result: {str(e)}")
            return jsonify({'error': f'Error retrieving execution result: {str(e)}'}), 500

    # Return the result
    if result.status == "succeeded":
        print("Execution succeeded.")
        print(f"Result output: {result.output}")
        
        # Process action items
        action_items = result.output['result']['action_items']
        for item in action_items:
            try:
                add_to_calendar(item['assignee'], item['task'], item['due_date'])
                send_email(item['assignee'], item['task'], item['due_date'])
            except Exception as e:
                print(f"Error processing action item: {str(e)}")

        return jsonify({
            'summary': result.output['result']['summary'],
            'action_items': action_items
        })
    else:
        print(f"Execution failed: {result.error}")
        return jsonify({'error': result.error}), 500

def add_to_calendar(assignee, task, due_date):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar'])
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = Flow.from_client_secrets_file(
                'credentials.json',
                ['https://www.googleapis.com/auth/calendar']
            )
            flow.run_local_server(port=0)
            creds = flow.credentials

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': task,
            'description': f'Assigned to: {assignee}',
            'start': {
                'date': due_date,
            },
            'end': {
                'date': due_date,
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
    except Exception as e:
        print(f"Error creating calendar event: {str(e)}")

def send_email(assignee, task, due_date):
    sender_email = "your_email@example.com"
    sender_password = "your_email_password"
    receiver_email = f"{assignee.lower()}@yourcompany.com"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"New Task Assignment: {task}"

    body = f"""
    Dear {assignee},

    You have been assigned a new task:

    Task: {task}
    Due Date: {due_date}

    Please complete this task by the due date.

    Best regards,
    Meeting Summarizer Bot
    """

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Email sent to {assignee}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

@app.route('/generate_email', methods=['POST'])
def generate_email():
    data = request.json
    task = data.get('task')
    assignee = data.get('assignee')
    due_date = data.get('due_date')

    if not all([task, assignee, due_date]):
        return jsonify({'error': 'Missing required data'}), 400

    subject = f"{task}"
    body = f"""
Dear {assignee},

I hope this email finds you well. I wanted to follow up on an action item from our recent meeting:

{task}

Due Date: {due_date}

Please let me know if you need any additional information or resources to complete this task. I'm here to help if you have any questions.

Best regards,
Meeting Summarizer
"""

    return jsonify({'subject': subject, 'body': body})

@app.route('/verify_google_token', methods=['POST'])
def verify_google_token():
    token = request.json['token']
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), '1023475948258-9adaetccag88i38dci37031g4r708rt5.apps.googleusercontent.com')
        userid = idinfo['sub']
        session['user_id'] = userid
        session['user_email'] = idinfo['email']
        return jsonify({'success': True, 'userid': userid, 'email': idinfo['email']}), 200
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 400

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if audio_file:
        # Read the audio file into memory
        audio_data = audio_file.read()
        
        # Use speech recognition
        recognizer = sr.Recognizer()
        
        try:
            # Convert the audio data to an AudioFile object
            with sr.AudioFile(BytesIO(audio_data)) as source:
                audio = recognizer.record(source)
            
            # Perform the transcription
            transcript = recognizer.recognize_google(audio)
            return jsonify({'transcript': transcript})
        except sr.UnknownValueError:
            return jsonify({'error': 'Speech recognition could not understand the audio'}), 400
        except sr.RequestError as e:
            return jsonify({'error': f'Could not request results from speech recognition service; {e}'}), 500
    
    return jsonify({'error': 'Unknown error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True)
