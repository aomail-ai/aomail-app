"""
Handles user profile, email sending, and contact management operations, returns results to frontend, and saves to database.

Endpoints:
- ✅ create_sender: Create a new sender associated with the authenticated user.
- ✅ get_emails_linked: Returns the list of emails linked to the authenticated user's account.
- ✅ get_profile_image: Retrieves the profile image URL of the social API selected.
- ✅ get_user_contacts: Retrieve contacts associated with the authenticated user.
- ✅ get_user_description: Retrieves user description of the given email.
- ✅ send_email: Sends an email using the social API selected.
- ✅ update_user_description: Updates the user description of the given email.
"""

import importlib
import json
import logging
import os
import threading
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, FileResponse, Http404
from aomail.email_providers.google import authentication as auth_google
from aomail.email_providers.microsoft import authentication as auth_microsoft
from aomail.email_providers.microsoft import (
    email_operations as email_operations_microsoft,
)
from aomail.email_providers.google import (
    email_operations as email_operations_google,
)
from aomail.email_providers.imap import (
    email_operations as email_operations_imap,
)
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from aomail.utils.security import subscription
from aomail.constants import (
    ALLOW_ALL,
    ALLOWED_PLANS,
    GOOGLE,
    MEDIA_ROOT,
    MICROSOFT,
)
from aomail.models import (
    SocialAPI,
    Sender,
    Contact,
)
from aomail.utils.serializers import (
    SenderSerializer,
    ContactSerializer,
)


######################## LOGGING CONFIGURATION ########################
LOGGER = logging.getLogger(__name__)


######################## ENDPOINTS HANDLING GMAIL & OUTLOOK ########################
@api_view(["GET"])
@subscription(ALLOW_ALL)
def get_profile_image(request: Request):
    return forward_request(request._request, "profile", "get_profile_image")


@api_view(["POST"])
@subscription(ALLOW_ALL)
def send_email(request: Request):
    return forward_request(request._request, "compose_email", "send_email")


@api_view(["POST"])
@subscription(ALLOW_ALL)
def send_schedule_email(request: Request):
    return forward_request(request._request, "compose_email", "send_schedule_email")


@api_view(["POST"])
@subscription(ALLOWED_PLANS)
def check_connectivity(request: Request):
    return forward_request(request._request, "troubleshooting", "check_connectivity")


@api_view(["POST"])
@subscription(ALLOWED_PLANS)
def synchronize(request: Request):
    return forward_request(request._request, "troubleshooting", "synchronize")


