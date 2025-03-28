"""
Handles webhook notifications from Microsoft Graph API.

Endpoints:
- ✅ MicrosoftSubscriptionNotification: Handles POST requests containing subscription notifications.
- ✅ MicrosoftEmailNotification: Handles email notifications from subscriptions.
- ✅ MicrosoftContactNotification: Handles POST requests containing contact notifications.
"""

import datetime
import json
import logging
import threading
import requests
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.views import View
from rest_framework.response import Response
from aomail.email_providers.microsoft.authentication import (
    get_headers,
    get_social_api,
    refresh_access_token,
)
from aomail.utils import email_processing
from aomail.constants import (
    BASE_URL,
    GRAPH_URL,
    MICROSOFT_CLIENT_STATE,
)
from aomail.models import (
    Contact,
    Email,
    MicrosoftListener,
    SocialAPI,
    Subscription,
)
from aomail.email_providers.utils import email_to_db
from aomail.email_providers.microsoft import webhook as webhook_microsoft


######################## LOGGING CONFIGURATION ########################
LOGGER = logging.getLogger(__name__)


def calculate_expiration_date(days=0, hours=0, minutes=0) -> str:
    """
    Returns the expiration date as a string formatted in UTC.

    Args:
        days (int, optional): Number of days to add.
        hours (int, optional): Number of hours to add.
        minutes (int, optional): Number of minutes to add.

    Returns:
        str: Formatted expiration date string in UTC.
    """
    expiration_date = datetime.datetime.now() + datetime.timedelta(
        days=days, hours=hours, minutes=minutes
    )
    expiration_date_str = expiration_date.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    return expiration_date_str


def check_and_resubscribe_to_missing_resources(user: User, email: str):
    """
    Check all subscriptions for the given user and resubscribe to missing resources (email or contacts).

    Args:
        user (User): The Django User object.
        email (str): The email address of the user.
    """
    url = f"{GRAPH_URL}subscriptions"
    access_token = refresh_access_token(get_social_api(user, email))
    headers = get_headers(access_token)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        subscription_data = response.json()

        active_email_subscription = False
        active_contact_subscription = False

        for subscription in subscription_data["value"]:
            resource = subscription.get("resource", "")

            if "me/mailFolders('inbox')/messages" in resource:
                active_email_subscription = True
            if "me/contacts" in resource:
                active_contact_subscription = True

        if not active_email_subscription:
            webhook_microsoft.subscribe_to_email_notifications(user, email)

        if not active_contact_subscription:
            webhook_microsoft.subscribe_to_contact_notifications(user, email)

    else:
        LOGGER.error(
            f"Failed to fetch subscriptions. Status code: {response.status_code}"
        )


def subscribe_to_email_notifications(user: User, email: str) -> bool:
    """
    Subscribe the user to email notifications via Microsoft Graph API.

    Args:
        user (User): The Django User object.
        email (str): The email address of the user.

    Returns:
        bool: True if subscription was successful, False otherwise.
    """
    LOGGER.info(
        f"Initiating subscription to Microsoft email notifications for user ID: {user.id} with email: {email}"
    )
    access_token = refresh_access_token(get_social_api(user, email))
    notification_url = f"{BASE_URL}aomail/microsoft/receive_mail_notifications/"
    lifecycle_notification_url = (
        f"{BASE_URL}aomail/microsoft/receive_subscription_notifications/"
    )
    subscription_body = {
        "changeType": "created,deleted",
        "notificationUrl": notification_url,
        "lifecycleNotificationUrl": lifecycle_notification_url,
        "resource": "me/mailFolders('inbox')/messages",
        "expirationDateTime": calculate_expiration_date(minutes=4230),
        "clientState": MICROSOFT_CLIENT_STATE,
    }
    url = f"{GRAPH_URL}subscriptions"
    headers = get_headers(access_token)

    try:
        response = requests.post(url, json=subscription_body, headers=headers)

        if not status.is_success(response.status_code):
            LOGGER.error(
                f"Failed to subscribe to Microsoft email notifications for user with ID: {user.id} and email {email}: {response.reason}"
            )
            return False

        response_data = response.json()

        social_api = SocialAPI.objects.get(user=user, email=email)
        subscription_id = response_data["id"]

        MicrosoftListener.objects.create(
            subscription_id=subscription_id,
            user=social_api.user,
            email=email,
        )

        if response.status_code == 201:
            LOGGER.info(
                f"Successfully subscribed user ID: {user.id} to Microsoft email notifications"
            )
            return True
        else:
            LOGGER.error(
                f"Failed to subscribe to Microsoft email notifications for user with ID: {user.id} and email {email}: {response.reason}"
            )
            return False

    except Exception as e:
        LOGGER.error(
            f"An error occurred while subscribing to Microsoft email notifications for user ID: {user.id}: {str(e)}"
        )
        return False


