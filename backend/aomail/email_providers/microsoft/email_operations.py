"""
Provides email search and operation functions using Microsoft Graph API.
"""

import datetime
import logging
import requests
from django.utils.timezone import make_aware
from django.contrib.auth.models import User
from aomail.email_providers.microsoft.authentication import (
    get_headers,
    get_social_api,
    refresh_access_token,
)
from aomail.utils import email_processing
from aomail.constants import GRAPH_URL
from aomail.models import Attachment, Email, SocialAPI


######################## LOGGING CONFIGURATION ########################
LOGGER = logging.getLogger(__name__)


def parse_name_and_email(
    sender: dict[str, dict],
) -> tuple[str, str] | tuple[None, None]:
    """
    Parses the name and email address from a sender dictionary.

    Args:
        sender (dict): Dictionary containing sender information.

    Returns:
        tuple: Tuple containing name and email address
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


def delete_email(social_api: SocialAPI, email_id: str) -> dict:
    """
    Moves the email to the bin of the user using the Microsoft Graph API.

    Args:
        social_api (SocialAPI): The SocialAPI instance containing the user's access and refresh tokens.
        email_id (str): The ID of the email to be moved to the bin.

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
    file_extensions: list[str] = None,
    filenames: list[str] = None,
    from_addresses: list[str] = None,
    to_addresses: list[str] = None,
    subject: str = None,
    body: str = None,
    keywords: list[str] = None,
    date_from: str = None,
    search_in: dict = None,
) -> list[str]:
    """
    Searches for emails matching the specified query parameters using Microsoft Graph API.

    Args:
        access_token (str): The access token for authenticating with Microsoft Graph API.
        max_results (int): The maximum number of email results to retrieve. Default is 100.
        filenames (list): A list of filenames to search for in the attachments.
        file_extensions (list): A list of file extensions to filter attachments.
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

    # Populate search parameters
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
        params["receivedDateTime"] = f"gt{date_from}T00:00:00Z"

    def run_request(graph_endpoint: str):
        """Function to run the email search request"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(graph_endpoint, headers=headers, params=params)
            response.raise_for_status()
            data: dict = response.json()
            messages = data.get("value", [])
            message_ids.extend([message["id"] for message in messages])
        except Exception as e:
            LOGGER.error(f"Failed to search emails with AI filled parameters: {str(e)}")

    # Build folder endpoints
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

    # Also search in the inbox if specified
    if not any(search_in.values()):
        graph_endpoint = f"{folder_url}inbox/messages"
        run_request(graph_endpoint)

    if not filenames and not file_extensions:
        return message_ids

    # Filter messages by attachment criteria (filenames and extensions)
    filtered_message_ids = []

    for email_id in message_ids:
        attachments = fetch_attachments(access_token, email_id)

        # Check if any attachment matches the filename or extension criteria
        for attachment in attachments:
            attachment_name = attachment.get("attachmentName", "")
            attachment_extension = (
                attachment_name.split(".")[-1].lower() if "." in attachment_name else ""
            )

            # Check filename matches, if specified
            name_matches = filenames is None or any(
                attachment_name == filename for filename in filenames
            )
            # Check extension matches, if specified
            ext_matches = file_extensions is None or any(
                attachment_extension == ext.lower() for ext in file_extensions
            )

            # If either name and extension match, add this email_id to filtered list
            if name_matches and ext_matches:
                filtered_message_ids.append(email_id)
                break

    return filtered_message_ids


