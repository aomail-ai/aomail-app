"""
Handles authentication and HTTP requests for the Microsoft Graph API.

TODO:
- [SUBSCRIPTION] handle "subscriptionRemoved or missed"
- Split into smaller functions: email_to_db + opti the function first
- Add a function save_email_to_db as a utility function common to all email providers
"""

import base64
import datetime
import json
import logging
import threading
import time
import urllib.parse
import requests
from collections import defaultdict
from urllib.parse import urlencode
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import UploadedFile
from django.utils.timezone import make_aware
from msal import ConfidentialClientApplication
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import View
from rest_framework.response import Response
from MailAssistant.ai_providers import claude
from MailAssistant.utils.tree_knowledge import Search
from MailAssistant.utils import security
from MailAssistant.utils.security import subscription
from MailAssistant.utils.serializers import (
    EmailDataSerializer,
    EmailScheduleDataSerializer,
)
from MailAssistant.email_providers.microsoft.authentication import (
    get_headers,
    get_social_api,
    refresh_access_token,
)
from MailAssistant.utils import email_processing
from MailAssistant.constants import (
    FREE_PLAN,
    ADMIN_EMAIL_LIST,
    BASE_URL,
    DEFAULT_CATEGORY,
    EMAIL_NO_REPLY,
    ENCRYPTION_KEYS,
    GRAPH_URL,
    MAX_RETRIES,
    MICROSOFT_AUTHORITY,
    MICROSOFT_CLIENT_STATE,
    MICROSOFT_CONFIG,
    MICROSOFT_PROVIDER,
    MICROSOFT_SCOPES,
    REDIRECT_URI_LINK_EMAIL,
    REDIRECT_URI_SIGNUP,
)
from MailAssistant.models import (
    Category,
    Contact,
    Email,
    KeyPoint,
    MicrosoftListener,
    Preference,
    Rule,
    Sender,
    SocialAPI,
)


######################## LOGGING CONFIGURATION ########################
LOGGER = logging.getLogger(__name__)


######################## PROFILE REQUESTS ########################
def verify_license(access_token: str) -> bool:
    """
    Verifies if there is a license associated with the account.

    Args:
        access_token (str): The access token used to authenticate the request.

    Returns:
        bool: True if a license is associated with the account, False otherwise.
    """
    graph_endpoint = f"{GRAPH_URL}me/licenseDetails"
    headers = get_headers(access_token)
    response = requests.get(graph_endpoint, headers=headers)

    if response.status_code == 200:
        data: dict = response.json()
        if data["value"] == []:
            return False
        else:
            return True
    return False


def get_info_contacts(access_token: str) -> list:
    """
    Fetch the name and the email of the contacts of the user.

    Args:
        access_token (str): The access token used to authenticate the request.

    Returns:
        list: A list of dictionaries containing contact names and their email addresses.
    """
    graph_endpoint = f"{GRAPH_URL}me/contacts"

    try:
        headers = get_headers(access_token)
        params = {"$top": 1000}

        response = requests.get(graph_endpoint, headers=headers, params=params)
        response.raise_for_status()
        response_data: dict = response.json()

        contacts: list[dict] = response_data.get("value", [])
        names_emails = []

        for contact in contacts:
            name = contact.get("displayName")
            email_addresses = [
                email["address"] for email in contact.get("emailAddresses", [])
            ]
            names_emails.append({"name": name, "emails": email_addresses})

        return names_emails

    except Exception as e:
        error = (
            response_data.get("error_description", response.reason)
            if response
            else str(e)
        )
        LOGGER.error(
            f"Failed to retrieve contacts. Error: {str(e)}. Response details: {error}"
        )
        return []


def get_unique_senders(access_token: str) -> dict:
    """
    Fetches unique sender information from Microsoft Graph API messages.

    Args:
        access_token (str): The access token used to authenticate the request.

    Returns:
        dict: A dictionary where keys are email addresses of senders and values are their corresponding names.
    """
    senders_info = {}

    try:
        headers = get_headers(access_token)
        limit = 50
        graph_endpoint = f"{GRAPH_URL}me/messages?$select=sender&$top={limit}"
        response = requests.get(graph_endpoint, headers=headers)
        response_data: dict = response.json()

        if response.status_code == 200:
            messages: list[dict] = response_data.get("value", [])
            for message in messages:
                sender: dict[str, dict] = message.get("sender", {})
                email_address = sender.get("emailAddress", {}).get("address", "")
                name = sender.get("emailAddress", {}).get("name", "")
                senders_info[email_address] = name
        else:
            error = response_data.get("error_description", response.reason)
            LOGGER.error(f"Failed to fetch messages: {error}")

        return senders_info

    except Exception as e:
        LOGGER.error(f"Error fetching senders: {str(e)}")
        return senders_info