def forward_request(request: HttpRequest, api_module: str, api_method: str) -> Response:
    """
    Forwards the request to the appropriate API method based on type_api.

    Args:
        request (HttpRequest): The HTTP request object containing the following parameters in the body or headers:
            email (str, optional): User's email address.
        api_module (str): The module containing the API methods.
        api_method (str): The specific API method to be called.

    Returns:
        Response: The response from the API method or an error response if
                      the API type or method is unsupported, or if the SocialAPI
                      entry is not found for the user and email.
    """
    user = request.user
    if request.method == "POST":
        content_type = request.content_type

        if content_type.startswith("application/json"):
            try:
                parameters = json.loads(request.body)
                email = parameters.get("email") or request.headers.get("email")
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid JSON in request body"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif content_type.startswith("multipart/form-data"):
            email = request.POST.get("email") or request.headers.get("email")
            parameters = request.POST.dict()
            parameters.update({"attachments": request.FILES.getlist("attachments")})
        else:
            return Response(
                {"error": "Unsupported Content-Type"},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
    elif request.method == "GET":
        email = request.headers.get("email")
    else:
        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not email:
        return Response(
            {"error": "Email is neither in body nor in headers of the request"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        social_api = SocialAPI.objects.get(user=user, email=email)
    except ObjectDoesNotExist:
        LOGGER.error(
            f"SocialAPI entry not found for the user with ID: {user.id} and email: {email}"
        )
        return Response(
            {"error": "SocialAPI entry not found for the user and email"},
            status=status.HTTP_404_NOT_FOUND,
        )

    type_api = (
        social_api.type_api
        if not (api_method == "send_email" and social_api.imap_config)
        else "smtp"
    )
    if social_api.imap_config and api_method != "send_email":
        return Response(
            {"error": "Unsupported method for IMAP"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    module_name = f"aomail.email_providers.{type_api}.{api_module}"
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, api_method):
            api_function = getattr(module, api_method)
            return api_function(request)
        else:
            return Response(
                {"error": f"Unsupported API method: {api_method}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except ImportError:
        return Response(
            {"error": f"Unsupported API: {type_api}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


######################## PICTURES ########################
def serve_image(request: HttpRequest, image_name: str) -> Response:
    """
    Serve an image file from the server's media directory.

    Args:
        request (HttpRequest): The HTTP request object that represents the client request.
        image_name (str): The name of the image file to be served.

    Returns:
        FileResponse: A file response containing the image if found and valid.

    Raises:
        Http404: If the image is not found or the image format is unsupported.
    """
    image_path = os.path.join(MEDIA_ROOT, "pictures", image_name)
    if os.path.exists(image_path):
        _, ext = os.path.splitext(image_path)
        content_type = (
            "image/jpeg"
            if ext.lower() == ".jpg"
            else "image/png" if ext.lower() == ".png" else None
        )
        if content_type:
            return FileResponse(open(image_path, "rb"), content_type=content_type)
        else:
            raise Http404("Unsupported image format")
    else:
        raise Http404("Image not found")


def serve_agent_icon(request: HttpRequest, image_name: str) -> Response:
    """
    Serve an image file from the server's media directory.

    Args:
        request (HttpRequest): The HTTP request object that represents the client request.
        image_name (str): The name of the image file to be served.

    Returns:
        FileResponse: A file response containing the image if found and valid.

    Raises:
        Http404: If the image is not found or the image format is unsupported.
    """
    image_path = os.path.join(MEDIA_ROOT, "agent_icon", image_name)
    if os.path.exists(image_path):
        _, ext = os.path.splitext(image_path)
        content_type = (
            "image/jpeg"
            if ext.lower() == ".jpg"
            else "image/png" if ext.lower() == ".png" else None
        )
        if content_type:
            return FileResponse(open(image_path, "rb"), content_type=content_type)
        else:
            LOGGER.error(
                f"Unsupported image format: {image_path} Returning default agent icon"
            )
            return FileResponse(
                open(os.getcwd() + "/aomail/assets/default-agent-icon.png", "rb"),
                content_type="image/png",
            )
    else:
        LOGGER.error(f"Image not found: {image_path} Returning default agent icon")
        return FileResponse(
            open(os.getcwd() + "/aomail/assets/default-agent-icon.png", "rb"),
            content_type="image/png",
        )


############################# CONTACT ##############################
@api_view(["GET"])
@subscription(ALLOW_ALL)
def get_user_contacts(request: HttpRequest) -> Response:
    """
    Retrieve contacts associated with the authenticated user.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: JSON response containing user's contacts or an error message if no contacts are found.
    """
    try:
        user_contacts = Contact.objects.filter(user=request.user)
    except Contact.DoesNotExist:
        return Response(
            {"error": "No contacts found"}, status=status.HTTP_404_NOT_FOUND
        )

    contacts_serializer = ContactSerializer(user_contacts, many=True)
    return Response(contacts_serializer.data, status=status.HTTP_200_OK)


######################## DATABASE OPERATIONS ########################
@api_view(["GET"])
@subscription(ALLOW_ALL)
def get_emails_linked(request: HttpRequest) -> Response:
    """
    Returns the list of emails linked to the authenticated user's account.

    Args:
        request (HttpRequest): HTTP request object from the authenticated user.

    Returns:
        Response: A list of linked emails with their type of API if the request is successful,
                      or {"error": "Details of the specific error."} if there's an issue with the retrieval.
    """
    try:
        social_apis = SocialAPI.objects.filter(user=request.user)
        emails_linked = []
        for social_api in social_apis:
            emails_linked.append(
                {
                    "email": social_api.email,
                    "typeApi": social_api.type_api,
                    "isServerConfig": social_api.imap_config != None,
                }
            )
        return Response(emails_linked, status=status.HTTP_200_OK)
    except Exception as e:
        LOGGER.error(f"Error retrieving linked emails: {str(e)}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@subscription(ALLOW_ALL)
def search_emails(request: HttpRequest) -> Response:
    """
    Searches emails based on user-specified parameters.

    Args:
        request (HttpRequest): HTTP request object containing the search parameters in the request body.
            Expects JSON body with:
                emails (list of str): List of email addresses to search.
                max_results (int): Maximum number of results to return.
                query (str): The user query for the search.
                file_extensions (list of str): List of file extensions to filter attachments.
                advanced (bool): Flag to indicate if advanced search is enabled.
                from_addresses (list of str): List of sender email addresses to filter.
                to_addresses (list of str): List of recipient email addresses to filter.
                subject (str): Subject of the emails to filter.
                body (str): Body content of the emails to filter.
                date_from (str): Start date to filter emails.
                search_in (dict): Additional search parameters.

    Returns:
        Response: A JSON response with the search results categorized by email provider and email address,
                      or {"error": "Details of the specific error."} if there's an issue with the search process.
    """
    data: dict = json.loads(request.body)
    user = request.user
    emails: list = data["emails"]
    max_results: int = data["max_results"]
    query: str = data["query"]
    file_extensions: list = data["file_extensions"]
    filenames: list = data.get("filenames", [])
    advanced: bool = data["advanced"]
    from_addresses: list = data["from_addresses"]
    to_addresses: list = data["to_addresses"]
    subject: str = data["subject"]
    body: str = data["body"]
    date_from: str = data["date_from"]
    search_in: dict = data["search_in"]

    def append_to_result(provider: str, email: str, data: list):
        if len(data) > 0:
            if provider not in result:
                result[provider] = {}
            result[provider][email] = data

    result = {}
    for email in emails:
        social_api = SocialAPI.objects.get(email=email)
        type_api = social_api.type_api

        if type_api == GOOGLE and not social_api.imap_config:
            services = auth_google.authenticate_service(user, email, ["gmail"])
            search_result = threading.Thread(
                target=append_to_result,
                args=(
                    GOOGLE,
                    email,
                    email_operations_google.search_emails_manually(
                        services,
                        query,
                        max_results,
                        file_extensions,
                        filenames,
                        advanced,
                        search_in,
                        from_addresses,
                        to_addresses,
                        subject,
                        body,
                        date_from,
                    ),
                ),
            )
        elif type_api == MICROSOFT and not social_api.imap_config:
            access_token = auth_microsoft.refresh_access_token(
                auth_microsoft.get_social_api(user, email)
            )
            search_result = threading.Thread(
                target=append_to_result,
                args=(
                    MICROSOFT,
                    email,
                    email_operations_microsoft.search_emails_manually(
                        access_token,
                        query,
                        max_results,
                        file_extensions,
                        filenames,
                        advanced,
                        search_in,
                        from_addresses,
                        to_addresses,
                        subject,
                        body,
                        date_from,
                    ),
                ),
            )
        elif social_api.imap_config:
            search_result = threading.Thread(
                target=append_to_result,
                args=(
                    social_api.type_api,
                    social_api.email,
                    email_operations_imap.search_emails_manually(
                        social_api,
                        query,
                        max_results,
                        file_extensions,
                        filenames,
                        advanced,
                        search_in,
                        from_addresses,
                        to_addresses,
                        subject,
                        body,
                        date_from,
                    ),
                ),
            )

        search_result.start()
        search_result.join()

    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
@subscription(ALLOW_ALL)
def update_user_description(request: HttpRequest) -> Response:
    """
    Updates the user description of the given email.

    Args:
        request (HttpRequest): HTTP request object containing the email and new user description.
            Expects JSON body with:
                email (str): The email associated with the user.
                user_description (str, optional): The new user description to update. Defaults to an empty string.

    Returns:
        Response: A JSON response indicating success or failure of the update operation.
    """
    data: dict = json.loads(request.body)
    user = request.user
    email = data.get("email")
    user_description = data.get("userDescription", "")

    if email:
        try:
            social_api = SocialAPI.objects.get(user=user, email=email)
            social_api.user_description = user_description
            social_api.save()
            return Response(
                {"message": "User description updated"}, status=status.HTTP_200_OK
            )
        except SocialAPI.DoesNotExist:
            return Response(
                {"error": "Email not found"}, status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
            {"error": "No email provided"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@subscription(ALLOW_ALL)
def get_user_description(request: HttpRequest) -> Response:
    """
    Retrieves user description of the given email.

    Args:
        request (HttpRequest): HTTP request object containing the email.
            Expects JSON body with:
                email (str): The email associated with the user.

    Returns:
        Response: A JSON response containing the user description if found,
                      or an error message if no email is provided or if the email is not found.
    """
    data: dict = json.loads(request.body)
    user = request.user
    email = data.get("email")

    if email:
        try:
            social_api = SocialAPI.objects.get(user=user, email=email)
            return Response(
                {"description": social_api.user_description}, status=status.HTTP_200_OK
            )
        except SocialAPI.DoesNotExist:
            return Response(
                {"error": "Email not found"}, status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
            {"error": "No email provided"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@subscription(ALLOW_ALL)
def create_sender(request: HttpRequest) -> Response:
    """
    Create a new sender associated with the authenticated user.

    Args:
        request (HttpRequest): HTTP request object containing the sender data.
            Expects JSON body with:
                email (str): The email of the sender.
                name (str): The name of the sender.

    Returns:
        Response: Either {"id": <sender_id>} if the sender is successfully created,
                      or serializer errors with status HTTP 400 Bad Request if validation fails.
    """
    data: dict = json.loads(request.body)
    serializer = SenderSerializer(data=data)

    if serializer.is_valid():
        sender = Sender.objects.create(email=data["email"], name=data["name"])
        return Response({"id": sender.id}, status=status.HTTP_201_CREATED)
    else:
        return Response(
            {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )
