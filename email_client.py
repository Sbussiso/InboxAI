from bs4 import BeautifulSoup
import base64
import pickle
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
from bs4 import BeautifulSoup
import os
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def get_plain_text(parts):
    for part in parts:
        if part['mimeType'] == 'text/plain':
            text = part['body']['data']
            return base64.urlsafe_b64decode(text.encode('ASCII')).decode('utf-8')
        if part['mimeType'] == 'text/html':
            text = part['body']['data']
            html_content = base64.urlsafe_b64decode(text.encode('ASCII')).decode('utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        if 'parts' in part:
            return get_plain_text(part['parts'])


def email_access():
    # Set the required scopes
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


    # Load your credentials
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, prompt the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    MAX_RESULTS = 20

    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=MAX_RESULTS).execute()
    messages = results.get('messages', [])

    emails = []

    if not messages:
        print('No messages found.')
    else:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            subject = None
            internal_date = msg.get('internalDate', None)
            for header in msg['payload']['headers']:
                if header['name'].lower() == 'subject':
                    subject = header['value']
                    break

            content = get_plain_text(msg['payload'].get('parts', [msg['payload']]))

            emails.append({
                'id': msg['id'],
                'subject': subject,
                'content': content,
                'internal_date': int(internal_date) if internal_date is not None else None
            })

    return emails, service

def display_emails(service):
    emails, _ = email_access()

    # Sort emails by internal_date in descending order (newest to oldest)
    emails.sort(key=lambda x: x['internal_date'], reverse=True)

    #Create a folder named emails if it dosent exist
    if not os.path.exists('emails'):
        os.makedirs('emails')

    for email in emails:
        # Extract sender's email address
        sender_email = None
        msg = service.users().messages().get(userId='me', id=email['id']).execute()
        for header in msg['payload']['headers']:
            if header['name'].lower() == 'from':
                sender_email = header['value']
                break

        if sender_email is None:
            continue

        # Replace invalid characters in the sender's email address
        sender_email = sender_email.replace('<', '').replace('>', '').replace('/', '_').replace('"', '')

        # Create a unique file name for each email
        file_name = f"{sender_email}_{email['id']}.txt"
        print(f"Saving email to file: {file_name}")

        # Save the email content to a separate text file
        with open(os.path.join('emails', file_name), 'w', encoding='utf-8') as file:
            file.write(f"Message ID: {email['id']} - Subject: {email['subject']}\n")
            file.write(f"Content: {email['content']}\n\n")
    



# stars email at user request
def star_email(service, message_id):
    try:
        # Add the 'STARRED' label to the email
        label_ids_to_add = ['STARRED']
        msg_labels = {'addLabelIds': label_ids_to_add}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} marked as important.')
    except HttpError as error:
        print(f'An error occurred: {error}')



#deletes email at user request
def move_email_to_trash(service, message_id):
    try:
        # Add the 'TRASH' label to the email
        label_ids_to_add = ['TRASH']
        msg_labels = {'addLabelIds': label_ids_to_add}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} moved to trash successfully.')
    except HttpError as error:
        print(f'An error occurred: {error}')


#replies to current email "go thru emails" function
def reply_email(service, message_id, recipient, text):
    try:
        # Create a MIMEText object with the reply text
        message = MIMEText(text, 'plain')
        message['to'] = recipient
        message['subject'] = f"Re: (your subject here)"
        message['In-Reply-To'] = message_id
        message['References'] = message_id

        # Encode the MIMEText object in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send the email
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        print(f"Replied to message with ID {message_id}.")
    except HttpError as error:
        print(f"An error occurred: {error}")






#creates label if does not exist
def create_label(service, label_name):
    label_object = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }

    existing_labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in existing_labels:
        if label['name'].lower() == label_name.lower():
            return label['id']

    new_label = service.users().labels().create(userId='me', body=label_object).execute()
    return new_label['id']





# organizes email into folder
def organize_email_into_folder(service, message_id, folder_name):
    label_id = create_label(service, folder_name)

    try:
        # Add the folder label to the email
        msg_labels = {'addLabelIds': [label_id]}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} moved to folder "{folder_name}".')
    except HttpError as error:
        print(f'An error occurred: {error}')




#functions to delete email folders(labels)



def get_label_id_by_name(service, label_name):
    try:
        labels = service.users().labels().list(userId='me').execute().get('labels', [])
        for label in labels:
            if label['name'].lower() == label_name.lower():
                return label['id']
    except HttpError as error:
        print(f"An error occurred: {error}")
    return None

