from openai import OpenAI

client = OpenAI()
def classify_email(email_content):
    
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
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-3.5-turbo",)
    
    response = chat_completion.choices[0].message.content
    return response

email_content = """Hi
We have received your application for position Software Engineering Internship - Summer 2025 - 12345 .
Thank you for choosing ABCD as a prospective employer, where we are passionate about our people and the limitless potential of your career. We are currently reviewing your application and will reach out as soon as there is an update.
Thanks,
Qualcomm Talent Acquisition Team
Why ABCD?
Career Development - We prioritize opportunities for continuous learning with career development programs, employee recognition initiatives, tuition reimbursement, and mentorship, all so our employees can exceed their potential.
Diversity, Equity, & Inclusion - We find diversity and the creativity it brings, vital to our success. To foster this diversity, we are committed to equitable and inclusive practices that allow each employee the opportunity to succeed.
Corporate Responsibility - We invent technologies that have the power to catalyze social change and the potential to have a positive impact on society for the better-for everyone. Click here to learn more.
"""

result = classify_email(email_content)

print(result)