def search_emails_manually(
    access_token: str,
    search_query: str = "",
    max_results: int = 100,
    file_extensions: list[str] = None,
    filenames: list[str] = None,
    advanced: bool = False,
    search_in: dict = None,
    from_addresses: list[str] = None,
    to_addresses: list[str] = None,
    subject: str = None,
    body: str = None,
    date_from: str = None,
) -> list[str]:
    """
    Manually searches for emails using the specified query parameters with AND logic for attachments.

    Args:
        access_token (str): Access token for authenticating with Microsoft Graph API.
        search_query (str, optional): General search string to look for in emails.
        max_results (int, optional): The maximum number of email results to retrieve. Default is 100.
        file_extensions (list, optional): List of file extensions to filter attachments.
        filenames (list, optional): List of filenames to filter attachments.
        advanced (bool, optional): If True, applies advanced search parameters. Defaults to False.
        search_in (dict, optional): Dictionary specifying folders to search in.
        from_addresses (list, optional): List of sender email addresses to filter emails.
        to_addresses (list, optional): List of recipient email addresses to filter emails.
        subject (str, optional): Subject to filter emails.
        body (str, optional): Body content to filter emails.
        date_from (str, optional): Filter emails received after this date.

    Returns:
        list[str]: A list of email IDs that match the criteria.
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
                f"Failed to search_emails_manually for url: {graph_endpoint}: {str(e)}"
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
            # Simple search using `search_query`
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
        message_ids.extend([message["id"] for message in messages])

        # If no filename or extension filtering is specified, return results directly
        if not filenames and not file_extensions:
            return message_ids

        # Filter messages by attachment criteria (both filenames and extensions required if specified)
        filtered_message_ids = []

        for email_id in message_ids:
            attachments = fetch_attachments(access_token, email_id)

            for attachment in attachments:
                attachment_name = attachment.get("attachmentName", "")
                attachment_extension = (
                    attachment_name.split(".")[-1].lower()
                    if "." in attachment_name
                    else ""
                )

                # Check if both filename and extension criteria are satisfied
                name_matches = filenames is None or any(
                    attachment_name == filename for filename in filenames
                )
                ext_matches = file_extensions is None or any(
                    attachment_extension == ext.lower() for ext in file_extensions
                )

                # If both conditions are met, consider this email ID a match
                if name_matches and ext_matches:
                    filtered_message_ids.append(email_id)
                    break

        return filtered_message_ids

    except Exception as e:
        LOGGER.error(f"Failed to search emails from Microsoft API: {str(e)}")
        return []


def get_demo_list(user: User, email: str) -> list[str]:
    """
    Retrieves a list of up to 5 email message IDs from the user's Microsoft Outlook inbox.

    Args:
        user (User): The user object representing the email account owner.
        email (str): The email address of the user.

    Returns:
        list[str]: A list of up to 10 email message IDs from the inbox.
                   Returns an empty list if no messages are found.
    """
    url = f"{GRAPH_URL}me/mailFolders/inbox/messages"
    access_token = refresh_access_token(get_social_api(user, email))
    headers = get_headers(access_token)

    params = {
        "$top": 5,
        "$select": "id",
    }
    response = requests.get(url, headers=headers, params=params)
    messages = response.json().get("value", [])

    return [msg["id"] for msg in messages] if messages else []


def fetch_attachments(social_api: SocialAPI, email_id: str) -> list:
    """
    Fetch attachments for a given email by ID.

    Args:
        social_api (SocialAPI): SocialAPI object containing authentication information.
        email_id (str): ID of the specific email message.

    Returns:
        list: List of dictionaries, each containing 'attachmentId' and 'attachmentName'.
    """
    access_token = refresh_access_token(social_api)
    headers = get_headers(access_token)

    attachments_url = f"{GRAPH_URL}me/messages/{email_id}/attachments"
    response = requests.get(attachments_url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch attachments: {response.status_code}, {response.text}"
        )

    attachment_data = response.json().get("value", [])
    attachments = [
        {"attachmentId": att["id"], "attachmentName": att["name"]}
        for att in attachment_data
    ]

    return attachments


def get_mail_to_db(social_api: SocialAPI, email_id: str) -> dict:
    """
    Retrieve email information for processing email to database.

    Args:
        social_api (SocialAPI): SocialAPI object containing authentication information.
        email_id (str): ID of the specific email message to retrieve.

    Returns:
        dict: Dictionary containing email information for processing:
            str: Subject of the email.
            tuple[str, str]: Tuple containing sender name and email address.
            str: Preprocessed email content.
            str: ID of the email message.
            datetime.datetime: Sent date and time of the email.
            bool: Flag indicating whether the email has attachments.
            bool: Flag indicating whether the email is a reply ('RE:' in subject).
            list[dict]: List of dictionaries containing details about each attachment (ID and name).
    """
    url = f"{GRAPH_URL}me/messages/{email_id}"
    access_token = refresh_access_token(social_api)
    headers = get_headers(access_token)

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch email: {response.status_code}, {response.text}"
        )

    message_data: dict = response.json()

    has_attachments = message_data.get("hasAttachments", False)
    subject: str = message_data.get("subject", "")
    is_reply: bool = subject.lower().startswith("re:")
    sender = message_data.get("from", {})
    from_info = parse_name_and_email(sender)

    # Handling CC and BCC recipients
    cc_info = [
        parse_name_and_email(recipient)
        for recipient in message_data.get("ccRecipients", [])
    ]
    bcc_info = [
        parse_name_and_email(recipient)
        for recipient in message_data.get("bccRecipients", [])
    ]

    # Parse the sent date
    sent_date_str = message_data.get("sentDateTime")
    sent_date = (
        make_aware(datetime.datetime.strptime(sent_date_str, "%Y-%m-%dT%H:%M:%SZ"))
        if sent_date_str
        else None
    )

    # Retrieve attachments if they exist
    attachments = fetch_attachments(social_api, email_id) if has_attachments else []

    # Process the email body
    decoded_data = parse_message_body(message_data)
    cleaned_html = email_processing.html_clear(decoded_data)
    preprocessed_data = email_processing.preprocess_email(cleaned_html)

    return {
        "subject": subject,
        "from_info": from_info,
        "preprocessed_data": preprocessed_data,
        "safe_html": decoded_data,
        "email_id": email_id,
        "sent_date": sent_date,
        "has_attachments": has_attachments,
        "is_reply": is_reply,
        "cc_info": cc_info,
        "bcc_info": bcc_info,
        "image_files": [],
        "attachments": attachments,
    }


def get_mail(access_token: str, int_mail: int = None, id_mail: str = None) -> tuple:
    """
    Retrieve email information for processing.

    Args:
        access_token (str): The access token for authenticating with the Microsoft Graph API.
        int_mail (int, optional): The zero-based index to retrieve the nth email from the inbox.
                                  If provided, this takes precedence over the `id_mail` parameter.
        id_mail (str, optional): The unique identifier of a specific email message to retrieve.
                                 Used if `int_mail` is not provided.

    Returns:
        tuple: A tuple containing the following information about the email:
            - subject (str): The subject line of the email.
            - from_info (tuple[str, str]): A tuple containing the sender's name and email address in the format (name, email).
            - decoded_data (str): The processed content of the email body, after parsing and any necessary preprocessing.
            - cc_info (list[tuple[str, str]]): A list of tuples with names and email addresses of CC (carbon copy) recipients.
            - bcc_info (list[tuple[str, str]]): A list of tuples with names and email addresses of BCC (blind carbon copy) recipients.
            - email_id (str): The unique ID of the email message.
            - sent_date (datetime.datetime): The sent date and time of the email, converted to an aware datetime object.

    Returns:
        None: If neither `int_mail` nor `id_mail` is specified, if no email is found with the provided index or ID, or if a request error occurs.
    """
    url = f"{GRAPH_URL}me/mailFolders/inbox/messages"
    headers = get_headers(access_token)

    if int_mail:
        response = requests.get(url, headers=headers)
        response_data: dict = response.json()
        messages = response_data.get("value", [])

        if not messages:
            return None

        email_id = messages[int_mail]["id"]
    elif id_mail:
        email_id = id_mail

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


def get_attachment_data(
    social_api: SocialAPI, email_id: str, attachment_name: str
) -> dict:
    """
    Retrieves the data for a specific attachment from an email using the Microsoft Graph API.

    Args:
        social_api (SocialAPI): SocialAPI object containing authentication information.
        email_id (str): The ID of the email containing the attachment.
        attachment_name (str): The name of the attachment to retrieve.

    Returns:
        dict: A dictionary containing:
            - attachmentName (str): The name of the attachment.
            - data (bytes): The attachment data.
            - Returns an empty dictionary if the attachment is not found.
    """
    try:
        access_token = refresh_access_token(social_api)
        headers = get_headers(access_token)

        email = Email.objects.get(user=social_api.user, provider_id=email_id)
        attachment = Attachment.objects.get(email=email, name=attachment_name)

        attachment_url = (
            f"{GRAPH_URL}me/messages/{email_id}/attachments/{attachment.id_api}/$value"
        )
        response = requests.get(attachment_url, headers=headers)

        if response.status_code != 200:
            LOGGER.error(
                f"Failed to retrieve attachment data: {response.status_code}, {response.text}"
            )
            return {}

        return {
            "attachmentName": attachment_name,
            "data": response.content,
        }

    except Email.DoesNotExist:
        LOGGER.error(f"No email found with ID {email_id}.")
        return {}

    except Attachment.DoesNotExist:
        LOGGER.error(
            f"No attachment found with name '{attachment_name}' for email ID {email_id}."
        )
        return {}

    except requests.RequestException as e:
        LOGGER.error(f"HTTP request failed: {str(e)}")
        return {}

    except Exception as e:
        LOGGER.error(
            f"Failed to get attachment data for email ID {email_id} and attachment '{attachment_name}': {str(e)}"
        )
        return {}
