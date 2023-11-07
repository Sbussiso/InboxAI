from flask import Blueprint, render_template, request, jsonify, session, flash, url_for
from flask_login import login_required, current_user
import openai
from email_client import email_access, display_emails, move_email_to_trash, star_email, reply_email, send_email_with_attachment
import os, re, base64, quopri, sys
#import tiktoken
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
import pickle
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask_sqlalchemy import SQLAlchemy
from .models import db, Email, Conversation
from datetime import datetime
import binascii
import logging, webbrowser
from flask import redirect
from tempfile import NamedTemporaryFile
import nltk
from gpt3api import gpt_response_upgraded, gpt_bot_response
from .forms import KeyForm  # Import form from forms.py
from .models import db, Email, Conversation, ApiKey  # Import models from models.py

import colorlog

# Define the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create a console handler
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)s - %(levelname)s - %(message)s'))

# Add the handler to the logger
logger.addHandler(handler)

logger.debug("Debug message")
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

#logging.disable()


#gets the api key from the current user.
def get_api_key(user_id):
    api_key_entry = ApiKey.query.filter_by(user_id=user_id).first()
    return api_key_entry.key if api_key_entry else None


#uses get_api_key to set configure the key
def connect_api_key():
    api_key = get_api_key(current_user.id)
    if api_key is None:
        # Handle the case where the API key is not set
        flash('API key not set.', 'error')
        return redirect(url_for('views.key'))

    openai.api_key = api_key







views = Blueprint('views', __name__)
# measures usage of API key
def token_size(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens








@views.route('/learnMore')
def more_info():
    return redirect("https://myinboxai.com/")


@views.route('/get')
def chat():
    #conntects user api to gpt-3
    connect_api_key()

    user_message = request.args.get('msg')
    
    # Store the user's message in the database
    user_conversation = Conversation(user_id=current_user.id, role="user", content=user_message)
    db.session.add(user_conversation)
    
    # Get the conversation history from the database
    conversation_history_query = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.timestamp)
    conversation_history = [{"role": conv.role, "content": conv.content} for conv in conversation_history_query]
    
    # Get the bot's response and add it to the database
    assistant_message, conversation_history = gpt_bot_response(conversation_history, user_message) 
    assistant_conversation = Conversation(user_id=current_user.id, role="assistant", content=assistant_message)
    db.session.add(assistant_conversation)
    db.session.commit()
    
    return jsonify({'message': assistant_message})  # return as JSON





