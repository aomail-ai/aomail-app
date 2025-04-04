"""
Contains functions for managing contacts and user profile operations for Microsoft Graph API.

Endpoints:
- ✅  get_profile_image: Retrieves the profile image URL of the user.
"""

import base64
import datetime
import logging
import time
import requests
from collections import defaultdict
from django.contrib.auth.models import User
from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from aomail.utils.security import subscription
from aomail.email_providers.microsoft.authentication import (
    get_headers,
    get_social_api,
    refresh_access_token,
)
from aomail.utils import email_processing
from aomail.constants import ALLOW_ALL, GRAPH_URL
from aomail.models import SocialAPI


######################## LOGGING CONFIGURATION ########################
LOGGER = logging.getLogger(__name__)


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
            return {"error": "Failed to get email from Microsoft API"}

    except Exception as e:
        LOGGER.error(
            f"Error retrieving user email from Microsoft API. Error: {str(e)}."
        )
        return {"error": "Internal server error"}


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


@api_view(["GET"])
@subscription(ALLOW_ALL)
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
                    {"profileImageUrl": photo_url}, status=status.HTTP_200_OK
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
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def set_all_contacts(user: User, email: str):
    """
    Stores all unique contacts from the latest 5,000 emails and contacts in the database.

    Args:
        user (User): User object representing the owner of the email account.
        email (str): Email address of the user.
    """
    LOGGER.info(
        f"Starting to save all contacts from user ID: {user.id} with Microsoft Graph API"
    )
    start = time.time()

    def refresh_and_get_headers():
        access_token = refresh_access_token(get_social_api(user, email))
        return get_headers(access_token)

    headers = refresh_and_get_headers()
    graph_api_contacts_endpoint = f"{GRAPH_URL}me/contacts"
    graph_api_messages_endpoint = f"{GRAPH_URL}me/messages?$top=100"

    try:
        all_contacts = defaultdict(set)
        message_count = 0

        def make_request(endpoint):
            nonlocal headers
            for attempt in range(2):
                response = requests.get(endpoint, headers=headers)
                if response.status_code == 401 and attempt == 0:
                    LOGGER.warning("Access token expired, attempting to refresh.")
                    headers = refresh_and_get_headers()
                else:
                    response.raise_for_status()
                    return response.json()

            LOGGER.error("Request failed after token refresh.")
            raise Exception("Token refresh failed, cannot continue request.")

        # Part 1: Retrieve contacts from Microsoft Contacts with pagination
        contacts_endpoint = graph_api_contacts_endpoint
        while contacts_endpoint:
            response_data = make_request(contacts_endpoint)
            contacts: list[dict] = response_data.get("value", [])

            for contact in contacts:
                name = contact.get("displayName", "")
                email_address = contact.get("emailAddresses", [{}])[0].get(
                    "address", ""
                )
                provider_id = contact.get("id", "")
                all_contacts[(user, name, email_address, provider_id)].add(
                    email_address
                )

            contacts_endpoint = response_data.get("@odata.nextLink")

        # Part 2: Retrieve contacts from Outlook messages with pagination, up to 5,000 messages
        messages_endpoint = graph_api_messages_endpoint
        while messages_endpoint and message_count < 5000:
            data = make_request(messages_endpoint)
            messages: list[dict] = data.get("value", [])

            for message in messages:
                if message_count >= 5000:
                    break
                sender: str = (
                    message.get("from", {}).get("emailAddress", {}).get("address", "")
                )
                if sender:
                    name = sender.split("@")[0]
                    if (user, name, sender, "") not in all_contacts:
                        all_contacts[(user, name, sender, "")].add(sender)
                message_count += 1

            messages_endpoint = data.get("@odata.nextLink")
            if not messages:
                LOGGER.info("Fewer than 5,000 messages found; stopping early.")
                break

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


def get_data(social_api: SocialAPI) -> dict:
    """
    Retrieve email statistics for a given Microsoft social API.

    Args:
        social_api (SocialAPI): The social API instance for the user.

    Returns:
        dict: A dictionary containing email statistics.
    """
    access_token = refresh_access_token(social_api)
    headers = get_headers(access_token)

    # Use the Microsoft Graph API to get counts directly
    num_emails_received = requests.get(
        f"{GRAPH_URL}/me/messages/$count", headers=headers
    ).json()
    num_emails_read = requests.get(
        f"{GRAPH_URL}/me/messages/$count?$filter=isRead eq true", headers=headers
    ).json()
    num_emails_archived = requests.get(
        f"{GRAPH_URL}/me/messages/$count?$filter=categories/any(c:c eq 'archive')",
        headers=headers,
    ).json()
    num_emails_starred = requests.get(
        f"{GRAPH_URL}/me/messages/$count?$filter=categories/any(c:c eq 'starred')",
        headers=headers,
    ).json()
    num_emails_sent = requests.get(
        f"{GRAPH_URL}/me/messages/$count?$filter=categories/any(c:c eq 'sent')",
        headers=headers,
    ).json()

    return {
        "num_emails_received": num_emails_received,
        "num_emails_read": num_emails_read,
        "num_emails_archived": num_emails_archived,
        "num_emails_starred": num_emails_starred,
        "num_emails_sent": num_emails_sent,
    }