def subscribe_to_contact_notifications(user: User, email: str) -> bool:
    """
    Subscribe the user to contact notifications via Microsoft Graph API.

    Args:
        user (User): The Django User object.
        email (str): The email address of the user.

    Returns:
        bool: True if subscription was successful, False otherwise.
    """
    LOGGER.info(
        f"Initiating subscription to Microsoft contact notifications for user ID: {user.id} with email: {email}"
    )
    access_token = refresh_access_token(get_social_api(user, email))
    notification_url = f"{BASE_URL}aomail/microsoft/receive_contact_notifications/"
    lifecycle_notification_url = (
        f"{BASE_URL}aomail/microsoft/receive_subscription_notifications/"
    )
    subscription_body = {
        "changeType": "created,updated,deleted",
        "notificationUrl": notification_url,
        "lifecycleNotificationUrl": lifecycle_notification_url,
        "resource": "me/contacts",
        "expirationDateTime": calculate_expiration_date(minutes=4230),
        "clientState": MICROSOFT_CLIENT_STATE,
    }
    url = f"{GRAPH_URL}subscriptions"
    headers = get_headers(access_token)

    try:
        response = requests.post(url, json=subscription_body, headers=headers)
        response_data = response.json()

        social_api = SocialAPI.objects.get(user=user, email=email)
        subscription_id = response_data["id"]

        MicrosoftListener.objects.create(
            subscription_id=subscription_id,
            user=social_api.user,
            email=email,
        )

        if response.status_code == 201:
            LOGGER.info(
                f"Successfully subscribed user ID: {user.id} to Microsoft contact notifications"
            )
            return True
        else:
            LOGGER.error(
                f"Failed to subscribe to Microsoft contact notifications for user with ID: {user.id} and email {email}: {response.reason}"
            )
            return False

    except Exception as e:
        LOGGER.error(
            f"An error occurred while subscribing to Microsoft contact notifications for user ID: {user.id}: {str(e)}"
        )
        return False


def delete_subscription(user: User, email: str, subscription_id: str) -> bool:
    """
    Delete a subscription via Microsoft Graph API.

    Args:
        user (User): The Django User object.
        email (str): The email address of the user.
        subscription_id (str): The ID of the subscription to delete.

    Returns:
        bool: True if subscription deletion was successful, False otherwise.
    """
    LOGGER.info(
        f"Initiating Microsoft unsubscription for user ID: {user.id} and subscription ID: {subscription_id}"
    )
    access_token = refresh_access_token(get_social_api(user, email))
    headers = get_headers(access_token)
    url = f"{GRAPH_URL}subscriptions/{subscription_id}"

    try:
        response = requests.delete(url, headers=headers)

        if response.status_code != 204:
            LOGGER.error(
                f"Failed to delete the subscription {subscription_id} for user ID: {user.id}: {response.content}"
            )
            return False
        else:
            LOGGER.info(f"Successfully deleted the subscription for user ID: {user.id}")
            return True

    except Exception as e:
        LOGGER.error(
            f"Failed to delete the subscription {subscription_id} for user ID: {user.id}: {str(e)}"
        )
        return False


def renew_subscription(user: User, email: str, subscription_id: str):
    """
    Renew a Microsoft subscription.

    Args:
        user (User): The Django User object.
        email (str): The email address of the user.
        subscription_id (str): The ID of the subscription to renew.
    """
    LOGGER.info(
        f"Initiating renewal of Microsoft subscription for user ID: {user.id} and subscription ID: {subscription_id}"
    )
    access_token = refresh_access_token(get_social_api(user, email))
    headers = get_headers(access_token)
    url = f"{GRAPH_URL}subscriptions/{subscription_id}"
    new_expiration_date = calculate_expiration_date(minutes=4_230)

    try:
        payload = {"expirationDateTime": new_expiration_date}
        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            LOGGER.info(
                f"Successfully renewed the subscription for user ID: {user.id} and subscription ID: {subscription_id}"
            )
        else:
            LOGGER.error(
                f"Failed to renew the subscription {subscription_id} for user ID: {user.id}: {response.content}"
            )

    except Exception as e:
        LOGGER.error(
            f"Failed to renew the subscription {subscription_id} for user ID: {user.id}: {str(e)}"
        )