@views.route('/')
@login_required
def home():

    #conntects user api to gpt-3
    connect_api_key()




    #writes console outpu to text file
    file_handler = logging.FileHandler('logfile.log')
    logging.getLogger().addHandler(file_handler)

    
    logging.debug("STARTING EMAIL PROCESS....")

    emails, service = email_access()

    # Get a list of emails
    result = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = result.get('messages')
    logging.debug("RETRIEVED MESSAGES")
    logging.debug(f"MESSAGES: {messages}")
    logging.debug("LOOPING THRU MESSAGES.......")

    # For each email in the list...
    for msg in messages:
        email_id = msg['id']
        logging.debug(f"CURRENT MESSAGE: {msg}")

        # Check if the email already exists in the database
        logging.debug("VERIFYING IF EMAIL EXISTS IN DATABASE.....\n")
        if Email.query.filter_by(id=email_id).first():
            logging.debug("EMAIL ALREADY EXISTS IN DATABASE, CONTINUING.......\n")
            continue  # Skip this email and move to the next one
        #! PROGRAM WILL EXIT FOR LOOP HERE IF ALL EMAILS ALREADY PRESENT IN DATABASE
        logging.debug("EMAIL NOT IN DATABASE, ADDING.......\n")
        logging.debug("FETCHING EMAIL DATA.....\n")
        # Fetch the email from the Gmail API...
        email_data = service.users().messages().get(userId='me', id=email_id).execute()
        logging.debug("DATA RECIEVED")

        logging.debug("CHECKING IF EMAIL IS MULTIPART.....")
        logging.debug(f"email_data['payload'] VALUE: {email_data['payload']}")

        # Initialize content as an empty string
        content = ''
        
        # Start by getting the payload
        payload = email_data['payload']

        def extract_data(part):
            data = part['body'].get('data')
            if data:
                return data
            if 'parts' in part:
                for subpart in part['parts']:
                    data = extract_data(subpart)
                    if data:
                        return data
            return None

        # First, try to extract 'data' directly from 'body'
        data = payload['body'].get('data')

        # If 'data' was not found directly under 'body'...
        if data is None:
            if 'parts' in payload:
                # If 'parts' exist, try to recursively extract 'data'
                data = extract_data(payload)
        # If 'data' is still None after these steps, then there is no 'data' in the email payload
        if data is None:
            data = ''
            logging.debug("NO DATA FOUND IN EMAIL BODY")
        
        # If 'data' is found, proceed to decode and parse it
        if data:
            content = base64.urlsafe_b64decode(data).decode("utf-8")
            logging.debug(f"BASE64 DECODED CONTENT: {content}")

            # Parse the content with BeautifulSoup if it's HTML
            if payload['mimeType'] == 'text/html':
                soup = BeautifulSoup(content, 'html.parser')

                # Remove style and script tags content
                for element in soup(["script", "style"]):
                    element.decompose()

                content = soup.get_text(separator=' ', strip=True)
                logging.debug(f"BS EXTRACTED HTML CONTENT: {content}")


        logging.debug("EXTRACTING DATA FROM PAYLOAD.......")
        # Extract the headers from the payload
        headers = email_data['payload']['headers']

        logging.debug("EXTRACTING SENDER FROM HEADER......")
        # Extract the sender from the headers
        sender = next((header['value'] for header in headers if header['name'] == 'From'), '')
        receiver = next((header['value'] for header in headers if header['name'] == 'To'), '')
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), '')

        # Start by getting the payload
        payload = email_data['payload']
        logging.debug(f"PAYLOAD: {payload}")

        # Check if the email has parts
        if 'parts' in payload['body']:
            # Get the body data from the parts
            parts = payload['body']['parts']
            data = parts[0]['body']['data'] if 'data' in parts[0]['body'] else ""
        else:
            # Get the body data directly
            data = payload['body']['data'] if 'data' in payload['body'] else ""

        date_string = email_data['internalDate']
        unix_timestamp = int(date_string) / 1000.0  # Convert UNIX timestamp to seconds
        date = datetime.fromtimestamp(unix_timestamp)  # Convert UNIX timestamp to datetime


        # Print the details of the email being added
        logging.debug("New email added to the database:")
        logging.debug(f"Email ID: {email_id}")
        logging.debug(f"Sender: {sender}")
        logging.debug(f"Receiver: {receiver}")
        logging.debug(f"Subject: {subject}")
        logging.debug(f"Content: {content}")
        logging.debug(f"Date: {date}")
        logging.debug("--------")

        logging.debug("CLEANING UP CONTENT.......")

        # Remove CSS properties
        clean_content = re.sub(r'[\w-]*:\s*.*?;', '', content)

        # Remove CSS classes ending with "important"
        clean_content = re.sub(r'\w*important', '', clean_content)

        # Remove CSS classes ending with "displaynone"
        clean_content = re.sub(r'\w*displaynone', '', clean_content)

        # Remove multiple line breaks
        cleaned_content = re.sub(r'\n\s*\n', '\n', clean_content)

        # Remove multiple spaces
        cleaned_content = re.sub(r' +', ' ', cleaned_content)

        # removes links
        cleaned_content = re.sub(r'http\S+', '', cleaned_content)

        # removes special characters
        cleaned_content = re.sub(r'[^\w\s]', '', cleaned_content)

        #remove excess whitespace
        cleaned_content = ' '.join(cleaned_content.split())

        content = cleaned_content
        logging.debug(f"CONTENT CLEANED: {content}")

        # Create a new Email instance and add it to the session
        email = Email(
            id=email_id,
            sender=sender,
            receiver=receiver,
            subject=subject,
            content=content,
            date=date,
            gpt_response = None,
            token_size=None
        )

        

        # measure size of api request
        token = token_size(content, "gpt2")
        #adds token size to database
        email.token_size = token


        
        
        #TODO: send to gpt api
        logging.debug("CONVERTING EMAIL TO DICTIONARY.......")
        prompt = email.to_dict() #makes sure email is a dictionary
        logging.debug("EMAIL CONVERTED TO DICTIONARY")
        logging.debug(f"CONTENT: {prompt['content']}")

        prompt = prompt['content']

        # Generate response using GPT-3
        logging.debug("ATTEMPTING TO SENT TO GPT-3 API.......")


        #runs email through upgraded gpt response
        response = gpt_response_upgraded(prompt)#! imported from gpt3api.py, multiple depencencies
        
        logging.debug(f"GPT API CONNECTION SUCCESSFUL: {response}")
        email.gpt_response = response  
        db.session.add(email)



    # Commit all the added emails to the database
    db.session.commit()

    #to see updated database
    emails = Email.query.all()
    email_dicts = [email.to_dict() for email in emails]

    
    #TODO: display emails on front end
    #! this is the old one for files
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logging.debug(f"RECIEVED AjAX REQUEST SUCCESSFULLY: {email_dicts}")
        return jsonify(email_dicts)
    
    else:
        return render_template("home.html", user=current_user, summaries=email_dicts)






