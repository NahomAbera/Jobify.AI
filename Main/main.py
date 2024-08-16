import openai
import base64
import email
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import firebase_admin
from firebase_admin import credentials, firestore
import os
import pickle

openai.api_key = 'api-key'
cred = credentials.Certificate("path/to/your/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Authenticate and access Gmail
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
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

# Fetch and process emails
def get_emails(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = results.get('messages', [])
    
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)
        process_email(mime_msg)

# Process and classify each email using LLM
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

    response = classify_email_with_llm(text)
    analyze_and_update_firestore(response)

# Use the LLM to classify the email and extract details
def classify_email_with_llm(email_content):
    prompt = f"""
    You are an AI assistant that classifies emails related to job applications. 
    Please classify the following email and extract key details:
    Email:
    {email_content}
    Provide your response in the following format:
    1. Classification: [e.g., Application Received, Rejection, OA Invitation, Interview Invitation, Job Offer, None of These]
    2. Company Name: [Extracted company name]
    3. Job Title: [Extracted job title]
    4. Location: [Extracted location or "US" if not found]
    5. Job Number: [Extracted job number or "N/A" if not found]
    """
    chat_completion = openai.ChatCompletion.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-3.5-turbo",
    )
    
    response = chat_completion.choices[0].message.content
    return response

# Analyze the email content and update Firebase
def analyze_and_update_firestore(response):
    lines = response.splitlines()
    classification = lines[0].split(":")[1].strip()
    
    if classification == "None of These": # If classification is "None of These", do not update Firebase
        return
    
    company_name = lines[1].split(":")[1].strip()
    job_title = lines[2].split(":")[1].strip()
    location = lines[3].split(":")[1].strip()
    job_number = lines[4].split(":")[1].strip()

    status_map = {
        'Application Received': 'Applied',
        'OA Invitation': 'OA',
        'Interview Invitation': 'Interview',
        'Job Offer': 'Offer',
        'Rejection': 'Rejection'
    }
    
    status = status_map.get(classification, 'Unknown')
    update_firestore(company_name, job_title, location, status, job_number)

# Update the Firestore database
def update_firestore(company_name, job_title, location, status, job_number):
    doc_ref = db.collection('applications').document(f"{company_name}_{job_title}")
    doc = doc_ref.get()
    
    if doc.exists:
        doc_ref.update({'status': status})
    else:
        doc_ref.set({
            'company_name': company_name,
            'job_title': job_title,
            'location': location if location else 'US',
            'status': status,
            'job_number': job_number
        })

def main():
    service = authenticate_gmail()
    get_emails(service)

if __name__ == '__main__':
    main()