def reauthorize_subscription(user: User, email: str, subscription_id: str):
    """
    Reauthorize a Microsoft subscription.

    Args:
        user (User): The Django User object.
        email (str): The email address of the user.
        subscription_id (str): The ID of the subscription to reauthorize.
    """
    LOGGER.info(
        f"Initiating reauthorization of Microsoft subscription for user ID: {user.id} and subscription ID: {subscription_id}"
    )
    access_token = refresh_access_token(get_social_api(user, email))
    headers = get_headers(access_token)

    try:
        url = f"{GRAPH_URL}subscriptions/{subscription_id}/reauthorize"
        response = requests.post(url, headers=headers)

        if response.status_code == 200:
            LOGGER.info(
                f"Successfully reauthorized the subscription for user ID: {user.id} and subscription ID: {subscription_id}"
            )
        else:
            LOGGER.error(
                f"Failed to reauthorize the subscription {subscription_id} for user ID: {user.id}: {response.reason}"
            )

    except Exception as e:
        LOGGER.error(
            f"Failed to reauthorize the subscription {subscription_id} for user ID: {user.id}: {str(e)}"
        )


@method_decorator(csrf_exempt, name="dispatch")
class MicrosoftSubscriptionNotification(View):
    """
    Handles subscription expiration notifications from Microsoft Graph API.

    This view processes incoming subscription notifications,
    including renewing or reauthorizing subscriptions and handling lifecycle events.

    Methods:
        post(request: HttpRequest): Handles HTTP POST requests containing subscription notifications.
    """

    def post(self, request: HttpRequest) -> Response:
        """
        Handles POST requests containing subscription notifications from Microsoft Graph API.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: JSON response indicating the status of the notification processing.
                Returns a validation token if present or an error response for any issues encountered.
        """
        validation_token = request.GET.get("validationToken")
        if validation_token:
            return HttpResponse(validation_token, content_type="text/plain")

        try:
            subscription_data = json.loads(request.body.decode("utf-8"))

            if subscription_data["value"][0]["clientState"] == MICROSOFT_CLIENT_STATE:
                lifecycle_event = subscription_data["value"][0]["lifecycleEvent"]
                expiration_date_str = subscription_data["value"][0][
                    "subscriptionExpirationDateTime"
                ]
                subscription_expiration_date = datetime.datetime.fromisoformat(
                    expiration_date_str
                )
                subscription_id = subscription_data["value"][0]["subscriptionId"]
                microsoft_listener = MicrosoftListener.objects.filter(
                    subscription_id=subscription_id
                )
                current_datetime = datetime.datetime.now(datetime.timezone.utc)
                subscription = Subscription.objects.get(
                    user=microsoft_listener.first().user
                )

                if not microsoft_listener.exists():
                    pass
                elif subscription.is_block:
                    LOGGER.info(
                        f"User with email: {microsoft_listener.first().email} is blocked. Unsubscribing user from subscription {subscription_id}."
                    )
                    delete_subscription(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                        microsoft_listener.first().subscription_id,
                    )
                elif (
                    subscription_expiration_date - current_datetime
                    <= datetime.timedelta(minutes=15)
                ):
                    renew_subscription(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                        subscription_id,
                    )
                elif lifecycle_event == "reauthorizationRequired":
                    reauthorize_subscription(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                        subscription_id,
                    )

                elif (
                    lifecycle_event == "subscriptionRemoved"
                    or lifecycle_event == "missed"
                ):
                    LOGGER.error(
                        f"{lifecycle_event}: current time: {current_datetime}, expiration time: {expiration_date_str}"
                    )
                    check_and_resubscribe_to_missing_resources(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                    )

            return JsonResponse(
                {"status": "Notification received"}, status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            LOGGER.error(
                f"An error occurred in handling subscription notification: {str(e)}"
            )
            return JsonResponse(
                {"error": "Internal Server Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class MicrosoftEmailNotification(View):
    """
    Handles email notifications from Microsoft Graph API subscriptions.

    This view processes incoming email notifications, including storing emails in the database
    and handling errors related to email processing.

    Methods:
        post(request: HttpRequest) -> Response: Handles HTTP POST requests containing email notifications.
    """

    def post(self, request: HttpRequest) -> Response:
        """
        Handles POST requests containing email notifications from Microsoft Graph API.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: JSON response indicating the status of the notification processing.
                Returns a validation token if present, or an error response for any issues encountered.
        """
        validation_token = request.GET.get("validationToken")
        if validation_token:
            return HttpResponse(validation_token, content_type="text/plain")

        try:
            LOGGER.info(
                "Email notification received from Microsoft Graph API. Starting email processing"
            )

            email_data = json.loads(request.body.decode("utf-8"))

            if email_data["value"][0]["clientState"] == MICROSOFT_CLIENT_STATE:
                change_type = email_data["value"][0]["changeType"]
                email_id = email_data["value"][0]["resourceData"]["id"]
                subscription_id = email_data["value"][0]["subscriptionId"]
                microsoft_listener = MicrosoftListener.objects.filter(
                    subscription_id=subscription_id
                )
                subscription = Subscription.objects.get(
                    user=microsoft_listener.first().user
                )

                if not microsoft_listener.exists():
                    pass
                elif subscription.is_block:
                    LOGGER.info(
                        f"User with email: {microsoft_listener.first().email} is blocked. Unsubscribing user from subscription {subscription_id}."
                    )
                    delete_subscription(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                        microsoft_listener.first().subscription_id,
                    )
                elif change_type == "deleted":
                    Email.objects.get(provider_id=email_id).delete()
                else:
                    social_api = get_social_api(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                    )
                    threading.Thread(
                        target=email_to_db, args=(social_api, email_id)
                    ).start()

                return JsonResponse(
                    {"status": "Notification received"}, status=status.HTTP_202_ACCEPTED
                )
            else:
                LOGGER.error("Invalid client state in email notification")
                return JsonResponse(
                    {"error": "Invalid client state in email notification"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            LOGGER.error(f"An error occurred in handling email notification: {str(e)}")
            return JsonResponse(
                {"error": "Internal Server Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class MicrosoftContactNotification(View):
    """
    Handles notifications for Microsoft contact changes from Microsoft Graph API subscriptions.

    This view processes incoming contact notifications, including storing contacts in the database,
    updating existing contacts, or deleting contacts based on the notification type.

    Methods:
        post(request: HttpRequest) -> Response:
            Handles HTTP POST requests containing contact notifications.
    """

    def post(self, request: HttpRequest) -> Response:
        """
        Handles POST requests containing contact notifications from Microsoft Graph API.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: JSON response indicating the status of the notification processing.
                Returns a validation token if present, or an error response for any issues encountered.
        """
        validation_token = request.GET.get("validationToken")
        if validation_token:
            return HttpResponse(validation_token, content_type="text/plain")

        try:
            LOGGER.info(
                "Contact notification received from Microsoft Graph API. Starting contact processing..."
            )

            contact_data = json.loads(request.body.decode("utf-8"))

            if contact_data["value"][0]["clientState"] == MICROSOFT_CLIENT_STATE:
                id_contact = contact_data["value"][0]["resourceData"]["id"]
                subscription_id = contact_data["value"][0]["subscriptionId"]
                microsoft_listener = MicrosoftListener.objects.filter(
                    subscription_id=subscription_id
                )
                change_type = contact_data["value"][0]["changeType"]
                subscription = Subscription.objects.get(
                    user=microsoft_listener.first().user
                )

                if not microsoft_listener.exists():
                    pass
                elif subscription.is_block:
                    LOGGER.info(
                        f"User with email: {microsoft_listener.first().email} is blocked. Unsubscribing user from subscription {subscription_id}."
                    )
                    delete_subscription(
                        microsoft_listener.first().user,
                        microsoft_listener.first().email,
                        microsoft_listener.first().subscription_id,
                    )
                elif change_type == "deleted":
                    contact = Contact.objects.get(provider_id=id_contact)
                    contact.delete()
                else:
                    access_token = refresh_access_token(
                        get_social_api(
                            microsoft_listener.first().user,
                            microsoft_listener.first().email,
                        )
                    )
                    url = f"https://graph.microsoft.com/v1.0/me/contacts/{id_contact}"
                    headers = get_headers(access_token)

                    try:
                        response = requests.get(url, headers=headers)

                        if response.status_code == 200:
                            contact_data: dict[str, dict[str, dict]] = response.json()
                            name = contact_data.get("displayName")
                            email = contact_data.get("emailAddresses")[0].get("address")

                            if change_type == "created":
                                email_processing.save_email_sender(
                                    microsoft_listener.first().user,
                                    name,
                                    email,
                                    id_contact,
                                )

                            if change_type == "updated":
                                contact = Contact.objects.get(provider_id=id_contact)
                                contact.username = name
                                contact.email = email
                                contact.save()

                        else:
                            LOGGER.error(
                                f"Failed to retrieve contact data: {response.reason}"
                            )
                            return Response(
                                {
                                    "error": f"Failed to retrieve contact data: {response.reason}"
                                },
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )

                    except Exception as e:
                        LOGGER.error(
                            f"An error occurred in handling contact notification: {str(e)}"
                        )
                        return JsonResponse(
                            {"error": "Internal server error"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                return JsonResponse(
                    {"status": "Notification received"},
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                LOGGER.error("Invalid client state in contact notification")
                return JsonResponse(
                    {"error": "Invalid client state in contact notification"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            LOGGER.error(
                f"An error occurred in handling contact notification: {str(e)}"
            )
            return JsonResponse(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