#deletes emails at user request
@views.route('/star_email', methods=['POST'])
@login_required
def star_emails():
    logging.debug("RECIEVED DATA: ", request.get_json())
    emails, service = email_access()
    email_id = request.get_json().get('email_id')
    logging.debug(f"INPUT GOING INTO FUNCTION: {email_id}")

    if email_id is None:
        return {"message": "No email id provided"}, 400
    
   
    #stars email thru gmail api
    star_email(service, email_id)

    return {"message": "Email stared successfully"}, 200
    

    



@views.route('/delete_email', methods=['POST'])
@login_required
def delete_email():
    logging.debug("RECIEVED DATA: ", request.get_json())
    emails, service = email_access() #change emails to _
    # Get the email_id from the request data
    email_id = request.get_json().get('email_id')
    logging.debug(f"email_id, VALUE: {email_id}")
    


    if email_id is None:
        return {"message": "No email id provided"}, 400
    
    email_record = Email.query.get(email_id)
    if email_record is None:
        return {"message": "No email found with provided id"}, 400
    
    db.session.delete(email_record)
    logging.debug("MESSAGE REMOVED FROM DATABASE")
    db.session.commit()

    logging.debug("RUNNING GMAIL API FUNCTION........")
    move_email_to_trash(service, email_id)

    return {"message": "Email deleted successfully"}, 200




# regenerates and updates gpt3 response into database
@views.route('/regenerate_response', methods=['POST'])
@login_required
def regen_response():
    #conntects user api to gpt-3
    connect_api_key()

    print("Received data: ", request.get_json())
    emails, service = email_access() #change emails to _
    # Get the email_id from the request data
    email_id = request.get_json().get('email_id')
    logging.debug(f"email_id, VALUE: {email_id}")
    


    if email_id is None:
        return {"message": "No email id provided"}, 400
 
    #get email id
    email = Email.query.get(email_id)

    if email is None:
        return {"message": "No email found with provided id"}, 404

    #generate new response for email

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are summarizing an email."},
                {"role": "user", "content": email.content},
            ],
            max_tokens = 2000,
            n=1,
            stop=None,
            temperature=0.5 #0.5 is base temperature
        )
        print(f"API RESPONSE: {response}")

        # Extract the assistant's message from the response
        if 'choices' in response:
            assistant_message = response['choices'][0]['message']['content']
        else:
            assistant_message = "There was an error with the API call."
            print("API Error:", response)      

    except openai.OpenAIError as e:
        return {"message": f"GPT API Error: {e}"}, 500
    
    #update gpt response to database
    email.gpt_response = assistant_message
    db.session.commit()

    return jsonify({'gpt_response': assistant_message})  # return as JSON







