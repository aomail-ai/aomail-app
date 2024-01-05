import base64
import re
import time
import random
import json
import email
import logging
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from base64 import urlsafe_b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from .forms import MailForm
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.auth import exceptions as auth_exceptions
from google.oauth2 import credentials
from django.core.exceptions import ObjectDoesNotExist
from .models import SocialAPI
from googleapiclient.discovery import build
from . import library
from colorama import init, Fore
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from google_auth_oauthlib.flow import Flow
from rest_framework.response import Response
from rest_framework import status
from collections import defaultdict

# unused packages
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
from oauth2client import client
import google.auth
from google.auth.transport import requests as google_requests
from django.contrib.auth.models import User
import datetime
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.oauth2.credentials import Credentials
import httplib2
from google.auth.transport.urllib3 import AuthorizedHttp
import os.path
import pickle


# Initialize colorama with autoreset
init(autoreset=True)

test_int = 0


######################## GOOGLE API PROPERTIES ########################
GMAIL_READONLY_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'
GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'
CALENDAR_READONLY_SCOPE = 'https://www.googleapis.com/auth/calendar.readonly'
CONTACT_READONLY_SCOPE = 'https://www.googleapis.com/auth/contacts.readonly'
PROFILE_SCOPE = 'https://www.googleapis.com/auth/userinfo.profile'
EMAIL_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
OPENID_SCOPE = 'openid'
OTHER_CONTACT_READONLY_SCOPE = 'https://www.googleapis.com/auth/contacts.other.readonly'
SCOPES = [
    GMAIL_READONLY_SCOPE,
    GMAIL_SEND_SCOPE,
    CALENDAR_READONLY_SCOPE,
    CONTACT_READONLY_SCOPE,PROFILE_SCOPE,
    EMAIL_SCOPE,
    OPENID_SCOPE,
    OTHER_CONTACT_READONLY_SCOPE
]
CONFIG = json.load(open('creds/google_creds.json', 'r'))
# TODO change uri but first add it on the redirects uri in the google app project
#redirect_uri = 'http://localhost:9000/MailAssistant/google/auth_callback/'
CALLBACK_REDIRECT_URI = 'http://localhost:9000/google-login/'
SIGN_UP_REDIRECT_URI = 'http://localhost:8080/signup_part2'


######################## AUTHENTIFICATION ########################
def generate_auth_url(request):
    """Generate a connection URL to obtain the authorization code"""    
    flow = Flow.from_client_secrets_file(
        'google_creds.json',
        scopes = SCOPES,
        redirect_uri = CALLBACK_REDIRECT_URI
    )

    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    # Redirect the user to Google's consent screen
    return redirect(authorization_url)

def exchange_code_for_tokens(authorization_code):
    """Exchanges the authorization code for tokens and saves them in mailassistantdb"""
    flow = Flow.from_client_secrets_file(
        'google_creds.json',
        scopes = SCOPES,
        redirect_uri = SIGN_UP_REDIRECT_URI
    )

    # Exchange the authorization code for tokens
    flow.fetch_token(code=authorization_code)
    # Extract the tokens from the credentials
    credentials = flow.credentials
    access_token = credentials.token
    refresh_token = credentials.refresh_token    

    # TODO: Save tokens in mailassistantdb


