# Meeting Summarizer

Meeting Summarizer is a web application that helps users effortlessly summarize meetings, manage action items, and streamline post-meeting tasks. It uses AI-powered summarization, speech-to-text transcription, and integrates with Google services for task management.

## Features

- Transcribe audio files (MP3) to text
- Summarize meeting transcripts
- Extract and manage action items
- Filter action items by assignee
- Integrate with Google Calendar for setting reminders
- Generate and send follow-up emails
- Google Sign-In integration

## Technologies Used

- Backend: Python, Flask
- Frontend: HTML, CSS, JavaScript
- AI: Julep API (GPT-4)
- Speech Recognition: SpeechRecognition library
- Google APIs: Calendar, Gmail, OAuth

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/meeting-summarizer.git
   cd meeting-summarizer
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root and add the following:
   ```
   JULEP_API_KEY=your_julep_api_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

5. Set up Google OAuth:
   - Go to the Google Cloud Console and create a new project
   - Enable the Google Calendar API and Gmail API
   - Create OAuth 2.0 credentials (Web application)
   - Download the client configuration and save it as `credentials.json` in the project root

6. Run the application:
   ```
   python app.py
   ```

## Usage

1. Open a web browser and go to `http://localhost:5000`
2. Click on "Start Summarizing" to begin
3. Sign in with your Google account
4. Upload an audio file or enter a transcript manually
5. Click "Summarize" to generate a summary and action items
6. Use the action buttons to manage tasks:
   - "Send Email" to draft a follow-up email
   - "Set Reminder" to add the task to Google Calendar
   - "Copy" to copy the task details to clipboard
7. Filter action items by assignee name using the input field

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