@views.route('/draft_response', methods=['POST'])
@login_required
def response():
    logging.debug(f"RECIEVED DATA: {request.get_json()}")
    emails, service = email_access() #change emails to _
    # Get the email_id and draft_response from the request data
    data = request.get_json()
    email_id = data.get('email_id')
    draft_response = data.get('draft_response')

    logging.debug(f"email_id, VALUE: {email_id}")
    logging.debug(f"draft_response, VALUE: {draft_response}")
    
    if email_id is None:
        return {"message": "No email id provided"}, 400 
      
    email_record = Email.query.get(email_id)

    if email_record is None:
        return {"message": "No email found with provided id"}, 400
    logging.debug(f"EMAIL FOUND IN DATABASE, ID: {email_id}")

    #drafts and sends email response to current email sender
    #TODO: make user input come from website
    recipient = email_record.receiver

    reply_email(service, email_id, recipient, draft_response)

    return {"message": "Response sent successfully"}, 200




@views.route('/draft_response_attachment', methods=['POST'])
@login_required
def response_attachment():
    logging.debug(f"RECIEVED DATA: {request.get_json()}")
    logging.debug('ENTERING DRAFT_RESPONSE_ATTACHMENT FUNCTION')
    _, service = email_access()
    data = request.get_json()
    email_id = data.get('email_id')
    draft_response = data.get('draft_response')
    file_contents_base64 = data.get('file_contents')

    logging.debug(f"email_id, VALUE: {email_id}")
    logging.debug(f"draft_response, VALUE: {draft_response}")

    if email_id is None:
        return {"message": "No email id provided"}, 400 
      
    email_record = Email.query.get(email_id)

    if email_record is None:
        return {"message": "No email found with provided id"}, 400
    logging.debug(f"EMAIL FOUND IN DATABASE, ID: {email_id}")

    # Decode the base64 file contents and write to a temporary file
    file_data = base64.b64decode(file_contents_base64.split(',')[1])
    temp_file = NamedTemporaryFile(delete=False)
    temp_file.write(file_data)
    temp_file.close()

    recipient = email_record.receiver
    subject = "GPT attachment response from front end"
    body = draft_response

    logging.debug(f"""
    DATA BEING PASSED TO EMAIL ATTACHMENT FUNCTION:
    recipient = {recipient}
    subject = {subject}
    body = {body}
    file attachment = {temp_file.name}
    """)

    # Call send_email_with_attachment with the path of the temporary file
    send_email_with_attachment(service, recipient, subject, body, temp_file.name)

    # Delete the temporary file
    os.unlink(temp_file.name)

    return {"message": "Response sent successfully"}, 200



    



    





@views.route('/generate_draft', methods=['POST'])
def generate_draft():
    #conntects user api to gpt-3
    connect_api_key()

    data = request.get_json()
    email_id = data.get('email_id')

    # Here you would retrieve the email from your database and send the email content to GPT-3

    email = Email.query.get(email_id)
    #TODO: generate gpt response
    if email is None:
        return {"message": "No email found with provided id"}, 404

    #generate new response for email

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are to respond to this email professionally as if you are the original reciever of this content. Feel free to be creative"},
                {"role": "user", "content": email.content},
            ],
            max_tokens = 2000,
            n=1,
            stop=None,
            temperature=0.5 #0.5 is base temperature
        )
        print(f"API RESPONSE: {response}")

        # Extract the assistant's message from the response
        if 'choices' in response:
            assistant_message = response['choices'][0]['message']['content']
        else:
            assistant_message = "There was an error with the API call."
            print("API Error:", response)      

    except openai.OpenAIError as e:
        return {"message": f"GPT API Error: {e}"}, 500
    
    

    return jsonify({'gpt3_response': assistant_message})




#TODO: open email button
#opens gmail on current email
@views.route('/open_gmail', methods=['POST'])
@login_required
def to_gmail():
    logging.debug('ENTERED /open_gmail ROUTE.......')
    return redirect("https://www.gmail.com")