def auth_callback(request):
    """Handles the callback after user authorization"""
    authorization_response = request.build_absolute_uri()

    logging.info(f"{Fore.YELLOW}AUTH RESPONSE: {authorization_response}")

    authorization_code = request.GET.get('code')

    if not authorization_code:
        return Response({
            'error': 'No authorization code provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    exchange_code_for_tokens(authorization_code)
    
    # Redirect to home page
    return HttpResponseRedirect('http://localhost:8080/home')

######################## AUTHENTIFICATION WITH JWT ########################
def get_credentials(user):
    try:
        social_api = SocialAPI.objects.get(user=user, type_api='Google')
        creds_data = {
            'token': social_api.access_token,
            'refresh_token': social_api.refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': CONFIG['client_id'],
            'client_secret': CONFIG['client_secret'],
            'scopes': SCOPES
        }
        creds = credentials.Credentials.from_authorized_user_info(creds_data)
    except ObjectDoesNotExist:
        print(f"No credentials found for user {user.username}")
        creds = None
    return creds

def refresh_credentials(creds):
    try:
        creds.refresh(Request())
    except auth_exceptions.RefreshError as e:
        print(f"Failed to refresh credentials: {e}")
        creds = None
    return creds

def save_credentials(creds, user):
    try:
        social_api, _ = SocialAPI.objects.get_or_create(user=user, type_api='google')
        social_api.access_token = creds.token
        social_api.refresh_token = creds.refresh_token
        social_api.save()
    except Exception as e:
        print(f"Failed to save credentials: {e}")

def build_services(creds) -> dict:
    services = {
        'gmail.readonly': build('gmail', 'v1', cache_discovery=False, credentials=creds),
        'gmail.send': build('gmail', 'v1', cache_discovery=False, credentials=creds),
        'calendar': build('calendar', 'v3', cache_discovery=False, credentials=creds),
        'contacts': build('people', 'v1', cache_discovery=False, credentials=creds),
        'profile': build('people', 'v1', cache_discovery=False, credentials=creds),
        'email': build('people', 'v1', cache_discovery=False, credentials=creds)
    }
    return services

def authenticate_service(user) -> dict:
    creds = get_credentials(user)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds = refresh_credentials(creds)
        if creds:
            save_credentials(creds, user)
        else:
            print("Failed to authenticate")
            return None
    
    service = build_services(creds)
    return service

######################## GMAIL API REQUESTS ########################
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_mails(request):
    """Returns the number of unread emails"""
    try:
        user = request.user        
        unread_count = 0
        service = authenticate_service(user)
            
        if service is not None:
            try:
                response = service['gmail.readonly'].users().messages().list(userId='me', q='is:unread').execute()
                unread_count = len(response.get('messages', []))
                return JsonResponse({'unreadCount': unread_count}, status=200)
            except Exception as e:
                logging.error(f"Error getting unread emails: {e}")
                return JsonResponse({'error': 'Failed to retrieve unread count'}, status=500)
    
        logging.error(f"{Fore.RED}Failed to authenticate")
        return JsonResponse({'unreadCount': unread_count}, status=400)
    
    except Exception as e:
        logging.error(f"{Fore.RED}An error occurred: {e}")
        return JsonResponse({'unreadCount': 0}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_parsed_contacts(request) -> list:
    """Returns a list of parsed unique contacts e.g: [{name: example, email: example@test.com}]"""
    user = request.user

    # Authenticate the user and build the service
    credentials = get_credentials(user)
    services = build_services(credentials)
    contacts_service = services['contacts']

    try:
        # Get contacts
        contacts = contacts_service.people().connections().list(
            resourceName='people/me',
            personFields='names,emailAddresses'
        ).execute()

        # Get other contacts
        other_contacts = contacts_service.otherContacts().list(
            pageSize=1000,
            readMask='names,emailAddresses'
        ).execute()

        # Get unique sender information from Gmail
        unique_senders = get_unique_senders(services)

        # Combine all contacts into a dictionary to ensure uniqueness
        all_contacts = defaultdict(set)

        # Parse contacts and other contacts
        contact_types = {
            'connections': contacts.get('connections', []),
            'otherContacts': other_contacts.get('otherContacts', [])
        }

        # Parse contacts and other contacts
        for _, contact_list in contact_types.items():
            for contact in contact_list:
                names = contact.get('names', [])
                emails = contact.get('emailAddresses', [])
                if names and emails:
                    name = names[0].get('displayName', '')
                    email = emails[0].get('value', '')
                    all_contacts[email].add(name)

        # Add unique sender information
        for email, name in unique_senders.items():
            all_contacts[email].add(name)

        # Format the parsed contacts
        parsed_contacts = [{'name': ', '.join(names), 'email': email} for email, names in all_contacts.items()]

        logging.info(f"{Fore.YELLOW}Retrieved {len(parsed_contacts)} unique contacts")
        return Response(parsed_contacts)
    except Exception as e:
        logging.exception("Error fetching contacts:")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_unique_senders(services) -> dict:
    """Fetches unique sender information from Gmail messages"""
    service = services['gmail.readonly']
    limit = 50
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=limit).execute()
    messages = results.get('messages', [])

    senders_info = {}

    if not messages:
        print('No messages found.')
    else:
        for message in messages:
            try:
                msg = service.users().messages().get(userId='me', id=message['id'], format='metadata', metadataHeaders=['From']).execute()
                headers = msg['payload']['headers']
                sender_header = next(header['value'] for header in headers if header['name'] == 'From')
                
                # Extracting the email address and name
                sender_parts = sender_header.split('<')
                sender_name = sender_parts[0].strip().strip('"')
                sender_email = sender_parts[-1].split('>')[0].strip() if len(sender_parts) > 1 else sender_name

                # Store the sender's name with the email address as the key
                senders_info[sender_email] = sender_name
            except Exception as e:
                print(f"Error processing message {message['id']}: {e}")

    return senders_info

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_image(request):
    """Returns the profile image of the user"""
    user = request.user
    credentials = get_credentials(user)
    service = build_services(credentials)['profile']

    # Get user profile
    profile = service.people().get(resourceName='people/me', personFields='photos').execute()

    # Extract profile image URL if available
    if 'photos' in profile:
        photos = profile['photos']
        if photos:
            photo_url = photos[0]['url']
            return Response({'profile_image_url': photo_url})
    
    return Response({'error': 'Profile image not found'}, status=status.HTTP_404_NOT_FOUND)



######################## Read Mails ########################
def parse_name_and_email(header_value):
    if not header_value:
        return None, None

    # Regex to extract name and email
    match = re.match(r'(.*)\s*<(.+)>', header_value)
    if match:
        name, email = match.groups()
        return name.strip(), email.strip()
    else:
        # If the format doesn't match, assume the entire value is the email
        return None, header_value.strip()

def get_mail(services, int_mail=None, id_mail=None):
    service = services['gmail.readonly']
    plaintext_var = [0]
    plaintext_var[0] = 0

    if int_mail is not None:
        results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
        messages = results.get('messages', [])
        if not messages:
            print('No new messages.')
            return None
        message = messages[int_mail]
        email_id = message['id']
    elif id_mail is not None:
        email_id = id_mail
    else:
        print("Either int_mail or id_mail must be provided")
        return None

    msg = service.users().messages().get(userId='me', id=email_id).execute()

    # Initialize variables
    subject = from_info = cc_info = bcc_info = decoded_data = None
    email_data = msg['payload']['headers']

    for values in email_data:
        name = values['name']
        if name == 'Subject':
            subject = values['value']
        elif name == 'From':
            from_info = parse_name_and_email(values['value'])
        elif name == 'Cc':
            cc_info = parse_name_and_email(values['value'])
        elif name == 'Bcc':
            bcc_info = parse_name_and_email(values['value'])

    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            decoded_data_temp = library.process_part(part, plaintext_var)
            if decoded_data_temp:
                decoded_data = library.concat_text(decoded_data, decoded_data_temp)
    elif 'body' in msg['payload']:
        data = msg['payload']['body']['data']
        data = data.replace("-", "+").replace("_", "/")
        decoded_data_temp = base64.b64decode(data).decode('utf-8')
        decoded_data = library.html_clear(decoded_data_temp)
    
    preprocessed_data = library.preprocess_email(decoded_data)

    return subject, from_info, preprocessed_data, cc_info, bcc_info, email_id


######################## Search bar ########################

# GOOGLE
def get_email_by_id(email_id):
    services = authenticate_service()
    service = services['gmail.readonly']
    
    # Fetch the email by its ID
    # msg = service.users().messages().get(userId='me', id=email_id, format='raw').execute()
    msg = service.users().messages().get(userId='me', id=email_id, format='full').execute()
    print("msg :",msg)

    msg_raw = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
    mime_msg = email.message_from_bytes(msg_raw)

    payload = msg['payload']
    email_body = library.process_part(payload, 0)

    # Parsing email content based on your requirements
    email_subject = mime_msg['subject']
    email_from = mime_msg['from']

    return {
        'subject': email_subject,
        'from': email_from,
        'body': email_body
    }

# GOOGLE # constructs query for searching through emails
def email_query(from_list,to_list,after,before,keywords,int_attachement):
    # print("_",from_list,"_")
    # print("_",to_list,"_")
    # print("_",after,"_")
    # print("_",before,"_")
    # print("_",keywords,"_")
    query = ""
    query_list = [0,0,0,0,0]
    if from_list:
        query_list[0]=1
        int_from = 0
        for email_int in range(len(from_list)):
            query+="from:"+from_list[email_int]+" "
            if int_from < len(from_list)-1:
                query+= "OR "
                int_from+=1
    if to_list:
        query_list[1]=1
        # for email in to_list:
        #     query+="from:"+email+" "
        int_to = 0
        for email_int in range(len(to_list)):
            query+="to:"+to_list[email_int]+" "
            if int_to < len(to_list)-1:
                query+= "OR "
                int_to+=1
    if after:
        query_list[2]=1
        query+='after:'+after+" "
    if before:
        query_list[3]=1
        query+='before:'+before+" "
    if int_attachement==1:
        query+='has:attachement '
    if keywords:
        query_list[4]=1
        query+=keywords
        # 
    # print(len(to_list))
    return query, query_list

# # GOOGLE # Search for emails
# def search_emails(query):
#     services = authenticate_service()
#     service = services['gmail.readonly']
#     # print('query: ',query)
#     email_ids = []
    
#     # Initial API request
#     response = service.users().messages().list(userId='me', q=query).execute()
    
#     while 'messages' in response:
#         while 'messages' in response:
#             for message in response['messages']:
#                 email_ids.append(message['id'])
            
#             # Check if there are more pages of results
#             if 'nextPageToken' in response:
#                 response = service.users().messages().list(userId='me', q=query, pageToken=response['nextPageToken']).execute()
#             else:
#                 break

#         # If you want to print out the IDs
#         for email_id in email_ids:
#             print(email_id)
#         print("Number of mails: ",len(email_ids))

#         return email_ids
def search_emails(query):
    services = authenticate_service()
    service = services['gmail.readonly']
    
    email_ids = []
    
    # Initial API request
    response = service.users().messages().list(userId='me', q=query).execute()
    
    while 'messages' in response:
        for message in response['messages']:
            email_ids.append(message['id'])
        
        # Check if there are more pages of results
        if 'nextPageToken' in response:
            response = service.users().messages().list(userId='me', q=query, pageToken=response['nextPageToken']).execute()
        else:
            break

    # If you want to print out the IDs
    for email_id in email_ids:
        print(email_id)
    print("Number of mails: ", len(email_ids))

    return email_ids


# delays retries after error 429 sync quota exceeded
def get_contacts(name,service_name,resource_name, max_retries=5):
    for attempt in range(max_retries):
        try:
            return _get_contacts(name,service_name,resource_name)
        except HttpError as e:
            if e.resp.status == 429 and attempt < max_retries - 1:
                # Exponential backoff with jitter.
                sleep_time = (2 ** attempt) + random.uniform(0, 0.1 * (2 ** attempt))
                time.sleep(sleep_time)
            else:
                raise
    return []

# GOOGLE # from text get corresponding email addresses
def get_email_address(from_who,to_who):
    myself_list = ['me','[Your Name]']
    if from_who in myself_list:
        email_list_from = get_user_email()
    else:
        email_list_from_in = get_contacts(from_who,'contacts','connections')
        email_list_from_ext = get_contacts(from_who,'other.contacts','otherContacts')
        email_list_from = email_list_from_in+email_list_from_ext
    if to_who in myself_list:
        email_list_to = get_user_email()
    else:
        email_list_to_in = get_contacts(to_who,'contacts','connections')
        email_list_to_ext = get_contacts(to_who,'other.contacts','otherContacts')
        email_list_to = email_list_to_in+email_list_to_ext
    return email_list_from,email_list_to

# GOOGLE # gets list of contact based on name
def get_contacts_name(name):
    services = authenticate_service()
    service = services['contacts']

    # Call the People API
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=1000,
        personFields='names,emailAddresses').execute()
    connections = results.get('connections', [])

    matching_contacts = []
    for person in connections:
        names = person.get('names', [])
        if names:
            full_name = names[0].get('displayName')
            if name.lower() in full_name.lower():
                matching_contacts.append(full_name)

    return matching_contacts

# GOOGLE # gets list of emails based on names
def _get_contacts(name, service_name,resource_name):
    services = authenticate_service()
    service = services[service_name]
    # print("_"+name+"_")
    if name:
        # Call the People API
        if service_name=='contacts':
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses').execute()
        else:
            results = service.otherContacts().list(
                pageSize=1000,
                readMask='names,emailAddresses').execute()
        # if resource_name == 'otherContacts':print('results: ',results)
        connections = results.get(resource_name, [])
        matching_contacts = []

        for person in connections:
            names = person.get('names', [])
            email_addresses = person.get('emailAddresses', [])
            if email_addresses:  # checking if there's an email address
                email = email_addresses[0].get('value')  # get the primary email address
                
                # If there's a display name and it matches the search, add it
                if names and name.lower() in names[0].get('displayName', '').lower():
                    full_name = names[0].get('displayName')
                    # matching_contacts.append((full_name, email))
                    matching_contacts.append(email)
                elif name.lower() in email.lower():
                    if names:
                        full_name = names[0].get('displayName')
                    else:
                        full_name = None
                    # matching_contacts.append((full_name, email))
                    matching_contacts.append(email)

        return matching_contacts
    else:
        return []

# GOOGLE # gets the user's email
def get_user_email():
    services = authenticate_service()
    service = services['contacts']

    # Retrieve user's profile information
    results = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()

    # Extract the email address from the response
    email_addresses = results.get('emailAddresses', [])
    if email_addresses:
        email = email_addresses[0].get('value')
    
    return [email]

# GOOGLE # Search attachement
# def search_attachments(query):
#     """
#     Search for attachments in Gmail.

#     :param service: the Gmail API service instance.
#     :param user_id: the user's email address. Use "me" to indicate the authenticated user.
#     :param query: the search query string (same as in Gmail search box).
#     :return: a list of attachment filenames and their data.
#     """
#     services = authenticate_service()
#     service = services['gmail.readonly']

#     # Step 1: List Emails
#     results = service.users().messages().list(userId='me', q=query).execute()
#     messages = results.get('messages', [])

#     attachments = []

#     for message in messages:
#         # Step 2: Fetch Individual Email
#         msg = service.users().messages().get(userId='me', id=message['id']).execute()

#         for part in msg['payload']['parts']:
#             # Step 3: Examine Attachments
#             if 'filename' in part and part['filename']:
#                 data = part['body'].get('data')
#                 file_data = base64.urlsafe_b64decode(data.encode('UTF-8')) if data else None
#                 attachments.append({
#                     'filename': part['filename'],
#                     'data': file_data,
#                     'mail_id': message['id']
#                 })

#     return attachments

def search_attachments(query):
    """
    Search for attachments in Gmail.

    :param query: the search query string (same as in Gmail search box).
    :param user_id: the user's email address. Use "me" to indicate the authenticated user.
    :return: a list of attachment filenames and their data.
    """
    services = authenticate_service()
    service = services['gmail.readonly']

    # Step 1: List Emails
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    attachments = []

    for message in messages:
        # Step 2: Fetch Individual Email
        msg = service.users().messages().get(userId='me', id=message['id']).execute()

        for part in msg['payload']['parts']:
            # Step 3: Examine Attachments
            if 'filename' in part and part['filename']:
                data = part['body'].get('data')
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8')) if data else None
                attachments.append({
                    'filename': part['filename'],
                    'data': file_data,
                    'mail_id': message['id']
                })

    return attachments

######################## Other ########################


# GOOGLE
def send_mail(request):
    # \"\"\"Handle the process of sending emails.\"\"\"
    # service = authenticate_service(GMAIL_SEND_SCOPE)
    services = authenticate_service()
    service = services['gmail.send']
    if request.method == 'POST' :
        form = MailForm(request.POST)
        if form.is_valid() :
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            to = form.cleaned_data['to']
            cc = form.cleaned_data['cc']
            bcc = form.cleaned_data['bcc']
            piece_jointe = form.cleaned_data['piece_jointe']

            multipart_message = MIMEMultipart()
            multipart_message["Subject"] = subject
            multipart_message["from"] = "me"
            multipart_message["to"] = to
            multipart_message["cc"] = cc
            multipart_message["bcc"] = bcc

            # Attach the message content to the email, regardless of whether
            # there's an attachment.
            multipart_message.attach(MIMEText(message, "plain"))

            if piece_jointe != None :
                piece_jointe = MIMEApplication(open(piece_jointe, 'rb').read())
                piece_jointe.add_header('Content-Disposition', 'attachment', filename='attachment.pdf')
                multipart_message.attach(piece_jointe)

            raw_message = urlsafe_b64encode(multipart_message.as_string().encode('UTF-8')).decode()

            body = {'raw': raw_message}

            multipart_message = service.users().messages().send(userId="me", body=body).execute()

            return redirect('MailAssistant:home_page')

    else : 
        form = MailForm()         
    return render(request, 'send_mails.html', {'form': form})

# GOOGLE
def get_calendar_events(services):
    # \"\"\"Retrieve events from Google Calendar.\"\"\"
    # service = authenticate_service(CALENDAR_READONLY_SCOPE)
    service = authenticate_service()
    service = services['calendar']
    events_result = service.events().list(calendarId='primary', maxResults=10).execute()
    events = events_result.get('items',[])
    
    for item in events:
        print('item: ',item)



# Fetch the name and the email of the contacts of the user 
def get_info_contacts(services):
    service = services['contacts']

    # Request a list of all the user's connections (contacts)
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=1000,  # Adjust the page size as needed
        personFields='names,emailAddresses'
    ).execute()

    contacts = results.get('connections', [])

    names_emails = []
    for contact in contacts:
        # Extract the name and email address of each contact
        name = contact.get('names', [{}])[0].get('displayName')
        email_addresses = [email['value'] for email in contact.get('emailAddresses', [])]

        names_emails.append({'name': name, 'emails': email_addresses})

    return names_emails


