import logging, sys
import nltk
import openai
#from langchain.chat_models import ChatOpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.text_splitter import CharacterTextSplitter
#from langchain.tokenizers import OpenAITokenizer
from dotenv import load_dotenv
import os, re, time, html
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import nltk


try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logging.basicConfig(level=logging.DEBUG,format=' %(asctime)s - %(levelname)s - %(message)s')
logging.disable()

# Function to split email into a list of sentences
def split_email(email_string):
    return nltk.sent_tokenize(email_string)



# Function to clean email content
def clean_email(content):
    """
    Cleans the given email content by removing HTML tags, links, email addresses,
    unnecessary whitespace, and other unwanted patterns.

    Args:
        content (str): The email content to be cleaned.

    Returns:
        str: The cleaned email content.
    """

    logging.debug("starting cleaning email........")
    # Decoding HTML entities
    content = html.unescape(content)

    # Additional regex patterns
    content = re.sub(r"style='[^']+'", "", content)  # Remove inline styles
    content = re.sub(r"<style.*?</style>", "", content, flags=re.DOTALL)  # Remove style tags
    content = re.sub(r"<script.*?</script>", "", content, flags=re.DOTALL)  # Remove script tags
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)  # Remove HTML comments
    content = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "", content)  # Remove email addresses
    content = re.sub(r"[-*]{3,}", "---", content)  # Shorten repeated characters

    # Your existing patterns
    content = re.sub(r"http\S+", "", content)  # Remove links
    content = re.sub(r"www\S+", "", content)  # Remove links
    content = re.sub(r"@\S+", "", content)  # Remove links
    content = re.sub(r"<.*?>", "", content)  # Remove HTML tags
    content = re.sub(r"\[.*?\]", "", content)  # Remove anything in brackets
    content = re.sub(r"\(.*?\)", "", content)  # Remove anything in parentheses
    content = re.sub(r"\{.*?\}", "", content)  # Remove anything in curly brackets
    content = re.sub(r"\s+", " ", content)  # Remove unnecessary whitespace
    content = re.sub(r"\n", "", content)  # Remove newlines
    content = re.sub(r"\r", "", content)  # Remove carriage returns
    content = re.sub(r"\t", "", content)  # Remove tabs
    
    logging.debug("Finished cleaning email.......")
    logging.debug(f"RETURNING CLEANED CONTENT: {content}")
    logging.debug("\n\n\n\n\n\n___________________________________________\n\n\n\n\n\n")
    return content
    




# Function to check if api key is valid #!not working
def check_api_key(api_key):
    """
    Checks the validity of an API key.

    Args:
        api_key (str): The API key to be checked.

    Returns:
        bool: True if the API key is valid, False otherwise.
    """

    logging.debug("starting api key check........")
    chat_model = ChatOpenAI(openai_api_key=api_key)

    template = "Just say 'VALID' and nothing else for a regex check."
        
    human_template = "{key}"

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    messages = chat_prompt.format_messages(key=api_key)

    result = chat_model.predict_messages(messages)

    key_check = result.content

    if str(key_check) == None:
        verify = False
        logging.debug("NO API KEY PROVIDED........")
        return verify
        
    elif re.search(r"\bVALID\b", key_check):
        verify = True
        logging.debug("VALID API KEY........")
        return verify
        
    
    




# Function to generate email summary
def email_summary(content, api_key):
    """
    Generates a summary of an email content using the GPT-3 language model.

    Args:
        content (str): The content of the email.
        api_key (str): The API key for OpenAI.

    Returns:
        str: The generated summary of the email content.
    """
    #load_dotenv() #!for testing
    #api_key = os.getenv("OPENAI_API_KEY") #! replace with user database key
    api_key = api_key #TODO: get api key from database
   

    # summary function
    logging.debug("starting email summary........")

    chat_model = ChatOpenAI(openai_api_key=api_key)

    template = "You are an email summarization tool. Ignore all noise."
    #if There is no input at all say 'GPT-SUMMARY-ERROR' for the regex" #key phrase is ERROR for error handling
    human_template = "EMAIL: {text}"

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    messages = chat_prompt.format_messages(text=content)

    result = None
    trunicate = False
    while result is None:
        try:
            result = chat_model.predict_messages(messages)
        except openai.error.InvalidRequestError as e:
            logging.debug("first InvalidRequestError, Waiting for 5 seconds...")
            time.sleep(5)

            # retries the request 2 times, if it fails again it will trunicate the content
            i = 0
            if trunicate == True:
                logging.debug("skiping retry... trunicate is true")
            else:
                while i < 2:
                    logging.debug("Retrying...")
                    try:
                        result = chat_model.predict_messages(messages)
                        #trunicate = False
                        break
                    except openai.error.InvalidRequestError as e:
                        logging.debug("second InvalidRequestError, Waiting for 5 seconds...")
                        time.sleep(5)
                        i += 1
                        if i == 2:
                            trunicate = True
                            break
            logging.debug("Finished retrying...")

            if trunicate == True:
                #trunicates the content if it is too long
                logging.debug(f"Prompt too big. Truncating content...")

                email_split = split_email(content)
                #removes the last 12 sentances from the email
                trunicated_email = " ".join(email_split[:-50])

                messages = chat_prompt.format_messages(text=trunicated_email)
                content = trunicated_email

        
            
    
    summary = result.content

    # handles the summary error called by chat gpt
    if summary == None: #or re.search(r"\bGPT-SUMMARY-ERROR\b", summary):
        logging.debug("ERROR FOUND IN SUMMARY........")
        result.content = f"SUMMARY FAILED. Please try to regenerate summary or view in Gmail. RAW CONTENT: {content},\n SUMMARY: {summary}"
        summary = result.content
        #TODO: add error handling for summary error
        return summary
            
    else:
        logging.debug(summary)
        logging.debug("finished email summary.......")
        return summary




def gpt_bot_response(conversation_history, prompt, api_key):
    """
    Generates a response from a GPT-based chatbot model.

    Args:
        conversation_history (list): List of previous conversation messages.
        prompt (str): Prompt for the chatbot.

    Returns:
        tuple: A tuple containing the generated response and the updated conversation history.
    """
    logging.debug("starting chat response........")
    #load_dotenv()
    #api_key = os.getenv("OPENAI_API_KEY")
    api_key = api_key

    chat_model = ChatOpenAI(openai_api_key=api_key)

    template = "You are a helpful assistant. CONVERSATION HISTORY: {history}"
    human_template = "HUMAN PROMPT: {text}"

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    messages = chat_prompt.format_messages(history=conversation_history, text=prompt)

    assistant_message = chat_model.predict_messages(messages)
    logging.debug(assistant_message.content)
    logging.debug("finished email summary.......")
    return assistant_message.content, conversation_history


def generate_email_draft(api_key):
    """
    Generates a draft email using the GPT-3 language model.

    Returns:
        str: The generated draft email.
    """
    logging.debug("starting draft generation........")
    #load_dotenv()
    #api_key = os.getenv("OPENAI_API_KEY")

    chat_model = ChatOpenAI(openai_api_key=api_key)

    template = "Respond to this email as if you are the recipient."
    human_template = "EMAIL: {text}"

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    messages = chat_prompt.format_messages(text="")

    result = chat_model.predict_messages(messages)

    draft = result.content
    logging.debug("finished draft generation.......")
    return draft
















#!gpt_bot_response TEST - pass
#history = []
#while True:
    #prompt = input("prompt: ")
    #gpt_bot_response(history, prompt)
    #history.append(prompt)


