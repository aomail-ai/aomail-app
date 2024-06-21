"""
Django Rest Framework (DRF) URL Configuration for MailAssistant RESTful API.
"""

from django.urls import path
from MailAssistant.email_providers import google_api, microsoft_api
from MailAssistant.controllers import artificial_intelligence as ai
from MailAssistant.controllers import authentication as auth
from MailAssistant.controllers import categories
from .controllers import views


app_name = 'MailAssistant'

urlpatterns = [
    #----------------------- AUTHENTICATION -----------------------#
    path("reset_password/<token>/", auth.reset_password, name="reset_password"), # dev
    path("generate_reset_token/", auth.generate_reset_token, name="generate_reset_token"), # dev

    path('api/is_authenticated/', auth.is_authenticated, name='is_authenticated'), # ok
    path('api/login/', auth.login, name='login'), # ok
    path('api/token/refresh/', auth.refresh_token, name='refresh_token'), # ok
    path('api/delete_account/', auth.delete_account, name='delete_account'), # ok
    path('signup/', auth.signup, name='signup'), # ok
    path('check_username/', auth.check_username, name='check_username'), # ok
    path('user/social_api/unlink/', auth.unlink_email, name='unlink_email'), # ok
    path('user/social_api/link/', auth.link_email, name='link_email'), # ok
    #----------------------- CATEGORIES -----------------------#
    path('user/categories/', categories.get_user_categories, name='get_user_categories'), # ok
    path('api/create_category/', categories.create_category, name='create_category'), # ok
    path('api/get_category_id/', categories.get_category_id, name='get_category_id'), # ok
    path('api/update_category/', categories.update_category, name='update_category'), # ok
    path('api/delete_category/', categories.delete_category, name='delete_category'), # ok
    path('api/get_rules_linked/', categories.get_rules_linked, name='get_rules_linked'), # ok
    #----------------------- RULES -----------------------#
    path('user/rules/', views.get_user_rules, name='get_user_rules'), # ok
    path('user/rules/<int:id_rule>/', views.get_user_rule_by_id, name='get_user_rule_by_id'), # ok
    path('user/delete_rules/<int:id_rule>/', views.delete_user_rule_by_id, name='delete_user_rule_by_id'), # ok
    path('user/create_rule/', views.create_user_rule, name='create_user_rule'), # ok
    path('user/update_rule/', views.update_user_rule, name='update_user_rule'), # ok
    #----------------------- PREFERENCES -----------------------#
    path('user/preferences/update_username/', views.update_username, name='update_username'), # ok
    path('user/preferences/update_password/', views.update_password, name='update_password'), # ok

    # TO DELETE
    path('user/preferences/bg_color/', views.get_user_bg_color, name='get_user_bg_color'), # ok
    path('user/preferences/set_bg_color/', views.set_user_bg_color, name='set_bg_color'), # ok

    path('user/preferences/language/', views.get_user_language, name='get_user_language'), # ok
    path('user/preferences/set_language/', views.set_user_language, name='set_user_language'), # ok
    path('user/preferences/theme/', views.get_user_theme, name='get_user_theme'), # ok
    path('user/preferences/set_theme/', views.set_user_theme, name='set_user_theme'), # ok
    path('user/preferences/timezone/', views.get_user_timezone, name='get_user_timezone'), # ok
    path('user/preferences/set_timezone/', views.set_user_timezone, name='set_user_timezone'), # ok
    path('user/preferences/username/', views.get_user_details, name='get_user_details'), # ok    
    #----------------------- EMAILS -----------------------#
    path('user/emails/delete_emails', views.delete_emails, name='delete_emails'), # waiting for implementation in FE

    path('user/get_first_email/', views.get_first_email, name='get_first_email'), # ok
    path('user/social_api/get_profile_image/', views.get_profile_image, name='get_profile_image'), # ok
    path('user/social_api/update_user_description/', views.update_user_description, name='update_user_description'), # ok
    path('user/social_api/get_user_description/', views.get_user_description, name='get_user_description'), # ok
    path('user/get_answer_later_emails/', views.get_answer_later_emails, name='get_answer_later_emails'), # ok
    path('user/emails/', views.get_user_emails, name='get_user_emails'), # ok
    path('user/emails/<int:email_id>/mark_read/', views.set_email_read, name='set_email_read'), # ok
    path('user/emails/<int:email_id>/mark_unread/', views.set_email_unread, name='set_email_unread'), # ok
    path('user/emails/<int:email_id>/mark_reply_later/', views.set_email_reply_later, name='set_email_reply_laterr'), # ok
    path('user/emails/<int:email_id>/unmark_reply_later/', views.set_email_not_reply_later, name='set_email_not_reply_later'), # ok
    path('user/emails/<int:email_id>/block_sender/', views.set_rule_block_for_sender, name='set_rule_block_for_sender'), # ok
    path('user/emails/<int:email_id>/attachments/<str:attachment_name>/', views.retrieve_attachment_data, name='retrieve_attachment_data'), 
    path('user/emails/<int:email_id>/delete/', views.delete_email, name='delete_email'), # ok
    path('user/contacts/', views.get_user_contacts, name='get_user_contacts'), # ok
    path('user/emails_linked/', views.get_emails_linked , name='get_emails_linked'), # ok    
    path('user/search_emails/', views.search_emails , name='search_emails'), # ok
    path('user/social_api/send_email/', views.send_email, name='send_email'), # ok
    path('api/create_sender', views.create_sender, name='create_sender'), # ok
    path('api/check_sender', views.check_sender_for_user, name='check_sender_for_user'), # ok
    path('api/get_mail_by_id', views.get_mail_by_id, name='get_mail_by_id'), # ok
    #----------------------- EMAIL PICTURES -----------------------#
    path('pictures/<path:image_name>', views.serve_image, name='serve_image'), # dev
    #----------------------- ARTIFICIAL INTELLIGENCE -----------------------#
    path('api/search_emails_ai/', ai.search_emails_ai , name='search_emails_ai'), # ok
    path('api/search_tree_knowledge/', ai.search_tree_knowledge, name='search_tree_knowledge'), # ok
    path('api/find_user_ai/', ai.find_user_view_ai, name='find_user_view_ai'), # ok
    path('api/new_email_ai/', ai.new_email_ai, name='new_email_ai'), # ok
    path('api/improve_email_writing/', ai.improve_email_writing, name='improve_email_writing'), # ok
    path('api/correct_email_language/', ai.correct_email_language, name='correct_email_language'), # ok
    path('api/check_email_copywriting/', ai.check_email_copywriting, name='check_email_copywriting'), # ok
    path('api/generate_email_response_keywords/', ai.generate_email_response_keywords, name='generate_email_response_keywords'), # ok
    path('api/generate_email_answer/', ai.generate_email_answer, name='generate_email_answer'), # ok
    #----------------------- AI CONVERSATIONS EXCHANGE FE & BE -----------------------#
    path('api/get_new_email_response/', ai.get_new_email_response, name='get_new_email_response'), # ok
    path('api/improve_draft/', ai.improve_draft, name='improve_draft'), # ok
    #----------------------- OAuth 2.0 EMAIL PROVIDERS API -----------------------#
    path('microsoft/auth_url/', microsoft_api.generate_auth_url, name='microsoft_auth_url'), # ok
    path('microsoft/auth_url_link_email/', microsoft_api.auth_url_link_email, name='microsoft_auth_url_link_email'), # ok
    path('microsoft/receive_mail_notifications/', microsoft_api.MicrosoftEmailNotification.as_view(), name='receive_mail_notifications'), # ok
    path('microsoft/receive_contact_notifications/', microsoft_api.MicrosoftContactNotification.as_view(), name='receive_contact_notifications'), # ok
    path('microsoft/receive_subscription_notifications/', microsoft_api.MicrosoftSubscriptionNotification.as_view(), name='receive_subscription_notifications'), # ok
    path('google/auth_url/', google_api.generate_auth_url, name='google_auth_url'), # ok
    path('google/auth_url_link_email/', google_api.auth_url_link_email, name='google_auth_url_link_email'), # ok
    path('google/receive_mail_notifications/', google_api.receive_mail_notifications, name='google_receive_mail_notifications'), # ok
    #----------------------- PAYMENT PROVIDER API -----------------------#
    path('stripe/receive_payment_notifications/', views.receive_payment_notifications, name='stripe_receive_payment_notifications'), # dev
]