# NEW MAIL
# search in mailbox
'''
def search_emails(services, search_query, max_results=5):
    service = services['gmail.readonly']
    query = f"{search_query}"

    # Limit the number of results to improve performance
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    found_emails = {}

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='metadata', metadataHeaders=['From']).execute()
        headers = msg.get('payload', {}).get('headers', [])
        sender = next((header['value'] for header in headers if header['name'] == 'From'), None)

        if sender and not any(substring in sender.lower() for substring in ["noreply", "no-reply"]): # CAN BE UPGRADED FOR MORE PERFORMANCE
            email = sender.split('<')[-1].split('>')[0].strip()
            name = sender.split('<')[0].strip() if '<' in sender else email
            if email:  # Ensure email is not empty
                found_emails[email] = name

    return found_emails'''

# V2 : better to check the mail structure (comparing with the input)
def search_emails(services, search_query, max_results=2):
    service = services['gmail.readonly']
    query = f"{search_query}"

    # Fetch the list of emails based on the query
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    found_emails = {}

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='metadata', metadataHeaders=['From']).execute()
        headers = msg.get('payload', {}).get('headers', [])
        sender = next((header['value'] for header in headers if header['name'] == 'From'), None)

        if sender:
            email = sender.split('<')[-1].split('>')[0].strip().lower()
            name = sender.split('<')[0].strip().lower() if '<' in sender else email

            # Additional filtering: Check if the sender email/name matches the search query
            if search_query.lower() in email or search_query.lower() in name:
                if email and not any(substring in email for substring in ["noreply", "no-reply"]):
                    found_emails[email] = name

    return found_emails


