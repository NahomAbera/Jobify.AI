import os
import pickle
import base64
import email
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def authenticate_gmail():
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] 
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('path', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service


def get_emails(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=10).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
    else:
        print("Messages:")
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            payload = msg['payload']
            headers = payload['headers']
            subject = None
            sender = None
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                if header['name'] == 'From':
                    sender = header['value']

            parts = payload.get('parts', [])
            body = None
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            print(f"Subject: {subject}")
            print(f"From: {sender}")
            print(f"Body: {body}\n")


def process_email(mime_msg):
    subject = mime_msg['subject']
    sender = mime_msg['from']

    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/plain':
                text = part.get_payload(decode=True).decode('utf-8')
                break
    else:
        text = mime_msg.get_payload(decode=True).decode('utf-8')
    print(f"Subject: {subject}")
    print(f"From: {sender}")
    print(f"Body: {text}\n")


def main():
    service = authenticate_gmail()
    get_emails(service)

if __name__ == '__main__':
    main()