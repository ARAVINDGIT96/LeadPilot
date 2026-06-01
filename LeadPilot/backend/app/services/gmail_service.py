from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from typing import Dict

class GmailService:
    def __init__(self, credentials_dict: Dict):
        """Initialize Gmail service with user's OAuth2 credentials"""
        self.credentials = Credentials(
            token=credentials_dict['access_token'],
            refresh_token=credentials_dict['refresh_token'],
            token_uri=credentials_dict['token_uri'],
            client_id=credentials_dict['client_id'],
            client_secret=credentials_dict['client_secret']
        )
        self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def send_email(self, to_email: str, subject: str, body: str, from_email: str) -> Dict:
        """Send email via Gmail API"""
        try:
            message = MIMEMultipart()
            message['to'] = to_email
            message['from'] = from_email
            message['subject'] = subject
            
            msg = MIMEText(body, 'plain')
            message.attach(msg)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}
            
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            return {
                "status": "success",
                "message_id": result['id'],
                "message": "Email sent successfully"
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