def find_user_in_emails(services, search_query):
    emails = search_emails(services, search_query)

    if not emails:
        return "No matching emails found."

    return emails

# To send email
def send_email_with_gmail(services, subject, message, to, cc, bcc, attachments=None):

    service = services['gmail.send']

    multipart_message = MIMEMultipart()
    multipart_message["Subject"] = subject
    multipart_message["from"] = "me"
    multipart_message["to"] = to

    if cc:
        multipart_message["cc"] = cc
    if bcc:
        multipart_message["bcc"] = bcc

    multipart_message.attach(MIMEText(message, "html"))

    # Attach each file in the attachments list
    if attachments:
        for uploaded_file in attachments:
            # Read the contents of the uploaded file
            file_content = uploaded_file.read()
            part = MIMEApplication(file_content)
            part.add_header('Content-Disposition', 'attachment', filename=uploaded_file.name)
            multipart_message.attach(part)

    raw_message = urlsafe_b64encode(multipart_message.as_string().encode('UTF-8')).decode()
    body = {'raw': raw_message}
    service.users().messages().send(userId="me", body=body).execute()

# GOOGLE # gets list of emails based on names
def _get_contacts(name, service_name,resource_name):
    services = authenticate_service()
    service = services[service_name]
    # print("_"+name+"_")
    if name:
        # Call the People API
        if service_name=='contacts':
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses').execute()
        else:
            results = service.otherContacts().list(
                pageSize=1000,
                readMask='names,emailAddresses').execute()
        # if resource_name == 'otherContacts':print('results: ',results)
        connections = results.get(resource_name, [])
        matching_contacts = []

        for person in connections:
            names = person.get('names', [])
            email_addresses = person.get('emailAddresses', [])
            if email_addresses:  # checking if there's an email address
                email = email_addresses[0].get('value')  # get the primary email address
                
                # If there's a display name and it matches the search, add it
                if names and name.lower() in names[0].get('displayName', '').lower():
                    full_name = names[0].get('displayName')
                    # matching_contacts.append((full_name, email))
                    matching_contacts.append(email)
                elif name.lower() in email.lower():
                    if names:
                        full_name = names[0].get('displayName')
                    else:
                        full_name = None
                    # matching_contacts.append((full_name, email))
                    matching_contacts.append(email)

        return matching_contacts
    else:
        return []