def delete_label(service, label_name):
    label_id = get_label_id_by_name(service, label_name)
    if label_id:
        try:
            service.users().labels().delete(userId='me', id=label_id).execute()
            print(f"Label '{label_name}' has been deleted.")
        except HttpError as error:
            print(f"An error occurred: {error}")
    else:
        print(f"Label '{label_name}' not found.")
    

#view all gmail labels
def view_all_labels(service):
    try:
        # Retrieve the list of labels
        labels = service.users().labels().list(userId='me').execute().get('labels', [])

        if not labels:
            print('No labels found.')
        else:
            print('Labels:')
            for label in labels:
                print(f"{label['name']} (ID: {label['id']})")

    except HttpError as error:
        print(f"An error occurred: {error}")



def search_inbox(service, query):
    try:
        # Perform a search with the given query
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
        else:
            print(f"Messages matching query '{query}':")
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                subject = None
                internal_date = msg.get('internalDate', None)
                for header in msg['payload']['headers']:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                        break

                content = get_plain_text(msg['payload'].get('parts', [msg['payload']]))

                print(f"Message ID: {msg['id']} - Subject: {subject}")
                print(f"Content: {content}\n")

    except HttpError as error:
        print(f"An error occurred: {error}")

#marks email as unread
def mark_email_as_unread(service, message_id):
    try:
        # Add the 'UNREAD' label to the email
        label_ids_to_add = ['UNREAD']
        msg_labels = {'addLabelIds': label_ids_to_add}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} marked as unread.')
        
    except HttpError as error:
        print(f'An error occurred: {error}')



# archives email
def archive_message(service, message_id):
    try:
        # Remove the 'INBOX' label from the email
        label_ids_to_remove = ['INBOX']
        msg_labels = {'removeLabelIds': label_ids_to_remove}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} archived.')

    except HttpError as error:
        print(f'An error occurred: {error}')


#reports spam and moves to spam folder
def report_spam(service, message_id):
    try:
        # Add the 'SPAM' label to the email
        label_ids_to_add = ['SPAM']
        msg_labels = {'addLabelIds': label_ids_to_add}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} reported as spam and moved to spam folder.')

    except HttpError as error:
        print(f'An error occurred: {error}')


#marks email as important
def mark_message_as_important(service, message_id):
    try:
        # Add the 'IMPORTANT' label to the email
        label_ids_to_add = ['IMPORTANT']
        msg_labels = {'addLabelIds': label_ids_to_add}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} marked as important.')

    except HttpError as error:
        print(f'An error occurred: {error}')



# marks email as not important
def mark_message_as_not_important(service, message_id):
    try:
        # Remove the 'IMPORTANT' label from the email
        label_ids_to_remove = ['IMPORTANT']
        msg_labels = {'removeLabelIds': label_ids_to_remove}
        service.users().messages().modify(userId='me', id=message_id, body=msg_labels).execute()

        print(f'Message with ID {message_id} marked as not important.')
    except HttpError as error:
        print(f'An error occurred: {error}')


def filter_messages(service, query):
    try:
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        filtered_emails = []

        if not messages:
            print('No messages found.')
        else:
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                subject = None
                internal_date = msg.get('internalDate', None)
                for header in msg['payload']['headers']:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                        break

                content = get_plain_text(msg['payload'].get('parts', [msg['payload']]))

                filtered_emails.append({
                    'id': msg['id'],
                    'subject': subject,
                    'content': content,
                    'internal_date': int(internal_date) if internal_date is not None else None
                })

        return filtered_emails
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None





def send_email_with_attachment(service, recipient, subject, body, attachment_path):
    try:
        # Create a MIMEMultipart object
        message = MIMEMultipart()
        message['to'] = recipient
        message['subject'] = subject

        # Attach the plain text message
        message.attach(MIMEText(body, 'plain'))

        # Attach the file
        with open(attachment_path, 'rb') as attachment_file:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(attachment_file.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
            message.attach(attachment)

        # Encode the MIMEMultipart object in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send the email
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        print(f"Email with attachment sent to {recipient}.")
    except HttpError as error:
        print(f"An error occurred: {error}")






def create_filter(service, from_email, label_name):
    try:
        # Create a new filter with the specified criteria and label
        filter_object = {
            'criteria': {
                'from': from_email
            },
            'action': {
                'addLabelIds': [label_name]
            }
        }
        service.users().settings().filters().create(userId='me', body=filter_object).execute()
        print(f"Filter created for emails from '{from_email}' and label '{label_name}'.")
    except HttpError as error:
        print(f"An error occurred: {error}")



