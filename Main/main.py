import os
import re
import json
import pickle
import base64
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI

client = OpenAI(api_key="")
gmail_credentials_path = r""
firebase_cred_path = ""
cred = credentials.Certificate(firebase_cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

def authenticate_gmail():
    """Authenticate and get the Gmail service."""
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    token_path = 'token.pickle'
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(gmail_credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_last_update_timestamp(user_id):
    """Retrieve the last email processing timestamp from Firestore."""
    doc_ref = db.collection('Users').document(user_id).collection('Last_Update').document('timestamp')
    doc = doc_ref.get()
    if doc.exists:
        last_update = doc.to_dict().get('timestamp')
        return int(last_update.timestamp())
    else:
        return int(datetime(2024, 5, 1).timestamp())

def update_last_update_timestamp(user_id, timestamp):
    """Update the Firestore with the last email processing timestamp."""
    doc_ref = db.collection('Users').document(user_id).collection('Last_Update').document('timestamp')
    doc_ref.set({
        'timestamp': datetime.fromtimestamp(timestamp)
    })

def get_emails(service, user_id):
    """Fetch emails from the last read timestamp to now."""
    last_update_timestamp = get_last_update_timestamp(user_id)
    current_timestamp = int(datetime.now().timestamp())
    print(f"Fetching emails from {datetime.fromtimestamp(last_update_timestamp)} to {datetime.fromtimestamp(current_timestamp)}")
    query = f"after:{last_update_timestamp} before:{current_timestamp}"
    print(f"Query: {query}")
    next_page_token = None
    messages = []
    while True:
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                labelIds=['INBOX'],
                maxResults=100,
                pageToken=next_page_token
            ).execute()
            new_messages = results.get('messages', [])
            print(f"Retrieved {len(new_messages)} messages in this batch.")
            messages.extend(new_messages)
            next_page_token = results.get('nextPageToken')
            if not next_page_token:
                break
        except HttpError as error:
            print(f'An error occurred: {error}')
            break
    print(f"Total messages retrieved: {len(messages)}")
    return messages

def process_email(service, message, user_id):
    """Extract, classify, and update Firestore for a single email."""
    try:
        msg = service.users().messages().get(
            userId='me',
            id=message['id'],
            format='full'
        ).execute()
    except HttpError as error:
        print(f'An error occurred while fetching message {message["id"]}: {error}')
        return
    email_timestamp = int(msg['internalDate']) // 1000  
    payload = msg['payload']
    headers = payload.get('headers', [])
    subject = sender = date_sent = None
    for header in headers:
        if header['name'] == 'Subject':
            subject = header['value']
        elif header['name'] == 'From':
            sender = header['value']
        elif header['name'] == 'Date':
            date_sent = header['value']
    if date_sent:
        print(f"Email sent on: {date_sent}")
    else:
        print(f"Email timestamp (from internalDate): {datetime.fromtimestamp(email_timestamp)}")
    body = get_email_body(payload)
    if body:
        body = truncate_email_body(body)
        response = classify_email(body)
        if response:
            analyze_and_update_firestore(response, user_id, email_timestamp)
            update_last_update_timestamp(user_id, email_timestamp)

def get_email_body(payload):
    """Extract the plain text body from the email payload."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    return body
    else:
        data = payload.get('body', {}).get('data')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
            return body
    return None

def truncate_email_body(body):
    """Truncate the email body to fit within the model's context limit."""
    max_characters = 3000
    return body[:max_characters]

def classify_email(email_content):
    """Use OpenAI API to classify email content."""
    prompt = f"""
    You are an AI assistant specialized in classifying emails related to job applications.
    **Your tasks are:**

    1. **Determine the classification** of the email based on the following categories:
        - **Application Received**: Confirmation that the applicant's job application has been received.
        - **Rejection**: Notification that the applicant has not been selected for the position. Note: Rejections may be indirect, such as phrases like "We've decided to continue with other applicants."
        - **OA Invitation**: Invitation to complete an Online Assessment, such as coding assessments, coding challenges, or coding snapshots.
        - **Interview Invitation**: Invitation to schedule or attend an interview.
        - **Job Offer**: An offer of employment.
        - **None of These**: If the email does not fit any of the above categories.

    2. **Extract the following key details** from the email:
        - **Company Name**: The name of the company sending the email. If not found, set to **"Unknown"**.
        - **Job Title**: The title of the job position. If not found, set to **"Unknown"**.
        - **Location**: The location of the job or company. If not found, set to **"Unknown"**.
        - **Job Number**: Any job reference number provided. If not found, set to **"Unknown"**.

    **Important Instructions:**
        - **Ignore** emails related to purchases, orders, newsletters, irrelevant content, job application advertisements, and communications from platforms like LinkedIn.
        - Be **precise** and **concise** in your extraction.
        - **Do not assume** information that is not explicitly stated.
        - **Only** classify and extract information if the email is directly related to the specified job application categories.
        - If the email is unrelated or does not contain sufficient information, classify it as **"None of These"**.

    Provide your response **exactly** in the following JSON format **without any extra text**:
    ```json
    {{
        "Classification": "<One of: Application Received, Rejection, OA Invitation, Interview Invitation, Job Offer, None of These>",
        "Company Name": "<Extracted company name or 'Unknown'>",
        "Job Title": "<Extracted job title or 'Unknown'>",
        "Location": "<Extracted location or 'Unknown'>",
        "Job Number": "<Extracted job number or 'Unknown'>"
    }}
    Important:
    1. Output only the JSON object and nothing else.
    2. Do not include any explanations, comments, or extra text.
    3. Ensure the JSON is valid and properly formatted.
    **Email Content:**
    {email_content}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            temperature=0.3,
        )
        response = chat_completion.choices[0].message.content.strip()
        if not response:
            print("Received empty response from OpenAI API.")
            return None
        return response
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def analyze_and_update_firestore(response, user_id, email_timestamp):
    """Parse classification response and update Firestore."""
    if not response:
        print("No response received. Skipping email.")
        return
    print(f"Response from classify_email function:\n{response}")
    
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
        else:
            print("No JSON object found in the response.")
            return
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return

    classification = data.get("Classification")
    company_name = data.get("Company Name")
    job_title = data.get("Job Title")
    location = data.get("Location")
    job_number = data.get("Job Number")

    if not classification or classification.lower() == "none of these":
        print("Email classification is 'None of These'. Skipping Firestore update.")
        return

    status_map = {
        'Application Received': 'Applied',
        'OA Invitation': 'OA',
        'Interview Invitation': 'Interview',
        'Job Offer': 'Offer',
        'Rejection': 'Rejection'
    }
    status = status_map.get(classification, 'Unknown')
    update_firestore(user_id, company_name, job_title, location, status, job_number, email_timestamp)


def sanitize_string(value): 
    """Sanitize strings for Firestore document paths.""" 
    if value and value.lower() != "unknown": 
        return value.replace("/", "_").replace("\\", "_")                                         
    return "Unknown"

def update_firestore(user_id, company_name, job_title, location, status, job_number, email_timestamp): 
    """Update the Firestore database for a specific user.""" 
    company_name = sanitize_string(company_name) 
    job_title = sanitize_string(job_title) 
    email_datetime = datetime.fromtimestamp(email_timestamp).strftime('%Y-%m-%d_%H-%M-%S')

    try:
        doc_ref = db.collection('Users').document(user_id).collection(status).document(f"{email_datetime}_{company_name}_{job_title}")
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.update({
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            print(f"Updated status for {company_name} - {job_title} to '{status}'.")
        else:
            doc_ref.set({
                'company_name': company_name,
                'job_title': job_title,
                'location': location or 'Unknown',
                'status': status,
                'job_number': job_number or 'Unknown',
                'email_received_at': email_datetime,  
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            print(f"Added new application for {company_name} - {job_title} with status '{status}'.")
    except Exception as e:
        print(f"Firestore update error: {e}")

def main():
    print("Script started.")
    try:
        service = authenticate_gmail()
        print("Gmail service authenticated.")
    except Exception as e:
        print(f"Failed to authenticate Gmail service: {e}")
        return

    user_id = "nahomtesfahun001@gmail.com"
    try:
        emails = get_emails(service, user_id)
        print(f"Number of emails retrieved: {len(emails)}")
    except Exception as e:
        print(f"Failed to retrieve emails: {e}")
        return

    if not emails:
        print("No emails to process.")
        return

    for idx, message in enumerate(emails, start=1):
        print(f"Processing email {idx}/{len(emails)}")
        try:
            process_email(service, message, user_id)
        except Exception as e:
            print(f"Error processing email {idx}: {e}")

if __name__ == '__main__':
    main()