''' OLD CODE TO DELETE AFTER CHECKING
def check_token_pickle():
    print('check_token_pickle')
    creds = None
    # Check if token.pickle exists and load credentials if it does
    if os.path.exists('token.pickle'):
        if os.stat("token.pickle").st_size > 0:
            with open('token.pickle', 'rb') as token:
                try:
                    creds = pickle.load(token)
                except EOFError:
                    print("EOFError: The file 'token.pickle' is empty or corrupted. Please regenerate the token.")
                    creds = None
        else:
            print("The file 'token.pickle' is empty. Please regenerate the token.")
            creds = None
    else:
        print("The file 'token.pickle' does not exist. Please generate the token.")
        creds = None
    return creds

def check_creds(creds):
    print('check_creds')
    # If there are no valid credentials, create them
    if not creds or not creds.valid:
        # if creds and creds.expired and creds.refresh_token:
        #     creds.refresh(Request())
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except RefreshError:
            creds = None  # set creds to None to force reauthentication
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8081)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def build_services(creds):
    print('build_services')
    # Build services for Gmail and Calendar based on the passed SCOPES
    service = {}
    if 'https://www.googleapis.com/auth/gmail.readonly' in SCOPES:
        service['gmail.readonly'] = build('gmail', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/gmail.send' in SCOPES:
        service['gmail.send'] = build('gmail', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/calendar.readonly' in SCOPES:
        service['calendar'] = build('calendar', 'v3', credentials=creds)
    if 'https://www.googleapis.com/auth/contacts.readonly' in SCOPES:
        service['contacts'] = build('people', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/userinfo.profile' in SCOPES:
        service['profile'] = build('people', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/userinfo.email' in SCOPES:
        service['email'] = build('people', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/contacts.other.readonly' in SCOPES:
        service['other.contacts'] = build('people', 'v1', credentials=creds)
    # return services
    return service

# authentication service for all google services needed at once, used on startup, then stored until log out
def authenticate_service():
    creds = check_token_pickle()
    creds = check_creds(creds)
    if creds:
        service = build_services(creds)
    else:
        global test_int
        test_int+=1
        print('coucou ',test_int)
        service = authenticate_service()
    return service


def authenticate_service_old():
    """Authenticate and return service objects for Google APIs."""
    creds = None
    # Check if token.pickle exists and load credentials if it does
    if os.path.exists('token.pickle'):
        if os.stat("token.pickle").st_size > 0:
            with open('token.pickle', 'rb') as token:
                try:
                    creds = pickle.load(token)
                except EOFError:
                    print("EOFError: The file 'token.pickle' is empty or corrupted. Please regenerate the token.")
                    creds = None
        else:
            print("The file 'token.pickle' is empty. Please regenerate the token.")
            creds = None
    else:
        print("The file 'token.pickle' does not exist. Please generate the token.")
        creds = None

    # If there are no valid credentials, create them
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Build services for Gmail and Calendar based on the passed SCOPES
    service = {}
    if 'https://www.googleapis.com/auth/gmail.readonly' in SCOPES:
        service['gmail.readonly'] = build('gmail', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/gmail.send' in SCOPES:
        service['gmail.send'] = build('gmail', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/calendar.readonly' in SCOPES:
        service['calendar'] = build('calendar', 'v3', credentials=creds)
    if 'https://www.googleapis.com/auth/contacts.readonly' in SCOPES:
        service['contacts'] = build('people', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/userinfo.profile' in SCOPES:
        service['profile'] = build('people', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/userinfo.email' in SCOPES:
        service['email'] = build('people', 'v1', credentials=creds)
    if 'https://www.googleapis.com/auth/contacts.other.readonly' in SCOPES:
        service['other.contacts'] = build('people', 'v1', credentials=creds)
    # return services
    return service
'''


