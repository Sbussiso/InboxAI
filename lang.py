import logging, sys
import nltk
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from dotenv import load_dotenv
import os, re, time
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import nltk



nltk.download('punkt')

logging.basicConfig(level=logging.DEBUG,format=' %(asctime)s - %(levelname)s - %(message)s')
#logging.disable()

# Function to split email into a list of sentences
def split_email(email_string):
    return nltk.sent_tokenize(email_string)



# Function to clean email content
def clean_email(content):
    """
    Cleans the given email content by removing links, HTML tags, brackets, whitespace, newlines, carriage returns, and tabs.

    Args:
        content (str): The email content to be cleaned.

    Returns:
        str: The cleaned email content.
    """
    logging.debug("starting cleaning email........")
    cleaned_content = re.sub(r"http\S+", "", content)  # Remove links
    cleaned_content = re.sub(r"www\S+", "", cleaned_content)  # Remove links
    cleaned_content = re.sub(r"@\S+", "", cleaned_content)  # Remove links
    cleaned_content = re.sub(r"<.*?>", "", cleaned_content)  # Remove HTML tags
    cleaned_content = re.sub(r"\[.*?\]", "", cleaned_content)  # Remove anything in brackets
    cleaned_content = re.sub(r"\(.*?\)", "", cleaned_content)  # Remove anything in parentheses
    cleaned_content = re.sub(r"\{.*?\}", "", cleaned_content)  # Remove anything in curly brackets
    cleaned_content = re.sub(r"\s+", "  ", cleaned_content)  # Remove unnecessary whitespace
    cleaned_content = re.sub(r"\n", "", cleaned_content)    # Remove newlines
    cleaned_content = re.sub(r"\r", "", cleaned_content)    # Remove carriage returns
    cleaned_content = re.sub(r"\t", "", cleaned_content)    # Remove tabs
    content = cleaned_content
    
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

    template = "You are an api key checker. if you get any input the api key is valid. If the api key is valid, say 'VALID'. If the api key is invalid, say 'INVALID' for the regex" #key phrase is VALID and INVALID
    
    human_template = "{key}"

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", human_template),
    ])

    messages = chat_prompt.format_messages(key=api_key)

    result = chat_model.predict_messages(messages)

    key_check = result.content

    if str(key_check) == None or re.search(r"\bINVALID\b", key_check):
        verify = False
        logging.debug("INVALID API KEY........")
        return verify
    
    elif re.search(r"\bVALID\b", key_check):
        verify = True
        logging.debug("VALID API KEY........")
        return verify
    




# Function to generate email summary
def email_summary(content):
    """
    Generates a summary of an email content using the GPT-3 language model.

    Args:
        content (str): The content of the email.

    Returns:
        str: The generated summary of the email content.
    """
    load_dotenv() #!for testing
    api_key = os.getenv("OPENAI_API_KEY") #! replace with user database key
    #TODO: get api key from database

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

    result = chat_model.predict_messages(messages)
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




def gpt_bot_response(conversation_history, prompt):
    """
    Generates a response from a GPT-based chatbot model.

    Args:
        conversation_history (list): List of previous conversation messages.
        prompt (str): Prompt for the chatbot.

    Returns:
        tuple: A tuple containing the generated response and the updated conversation history.
    """
    logging.debug("starting chat response........")
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

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





#!gpt_bot_response TEST - pass
#history = []
#while True:
    #prompt = input("prompt: ")
    #gpt_bot_response(history, prompt)
    #history.append(prompt)