@api_view(["GET"])
@subscription([FREE_PLAN])
def get_profile_image(request: HttpRequest) -> Response:
    """
    Retrieves the profile image URL of the user from Microsoft Graph API.

    Args:
        request (HttpRequest): The HTTP request object containing the user and email headers.

    Returns:
        Response: A JSON response containing the profile image URL or an error message.
    """
    user = request.user
    email = request.headers.get("email")
    social_api = get_social_api(user, email)

    if not social_api:
        return Response(
            {"error": "Social API credentials not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    access_token = refresh_access_token(social_api)

    try:
        headers = get_headers(access_token)
        graph_endpoint = f"{GRAPH_URL}me/photo/$value"
        response = requests.get(graph_endpoint, headers=headers)

        if response.status_code == 200:
            photo_data = response.content

            if photo_data:
                # Convert image to URL
                photo_data_base64 = base64.b64encode(photo_data).decode("utf-8")
                photo_url = f"data:image/png;base64,{photo_data_base64}"
                return Response(
                    {"profile_image_url": photo_url}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Profile image not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        else:
            response_data: dict = response.json()
            error = response_data.get("error_description", response.reason)
            LOGGER.error(
                f"Failed to retrieve profile image for user ID {user.id}: {error}"
            )
            return Response(
                {"error": f"Failed to retrieve profile image: {error}"},
                status=response.status_code,
            )

    except Exception as e:
        LOGGER.error(
            f"Failed to retrieve profile image for user ID {user.id}: {str(e)}"
        )
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def get_email(access_token: str) -> dict:
    """
    Retrieves the primary email of the user from Microsoft Graph API.

    Args:
        access_token (str): Access token required for authentication.

    Returns:
        dict: {'email': <user_email>} if successful,
              {'error': <error_message>} if any error occurs.
    """
    if not access_token:
        return {"error": "Access token is missing"}

    try:
        graph_api_endpoint = f"{GRAPH_URL}me"
        headers = get_headers(access_token)
        response = requests.get(graph_api_endpoint, headers=headers)
        json_data: dict = response.json()

        if response.status_code == 200:
            email = json_data["mail"]
            return {"email": email}
        else:
            error = json_data.get("error_description", response.reason)
            return {"error": f"Failed to get email from Microsoft API: {error}"}

    except Exception as e:
        return {"error": f"Failed to get email from Microsoft API: {str(e)}"}


######################## EMAIL REQUESTS ########################
@api_view(["POST"])
@subscription([FREE_PLAN])
def send_schedule_email(request: HttpRequest) -> Response:
    """
    Schedule the sending of an email using the Microsoft Graph API with deferred delivery.

    Args:
        request (HttpRequest): HTTP request object containing POST data with email details.

    Returns:
        Response: Response indicating success or error.
    """
    user = request.user
    email = request.POST.get("email")
    social_api = get_social_api(user, email)

    if not social_api:
        return Response(
            {"error": "Social API credentials not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    access_token = refresh_access_token(social_api)
    serializer = EmailScheduleDataSerializer(data=request.POST)

    if serializer.is_valid():
        data = serializer.validated_data
        try:
            send_datetime: datetime.datetime = data["datetime"]
            subject = data["subject"]
            message = data["message"]
            to = data["to"]
            cc = data.get("cc")
            bcc = data.get("bcc")
            attachments: list[UploadedFile] = data.get("attachments", [])
            all_recipients = to + (cc if cc else []) + (bcc if bcc else [])

            graph_endpoint = f"{GRAPH_URL}me/sendMail"
            headers = get_headers(access_token)

            email_content = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": message},
                    "toRecipients": [
                        {"emailAddress": {"address": email}} for email in to
                    ],
                    "singleValueExtendedProperties": [
                        {"id": "SystemTime 0x3FEF", "value": send_datetime.isoformat()}
                    ],
                }
            }

            if cc:
                email_content["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in cc
                ]

            if bcc:
                email_content["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in bcc
                ]

            if attachments:
                email_content["message"]["attachments"] = []

                for file_data in attachments:
                    file_name = file_data.name
                    file_content = file_data.read()
                    attachment = base64.b64encode(file_content).decode("utf-8")
                    email_content["message"]["attachments"].append(
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": file_name,
                            "contentBytes": attachment,
                        }
                    )

            try:
                response = requests.post(
                    graph_endpoint, headers=headers, json=email_content
                )

                if response.status_code == 202:
                    threading.Thread(
                        target=email_processing.save_contacts,
                        args=(user, email, all_recipients),
                    ).start()
                    return Response(
                        {"message": "Email scheduled successfully!"},
                        status=status.HTTP_202_ACCEPTED,
                    )
                else:
                    response_data: dict = response.json()
                    error = response_data.get("error", response.reason)
                    LOGGER.error(f"Failed to schedule email: {error}")
                    return Response({"error": error}, status=response.status_code)

            except Exception as e:
                LOGGER.error(f"Failed to send email: {str(e)}")
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            LOGGER.error(f"Error preparing email data: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@subscription([FREE_PLAN])
def send_email(request: HttpRequest) -> Response:
    """
    Sends an email using the Microsoft Graph API.

    Args:
        request (HttpRequest): HTTP request object containing POST data with email details.

    Returns:
        Response: Response indicating success or error.
    """
    user = request.user
    email = request.POST.get("email")
    social_api = get_social_api(user, email)

    if not social_api:
        return Response(
            {"error": "Social API credentials not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    access_token = refresh_access_token(social_api)
    serializer = EmailDataSerializer(data=request.POST)

    if serializer.is_valid():
        data = serializer.validated_data
        try:
            subject = data["subject"]
            message = data["message"]
            to = data["to"]
            cc = data.get("cc")
            bcc = data.get("bcc")
            attachments: list[UploadedFile] = data.get("attachments", [])
            all_recipients = to + (cc if cc else []) + (bcc if bcc else [])

            graph_endpoint = f"{GRAPH_URL}me/sendMail"
            headers = get_headers(access_token)

            email_content = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": message},
                    "toRecipients": [
                        {"emailAddress": {"address": email}} for email in to
                    ],
                }
            }

            if cc:
                email_content["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in cc
                ]

            if bcc:
                email_content["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in bcc
                ]

            if attachments:
                email_content["message"]["attachments"] = []

                for file_data in attachments:
                    file_name = file_data.name
                    file_content = file_data.read()
                    attachment = base64.b64encode(file_content).decode("utf-8")
                    email_content["message"]["attachments"].append(
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": file_name,
                            "contentBytes": attachment,
                        }
                    )

            try:
                response = requests.post(
                    graph_endpoint, headers=headers, json=email_content
                )

                if response.status_code == 202:
                    threading.Thread(
                        target=email_processing.save_contacts,
                        args=(user, email, all_recipients),
                    ).start()
                    return Response(
                        {"message": "Email sent successfully!"},
                        status=status.HTTP_202_ACCEPTED,
                    )
                else:
                    response_data: dict = response.json()
                    error = response_data.get("error", response.reason)
                    LOGGER.error(f"Failed to send email: {error}")
                    return Response({"error": error}, status=response.status_code)

            except Exception as e:
                LOGGER.error(f"Failed to send email: {str(e)}")
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            LOGGER.error(f"Error preparing email data: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


def delete_email(email_id: int, social_api: SocialAPI) -> dict:
    """
    Moves the email to the bin of the user using the Microsoft Graph API.

    Args:
        email_id (int): The ID of the email to be moved to the bin.
        social_api (SocialAPI): The SocialAPI instance containing the user's access and refresh tokens.

    Returns:
        dict: A dictionary containing a success message if the email is moved to the trash successfully,
              or an error message if the operation fails.
    """
    access_token = refresh_access_token(social_api)
    headers = get_headers(access_token)
    url = f"{GRAPH_URL}/me/messages/{email_id}/move"
    data = {"destinationId": "deleteditems"}

    response = requests.post(url, headers=headers, json=data)

    if "id" in response.text:
        return {"message": "Email moved to trash successfully!"}
    elif "error" in response.text:
        return {"message": "Email moved to trash successfully!"}
    else:
        LOGGER.error(
            f"Failed to move email to trash for Social API email: {social_api.email}: {response.text}"
        )
        return {"error": f"Failed to move email to trash: {response.text}"}


def set_email_read(social_api: SocialAPI, email_id: int):
    """
    Sets the status of the email to 'read' on Outlook.

    Args:
        social_api (SocialAPI): The SocialAPI instance containing the user's access and refresh tokens.
        email_id (int): The ID of the email to be marked as read.
    """
    access_token = refresh_access_token(social_api)
    headers = get_headers(access_token)
    data = {"isRead": True}
    requests.patch(f"{GRAPH_URL}/me/messages/{email_id}/", headers=headers, json=data)


def set_email_unread(social_api: SocialAPI, email_id: int):
    """
    Sets the status of the email to 'unread' on Outlook.

    Args:
        social_api (SocialAPI): The SocialAPI instance containing the user's access and refresh tokens.
        email_id (int): The ID of the email to be marked as unread.
    """
    access_token = refresh_access_token(social_api)
    headers = get_headers(access_token)
    data = {"isRead": False}
    requests.patch(f"{GRAPH_URL}/me/messages/{email_id}/", headers=headers, json=data)


def search_emails_ai(
    access_token: str,
    max_results: int = 100,
    filenames: list = None,
    from_addresses: list = None,
    to_addresses: list = None,
    subject: str = None,
    body: str = None,
    keywords: list = None,
    date_from: str = None,
    search_in: dict = None,
) -> list:
    """
    Searches for emails matching the specified query parameters using Microsoft Graph API.

    Args:
        access_token (str): The access token for authenticating with Microsoft Graph API.
        max_results (int): The maximum number of email results to retrieve. Default is 100.
        filenames (list): A list of filenames to search for in the attachments. (TODO: Implement this)
        from_addresses (list): A list of sender email addresses to filter emails.
        to_addresses (list): A list of recipient email addresses to filter emails.
        subject (str): A subject string to filter emails.
        body (str): A body string to filter emails.
        keywords (list): A list of keywords to search for in the email body.
        date_from (str): A date string in the format 'YYYY-MM-DD' to filter emails received after this date.
        search_in (dict): A dictionary specifying the folders to search in. Possible keys are:
            spams: Search in spam/junk folder.
            deleted_emails: Search in deleted items folder.
            drafts: Search in drafts folder.
            sent_emails: Search in sent items folder.

    Returns:
        list: A list of email IDs that match the search criteria.
    """
    folder_url = f"{GRAPH_URL}me/mailFolders/"
    message_ids = []
    params = {"$top": max_results, "$select": "id", "$count": "true"}

    if from_addresses:
        from_query = " OR ".join(
            ["from/emailAddress:" + from_address for from_address in from_addresses]
        )
        params["from/emailAddress"] = from_query
    if to_addresses:
        recipient_query = " OR ".join(
            ["toRecipients/emailAddress:" + to_address for to_address in to_addresses]
        )
        params["toRecipients/emailAddress"] = recipient_query
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body
    if keywords:
        keyword_query = " OR ".join(keywords)
        params["body"] = (
            keyword_query
            if not params.get("body")
            else params["body"] + " OR " + keyword_query
        )
    if date_from:
        params["receivedDateTime"] = "gt" + date_from + "T00:00:00Z"
    if filenames:
        # TODO: first retrieve emails + filenames and then check with a for loop
        pass

    def run_request(graph_endpoint: str):
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(graph_endpoint, headers=headers, params=params)
            response.raise_for_status()
            data: dict = response.json()
            messages = data.get("value", [])
            message_ids.extend([message["id"] for message in messages])
        except Exception as e:
            LOGGER.error(f"Failed to search emails with AI filled parameters: {str(e)}")

    endpoints = {
        "spams": "junkemail/messages",
        "deleted_emails": "deleteditems/messages",
        "drafts": "drafts",
        "sent_emails": "sentitems",
    }
    for folder in search_in:
        if folder in endpoints and search_in[folder]:
            graph_endpoint = f"{folder_url}{endpoints[folder]}"
            run_request(graph_endpoint)

    graph_endpoint = f"{folder_url}inbox/messages"
    run_request(graph_endpoint)

    return message_ids


def search_emails_manually(
    access_token: str,
    search_query: str,
    max_results: int,
    file_extensions: list,
    advanced: bool = False,
    search_in: dict = None,
    from_addresses: list = None,
    to_addresses: list = None,
    subject: str = None,
    body: str = None,
    date_from: str = None,
) -> list:
    """
    Searches for emails matching the specified query parameters using Microsoft Graph API.

    Args:
        access_token (str): The access token for authenticating with Microsoft Graph API.
        search_query (str): The search query string to search for in emails.
        max_results (int): The maximum number of email results to retrieve.
        file_extensions (list): A list of file extensions to filter attachments by. (TODO: Implement this)
        advanced (bool, optional): Flag indicating whether to use advanced search options. Defaults to False.
        search_in (dict, optional): A dictionary specifying the folders to search in. Possible keys are:
            spams: Search in spam/junk folder.
            deleted_emails: Search in deleted items folder.
            drafts: Search in drafts folder.
            sent_emails: Search in sent items folder.
        from_addresses (list, optional): A list of sender email addresses to filter emails.
        to_addresses (list, optional): A list of recipient email addresses to filter emails.
        subject (str, optional): A subject string to filter emails.
        body (str, optional): A body string to filter emails.
        date_from (str, optional): A date string in the format 'YYYY-MM-DD' to filter emails received after this date.

    Returns:
        list: A list of email IDs that match the search criteria.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    folder_url = f"{GRAPH_URL}me/mailFolders/"
    graph_endpoint = f"{folder_url}inbox/messages"
    message_ids = []

    def run_request(graph_endpoint, params):
        try:
            response = requests.get(graph_endpoint, headers=headers, params=params)
            response.raise_for_status()
            data: dict = response.json()
            messages = data.get("value", [])
            message_ids.extend([message["id"] for message in messages])

        except Exception as e:
            LOGGER.error(
                f"Failed to search_emails_ai for url: {graph_endpoint}: {str(e)}"
            )

    try:
        params = {"$top": max_results, "$select": "id", "$count": "true"}

        if advanced:
            if from_addresses:
                from_query = " OR ".join(
                    [f"from/emailAddress:{address}" for address in from_addresses]
                )
                params["from/emailAddress"] = from_query
            if to_addresses:
                recipient_query = " OR ".join(
                    [f"toRecipients/emailAddress:{address}" for address in to_addresses]
                )
                params["toRecipients/emailAddress"] = recipient_query
            if subject:
                params["subject"] = subject
            if body:
                params["body"] = body
            if date_from:
                params["receivedDateTime"] = f"gt{date_from}T00:00:00Z"
            if file_extensions:
                # TODO: Retrieve emails + filenames and check with a for loop
                pass

            endpoints = {
                "spams": "junkemail/messages",
                "deleted_emails": "deleteditems/messages",
                "drafts": "drafts",
                "sent_emails": "sentitems",
            }
            for folder in search_in or []:
                if folder in endpoints and search_in[folder]:
                    endpoint = f"{folder_url}{endpoints[folder]}"
                    run_request(endpoint, params)

        else:
            filter_expression = f"""
            contains(subject,'{search_query}') or 
            contains(body/content,'{search_query}') or 
            contains(sender/emailAddress/address,'{search_query}')
            """
            params["$filter"] = filter_expression

        response = requests.get(graph_endpoint, headers=headers, params=params)
        response.raise_for_status()
        response_data: dict = response.json()
        messages = response_data.get("value", [])

        return [message["id"] for message in messages]

    except Exception as e:
        LOGGER.error(f"Failed to search emails from Microsoft API: {str(e)}")
        return []


def search_emails(access_token: str, search_query: str, max_results=2) -> dict:
    """
    Searches for emails in the user's mailbox based on the provided search query in both the subject and body.

    Args:
        access_token (str): Access token for authenticating with Microsoft Graph API.
        search_query (str): The search query string to search for in email subjects and bodies.
        max_results (int, optional): Maximum number of email results to retrieve. Defaults to 2.

    Returns:
        dict: A dictionary mapping found email addresses (keys) to corresponding sender names (values).
              Each key-value pair represents an email address and its associated sender name found in the search results.
    """
    graph_endpoint = f"{GRAPH_URL}me/messages"

    try:
        headers = get_headers(access_token)
        filter_expression = f"startswith(subject, '{search_query}') or startswith(body/content, '{search_query}')"
        params = {"$filter": filter_expression, "$top": max_results}

        response = requests.get(graph_endpoint, headers=headers, params=params)
        data: dict = response.json()
        messages: list[dict[str, dict[str, dict]]] = data.get("value", [])

        found_emails = {}

        for message in messages:
            sender: str = (
                message.get("from", {}).get("emailAddress", {}).get("address", "")
            )

            if sender:
                email = sender.lower()
                name = sender.split("@")[0].lower()

                # Additional filtering: Check if the sender email/name matches the search query
                if search_query.lower() in email or search_query.lower() in name:
                    if email and not email_processing.is_no_reply_email(email):
                        found_emails[email] = name

        return found_emails

    except Exception as e:
        LOGGER.error(
            f"Failed to search emails from Microsoft Graph API. Query: {search_query}. Error: {str(e)}"
        )
        return {}


def set_all_contacts(access_token: str, user: User):
    """
    Retrieves all unique contacts from an email account using Microsoft Graph API and stores them in the database.

    Args:
        access_token (str): Access token for authenticating with Microsoft Graph API.
        user (User): User object representing the owner of the email account.
    """
    LOGGER.info(
        f"Starting to save all contacts from user ID: {user.id} with Microsoft Graph API"
    )
    start = time.time()

    graph_api_contacts_endpoint = f"{GRAPH_URL}me/contacts"
    graph_api_messages_endpoint = f"{GRAPH_URL}me/messages?$top=500"
    headers = get_headers(access_token)

    try:
        all_contacts = defaultdict(set)

        # Part 1: Retrieve contacts from Microsoft Contacts
        response = requests.get(graph_api_contacts_endpoint, headers=headers)
        response.raise_for_status()
        response_data: dict = response.json()
        contacts: list[dict[str, dict]] = response_data.get("value", [])

        for contact in contacts:
            name = contact.get("displayName", "")
            email_address = contact.get("emailAddresses", [{}])[0].get("address", "")
            provider_id = contact.get("id", "")
            all_contacts[(user, name, email_address, provider_id)].add(email_address)

        # Part 2: Retrieve contacts from Outlook messages
        response = requests.get(graph_api_messages_endpoint, headers=headers)
        response.raise_for_status()
        data: dict = response.json()
        messages: list[dict[str, dict[str, dict]]] = data.get("value", [])

        for message in messages:
            sender: str = (
                message.get("from", {}).get("emailAddress", {}).get("address", "")
            )
            if sender:
                name = sender.split("@")[0]
                if (user, name, sender, "") in all_contacts:
                    continue
                else:
                    all_contacts[(user, name, sender, "")].add(sender)

        # Part 3: Save the contacts to the database
        for contact_info, emails in all_contacts.items():
            _, name, email_address, provider_id = contact_info
            for _ in emails:
                email_processing.save_email_sender(
                    user, name, email_address, provider_id
                )

        formatted_time = str(datetime.timedelta(seconds=time.time() - start))
        LOGGER.info(
            f"Retrieved {len(all_contacts)} unique contacts in {formatted_time} from Microsoft Graph API for user ID: {user.id}"
        )

    except Exception as e:
        LOGGER.error(
            f"Error fetching contacts from Microsoft Graph API for user ID {user.id}: {str(e)}"
        )


def parse_name_and_email(
    sender: dict[str, dict]
) -> tuple[str, str] | tuple[None, None]:
    """
    Parses the name and email address from a sender dictionary.

    Args:
        sender (dict): Dictionary containing sender information.

    Returns:
        tuple[str, str] | tuple[None, None]: Tuple containing name and email address,
                                             or (None, None) if sender information is empty.

    """
    if not sender:
        return None, None

    name = sender.get("emailAddress", {}).get("name")
    email = sender.get("emailAddress", {}).get("address")

    return name, email


def parse_recipients(recipients: list[dict[str, dict]]) -> list[tuple[str, str]]:
    """
    Parses names and email addresses from a list of recipient dictionaries.

    Args:
        recipients (list): List of dictionaries containing recipient information.

    Returns:
        list[tuple[str, str]]: List of tuples containing names and email addresses of recipients.

    """
    if not recipients:
        return []

    parsed_recipients = []
    for recipient in recipients:
        name, email = parse_name_and_email(recipient)
        parsed_recipients.append((name, email))

    return parsed_recipients


def parse_message_body(message_data: dict) -> str | None:
    """
    Parses the message body content from a message data dictionary.

    Args:
        message_data (dict): Dictionary containing message data.

    Returns:
        str | None: Message body content as string, or None if no valid content type found.

    """
    if "body" in message_data:
        body = message_data["body"]
        if body["contentType"] in ["text", "html", "multipart"]:
            return body["content"]

    return None


def get_mail_to_db(
    access_token: str, int_mail: int = None, id_mail: str = None
) -> tuple:
    """
    Retrieve email information for processing email to database.

    Args:
        access_token (str): Access token for authentication.
        int_mail (int, optional): Index of the email in the inbox to retrieve. Defaults to None.
        id_mail (str, optional): ID of the specific email message to retrieve. Defaults to None.

    Returns:
        tuple: Tuple containing email information for processing:
            str: Subject of the email.
            tuple[str, str]: Tuple containing sender name and email address.
            str: Preprocessed email content.
            str: ID of the email message.
            datetime.datetime: Sent date and time of the email.
            bool: Flag indicating whether the email has attachments.
            bool: Flag indicating whether the email is a reply ('RE:' in subject).

    """
    url = f"{GRAPH_URL}me/mailFolders/inbox/messages"
    headers = get_headers(access_token)

    if int_mail is not None:
        response = requests.get(url, headers=headers)
        response_data: dict = response.json()
        messages: list[dict] = response_data.get("value", [])

        if not messages:
            return None

        email_id = messages[int_mail]["id"]
    elif id_mail is not None:
        email_id = id_mail
    else:
        return None

    message_url = f"{url}/{email_id}"
    response = requests.get(message_url, headers=headers)
    message_data: dict = response.json()

    has_attachments = message_data["hasAttachments"]
    subject: str = message_data.get("subject")
    is_reply: bool = subject.lower().startswith("re:")
    sender = message_data.get("from")
    from_info = parse_name_and_email(sender)
    sent_date_str = message_data.get("sentDateTime")
    sent_date = None
    if sent_date_str:
        sent_date = datetime.datetime.strptime(sent_date_str, "%Y-%m-%dT%H:%M:%SZ")
        sent_date = make_aware(sent_date)
    decoded_data = parse_message_body(message_data)
    decoded_data_temp = email_processing.html_clear(decoded_data)
    preprocessed_data = email_processing.preprocess_email(decoded_data_temp)

    return (
        subject,
        from_info,
        preprocessed_data,
        email_id,
        sent_date,
        has_attachments,
        is_reply,
    )




def email_to_db(user: User, email: str, id_email: str) -> bool | str:
    """
    Saves email notifications from Microsoft Graph API listener to the database.

    Args:
        user (User): The user object for whom the email is being saved.
        email (str): The email address associated with the notification.
        id_email (str): The ID of the email notification from Microsoft Graph API.

    Returns:
        bool | str: True if the email was successfully saved, False if there was an issue saving the email,
                    or an error message if an exception occurred.
    """
    LOGGER.info(
        f"Starting the process of saving email from Microsoft Graph API to database for user ID: {user.id} and email ID: {id_email}"
    )

    social_api = get_social_api(user, email)
    access_token = refresh_access_token(social_api)

    (
        subject,
        from_name,
        decoded_data,
        email_id,
        sent_date,
        has_attachments,
        is_reply,
    ) = get_mail_to_db(access_token, None, id_email)

    if Email.objects.filter(provider_id=email_id).exists():
        return True

    sender = Sender.objects.filter(email=from_name[1]).first()

    if not decoded_data:
        LOGGER.info(
            f"No decoded data retrieved from Microsoft Graph API for user ID: {user.id} and email ID: {id_email}"
        )
        return False

    category_dict = email_processing.get_db_categories(user)
    category = Category.objects.get(name=DEFAULT_CATEGORY, user=user)
    rules = Rule.objects.filter(sender=sender)
    rule_category = None

    if rules.exists():
        for rule in rules:
            if rule.block:
                return True

            if rule.category:
                category = rule.category
                rule_category = True

    user_description = (
        social_api.user_description if social_api.user_description is not None else ""
    )
    language = Preference.objects.get(user=user).language

    if is_reply:
        # Summarize conversation with Search
        email_content = email_processing.preprocess_email(decoded_data)
        user_id = user.id
        search = Search(user_id)
        conversation_summary = search.summarize_conversation(
            subject, email_content, user_description, language
        )
    else:
        # Summarize single email with Search
        email_content = email_processing.preprocess_email(decoded_data)
        user_id = user.id
        search = Search(user_id)
        email_summary = search.summarize_email(
            subject, email_content, user_description, language
        )

    email_processed = claude.categorize_and_summarize_email(
        subject, decoded_data, category_dict, user_description, from_name[1]
    )

    priority: str = email_processed["importance"]
    topic: str = email_processed["topic"]
    answer: str = email_processed["response"]
    relevance: str = email_processed["relevance"]
    flags: dict = email_processed["flags"]
    spam: bool = flags["spam"]
    scam: bool = flags["scam"]
    newsletter: bool = flags["newsletter"]
    notification: bool = flags["notification"]
    meeting: bool = flags["meeting"]
    summary: dict = email_processed["summary"]
    short_summary: str = summary["short"]
    one_line_summary: str = summary["one_line"]

    if not rule_category:
        if topic in category_dict:
            category = Category.objects.get(name=topic, user=user)

    if not sender:
        sender_name, sender_email = from_name[0], from_name[1]
        if not sender_name:
            sender_name = sender_email

        sender = Sender.objects.filter(email=sender_email).first()
        if not sender:
            sender = Sender.objects.create(email=sender_email, name=sender_name)

    try:
        email_entry = Email.objects.create(
            social_api=social_api,
            provider_id=email_id,
            email_provider=MICROSOFT_PROVIDER,
            short_summary=short_summary,
            one_line_summary=one_line_summary,
            subject=subject,
            priority=priority,
            sender=sender,
            category=category,
            user=user,
            date=sent_date,
            has_attachments=has_attachments,
            answer=answer,
            relevance=relevance,
            spam=spam,
            scam=scam,
            newsletter=newsletter,
            notification=notification,
            meeting=meeting,
        )

        if is_reply:
            conversation_summary_category = conversation_summary["category"]
            conversation_summary_organization = conversation_summary["organization"]
            conversation_summary_topic = conversation_summary["topic"]
            keypoints: dict = conversation_summary["keypoints"]

            for index, keypoints_list in keypoints.items():
                for keypoint in keypoints_list:
                    KeyPoint.objects.create(
                        is_reply=True,
                        position=index,
                        category=conversation_summary_category,
                        organization=conversation_summary_organization,
                        topic=conversation_summary_topic,
                        content=keypoint,
                        email=email_entry,
                    )

        else:
            email_summary_category = email_summary["category"]
            email_summary_organization = email_summary["organization"]
            email_summary_topic = email_summary["topic"]

            for keypoint in email_summary["keypoints"]:
                KeyPoint.objects.create(
                    is_reply=False,
                    category=email_summary_category,
                    organization=email_summary_organization,
                    topic=email_summary_topic,
                    content=keypoint,
                    email=email_entry,
                )

        contact_name, contact_email = from_name[0], from_name[1]
        Contact.objects.get_or_create(
            user=user, email=contact_email, username=contact_name
        )

        LOGGER.info(
            f"Email ID: {id_email} saved to database successfully for user ID: {user.id} using Microsoft Graph API"
        )
        return True

    except Exception as e:
        LOGGER.error(
            f"An error occurred when trying to create an email with ID {email_id} for user ID: {user.id}: {str(e)}"
        )
        return str(e)


###########################################################################
######################## TO DELETE IN THE FUTURE ? ########################
###########################################################################
# TO DELETE IN THE FUTURE ?
def get_mail(access_token: str, int_mail: int = None, id_mail: str = None):
    """Retrieve email information for processing."""

    url = f"{GRAPH_URL}me/mailFolders/inbox/messages"
    headers = get_headers(access_token)

    if int_mail is not None:
        response = requests.get(url, headers=headers)
        response_data: dict = response.json()
        messages = response_data.get("value", [])

        if not messages:
            return None

        email_id = messages[int_mail]["id"]
    elif id_mail is not None:
        email_id = id_mail
    else:
        return None

    message_url = f"{url}/{email_id}"
    response = requests.get(message_url, headers=headers)
    message_data: dict = response.json()

    subject = message_data.get("subject")
    sender = message_data.get("from")
    from_info = parse_name_and_email(sender)
    cc_info = parse_recipients(message_data.get("ccRecipients"))
    bcc_info = parse_recipients(message_data.get("bccRecipients"))
    sent_date_str = message_data.get("sentDateTime")
    sent_date = None
    if sent_date_str:
        sent_date = datetime.datetime.strptime(sent_date_str, "%Y-%m-%dT%H:%M:%SZ")
        sent_date = make_aware(sent_date)

    for header in message_data.get("internetMessageHeaders", []):
        if header["name"] == "Date":
            sent_date = datetime.datetime.strptime(
                header["value"], "%a, %d %b %Y %H:%M:%S %z"
            )
            break

    decoded_data = parse_message_body(message_data)

    return (
        subject,
        from_info,
        decoded_data,
        cc_info,
        bcc_info,
        email_id,
        sent_date,
    )