# used to get mail number "int_mail" (minus one as lists starts from 0) or mail ID 'id_mail' and returns subject, expeditor and body 
''' OLD function TO DELETE AFTER CHECKING
def get_mail(services, int_mail, id_mail):
    service = services['gmail.readonly']
    plaintext_var = [0]
    plaintext_var[0] = 0

    if int_mail!=None:
        # Call the Gmail API to fetch INBOX
        results = service.users().messages().list(userId='me',labelIds=['INBOX']).execute()
        messages = results.get('messages', [])
        if not messages:
            print('No new messages.')
        else:
            message = messages[int_mail]
            email_id = message['id']
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
    # 2 lines added to make it work for id as well
    elif id_mail!=None:
        email_id = id_mail
        msg = service.users().messages().get(userId='me', id=id_mail).execute()
    # lines idented back to work as intended
    email_data = msg['payload']['headers']
    for values in email_data:
        name = values['name']
        if name == 'Subject':
            subject = values['value']
        if name == 'From':
            from_name = values['value']
            print("From: ", from_name)
    decoded_data=None
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            decoded_data_temp = library.process_part(part,plaintext_var)
            if decoded_data_temp:
                decoded_data = library.concat_text(decoded_data,decoded_data_temp)

    # If there's no 'parts' field, the body of the email could be in the 'body' field
    elif 'body' in msg['payload']:
        data = msg['payload']['body']["data"]
        data = data.replace("-","+").replace("_","/")
        decoded_data_temp = base64.b64decode(data).decode('utf-8')
        decoded_data = library.html_clear(decoded_data_temp)
    preprocessed_data = library.preprocess_email(decoded_data)
                    
    return subject,from_name,preprocessed_data, email_id'''

''' OLD ONE 
USELESS AS THE OTHER ONE WORKS WELL
def build_services(creds):
    authed_http = AuthorizedHttp(creds, Request())
    service = {
        'gmail.readonly': build('gmail', 'v1', http=authed_http),
        'gmail.send': build('gmail', 'v1', http=authed_http),
        'calendar': build('calendar', 'v3', http=authed_http),
        'contacts': build('people', 'v1', http=authed_http),
        'profile': build('people', 'v1', http=authed_http),
        'email': build('people', 'v1', http=authed_http),
        'other.contacts': build('people', 'v1', http=authed_http),
    }
    return service'''

# Fetch all the mail in the mailbox of the user => WORKS but it take to much time
'''
def get_unique_senders(services):
    service = services['gmail.readonly']
    results = service.users().messages().list(userId='me', labelIds = ['INBOX']).execute()
    messages = results.get('messages', [])

    email_addresses = set()

    if not messages:
        print('No messages found.')
    else:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
            headers = msg['payload']['headers']
            sender = next(header['value'] for header in headers if header['name'] == 'From')
            email_address = sender.split('<')[-1].split('>')[0].strip()
            email_addresses.add(email_address)

    return list(email_addresses)'''