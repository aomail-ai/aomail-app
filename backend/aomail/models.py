"""
Database Models with Security Measures.

Each model corresponds to a database table, storing data and implementing security measures against SQL injection attacks.
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField


class Subscription(models.Model):
    """Model for storing subscription information."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=50)
    subscription_id = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_trial = models.BooleanField(default=True)
    is_block = models.BooleanField(default=False)


class Statistics(models.Model):
    """Model for storing statistical data about emails received."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Email categories
    nb_emails_received = models.IntegerField(default=0)
    nb_emails_important = models.IntegerField(default=0)
    nb_emails_informative = models.IntegerField(default=0)
    nb_emails_useless = models.IntegerField(default=0)

    # Token usage
    nb_tokens_input = models.IntegerField(default=0)
    nb_tokens_output = models.IntegerField(default=0)

    # Answer
    nb_answer_required = models.IntegerField(default=0)
    nb_might_require_answer = models.IntegerField(default=0)
    nb_no_answer_required = models.IntegerField(default=0)

    # Relevance
    nb_highly_relevant = models.IntegerField(default=0)
    nb_possibly_relevant = models.IntegerField(default=0)
    nb_not_relevant = models.IntegerField(default=0)

    # Flags
    nb_spam = models.IntegerField(default=0)
    nb_scam = models.IntegerField(default=0)
    nb_newsletter = models.IntegerField(default=0)
    nb_notification = models.IntegerField(default=0)
    nb_meeting = models.IntegerField(default=0)


class Message(models.Model):
    """Model for storing text messages."""

    text = models.CharField(max_length=200)


class Sender(models.Model):
    """Model for storing sender information."""

    email = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)


class Contact(models.Model):
    """Stores contacts of an email account"""

    email = models.CharField(max_length=320, null=True)
    username = models.CharField(max_length=100, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider_id = models.CharField(max_length=320, null=True)


class Category(models.Model):
    """Model for storing category information."""

    name = models.CharField(max_length=50)
    description = models.TextField(max_length=300)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class Preference(models.Model):
    """Model for storing user preferences."""

    # LLM settings
    llm_provider = models.CharField(max_length=50, default="google")
    llm_model = models.CharField(max_length=50, null=True)

    # Prompts
    improve_email_draft_prompt = models.TextField(max_length=1000, null=True)
    improve_email_response_prompt = models.TextField(max_length=1000, null=True)
    categorize_and_summarize_email_prompt = models.TextField(max_length=2000, null=True)
    generate_email_response_prompt = models.TextField(max_length=1000, null=True)
    generate_email_prompt = models.TextField(max_length=1000, null=True)
    generate_response_keywords_prompt = models.TextField(max_length=1000, null=True)

    # Guidelines
    important_guidelines = models.CharField(
        max_length=1000,
        default="if it's strictly work-related AND either urgent or requires prompt business action",
    )
    informative_guidelines = models.CharField(
        max_length=1000,
        default="if it's strictly work-related AND contains company updates or non-urgent team info",
    )
    useless_guidelines = models.CharField(
        max_length=1000,
        default="it's promotional OR newsletter content (like TV shows, marketing emails, subscriptions)",
    )

    # UI / UX settings
    timezone = models.CharField(max_length=50, default="UTC")
    theme = models.CharField(max_length=50, default="light")
    language = models.CharField(max_length=50, default="american")
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class EmailServerConfig(models.Model):
    """Stores configuration details for IMAP and SMTP email servers."""

    app_password = models.CharField(max_length=2000)
    host = models.CharField(max_length=30)
    port = models.IntegerField()
    encryption = models.CharField(max_length=10)


class SocialAPI(models.Model):
    """Table that contains email credentials."""

    last_fetched_date = models.DateTimeField(auto_now=True)
    type_api = models.CharField(max_length=50)
    email = models.CharField(max_length=524, unique=True)
    access_token = models.CharField(max_length=3000)
    refresh_token = models.CharField(max_length=2000)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_description = models.CharField(max_length=200, default="")
    imap_config = models.ForeignKey(
        EmailServerConfig,
        on_delete=models.CASCADE,
        null=True,
        related_name="imap_config",
    )
    smtp_config = models.ForeignKey(
        EmailServerConfig,
        on_delete=models.CASCADE,
        null=True,
        related_name="smtp_config",
    )


class Rule(models.Model):
    """Model for storing rule information."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    logical_operator = models.CharField(max_length=3, default="AND")  # "OR" allowed

    # --- static triggers --- #
    # email triggers
    domains = ArrayField(models.CharField(max_length=30), null=True)
    sender_emails = ArrayField(models.CharField(max_length=30), null=True)
    has_attachements = models.BooleanField(null=True)
    # after AI processing triggers
    categories = ArrayField(models.CharField(max_length=30), null=True)
    priorities = ArrayField(models.CharField(max_length=30), null=True)
    answers = ArrayField(models.CharField(max_length=30), null=True)
    relevances = ArrayField(models.CharField(max_length=30), null=True)
    flags = ArrayField(models.CharField(max_length=30), null=True)
    # --- AI triggers --- #
    email_deal_with = models.CharField(max_length=1000, null=True)  # user prompt

    # --- static actions --- #
    action_transfer_recipients = ArrayField(
        models.CharField(max_length=30), null=True
    )  # list of emails
    action_set_flags = ArrayField(
        models.CharField(max_length=30), null=True
    )  # list of flags
    action_mark_as = ArrayField(
        models.CharField(max_length=30), null=True
    )  # e.g [read, answerLater, archive]
    action_delete = models.BooleanField(null=True)  # whether to delete the email or not
    action_set_category = models.ForeignKey(
        Category, on_delete=models.CASCADE, blank=True, null=True
    )
    action_set_priority = models.CharField(max_length=30, null=True)  # Important
    action_set_relevance = models.CharField(max_length=30, null=True)  # Highly Relevant
    action_set_answer = models.CharField(max_length=30, null=True)  # Answer Required

    # --- AI actions --- #
    action_reply_prompt = models.CharField(max_length=1000, null=True)  # user prompt


class MicrosoftListener(models.Model):
    """Stores information about Microsoft subscriptions"""

    subscription_id = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=320)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class GoogleListener(models.Model):
    """Stores information about Google subscriptions"""

    last_modified = models.DateTimeField(null=True)
    social_api = models.ForeignKey(
        SocialAPI,
        on_delete=models.CASCADE,
        related_name="social_api_google_listener",
        null=True,
    )


class Email(models.Model):
    """Model for storing email information."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_emails")
    social_api = models.ForeignKey(
        SocialAPI, on_delete=models.CASCADE, related_name="social_api_emails", null=True
    )
    provider_id = models.CharField(max_length=200, unique=True)
    email_provider = models.CharField(max_length=50)
    short_summary = models.TextField()
    one_line_summary = models.CharField(max_length=1000)
    html_content = models.TextField(default="")
    subject = models.CharField(max_length=800)
    priority = models.CharField(max_length=50)
    read = models.BooleanField(default=False)
    read_date = models.DateTimeField(null=True, default=None)
    archive = models.BooleanField(default=False)
    answer_later = models.BooleanField(default=False)
    sender = models.ForeignKey(
        Sender, on_delete=models.CASCADE, related_name="related_emails"
    )
    date = models.DateTimeField(null=True, blank=True)
    has_attachments = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    answer = models.CharField(max_length=50)
    relevance = models.CharField(max_length=50)
    spam = models.BooleanField(default=False)
    scam = models.BooleanField(default=False)
    newsletter = models.BooleanField(default=False)
    notification = models.BooleanField(default=False)
    meeting = models.BooleanField(default=False)


class Filter(models.Model):
    """Model for storing filter information"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    social_api = models.ForeignKey(SocialAPI, on_delete=models.CASCADE, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=25)
    important = models.BooleanField(default=False)
    informative = models.BooleanField(default=False)
    useless = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    spam = models.BooleanField(default=False)
    scam = models.BooleanField(default=False)
    newsletter = models.BooleanField(default=False)
    notification = models.BooleanField(default=False)
    meeting = models.BooleanField(default=False)
    relevance = models.CharField(max_length=50, null=True, default=True)
    answer = models.CharField(max_length=50, null=True, default=True)


class Label(models.Model):
    """Model for storing shipping label information."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_labels")
    email = models.ForeignKey(Email, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=300)
    platform = models.CharField(max_length=50)
    carrier = models.CharField(max_length=50)
    label_name = models.CharField(max_length=250)
    postage_deadline = models.DateTimeField()


class Attachment(models.Model):
    """Model for storing email attachment information."""

    email = models.ForeignKey(
        Email, on_delete=models.CASCADE, related_name="attachments"
    )
    name = models.CharField(max_length=200)
    id_api = models.CharField(max_length=500)


class CC_sender(models.Model):
    """Model for storing CC sender information."""

    email_object = models.ForeignKey(
        Email, on_delete=models.CASCADE, related_name="cc_senders"
    )
    email = models.CharField(max_length=200)
    name = models.CharField(max_length=200)


class BCC_sender(models.Model):
    """Model for storing BCC sender information."""

    email_object = models.ForeignKey(
        Email, on_delete=models.CASCADE, related_name="bcc_senders"
    )
    email = models.CharField(max_length=200)
    name = models.CharField(max_length=200)


class Picture(models.Model):
    """Model for storing pictures sender of a mail"""

    email = models.ForeignKey(
        Email, on_delete=models.CASCADE, related_name="picture_mail"
    )
    path = models.TextField()


class KeyPoint(models.Model):
    """Model for storing keypoints needed by Ao for knowledge search."""

    is_reply = models.BooleanField()
    position = models.IntegerField(null=True, default=None)
    category = models.TextField(max_length=50)
    organization = models.TextField(max_length=50)
    topic = models.TextField(max_length=50)
    content = models.TextField(max_length=50)
    email = models.ForeignKey(Email, on_delete=models.CASCADE)


class Signature(models.Model):
    """Model for storing user email signatures."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="signatures")
    social_api = models.ForeignKey(
        SocialAPI, on_delete=models.CASCADE, related_name="signatures"
    )
    signature_content = models.TextField()


class Agent(models.Model):
    """Model for storing agent information."""

    agent_name = models.CharField(max_length=255)
    agent_ai_model = models.CharField(max_length=255)
    ai_template = models.TextField(null=True, blank=True)
    email_example = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    length = models.CharField(max_length=50)
    formality = models.CharField(max_length=50)
    language = models.CharField(max_length=50)
    last_used = models.BooleanField(default=False)
    picture = models.ImageField(
        upload_to="media/agent_icon/", null=True, blank=True
    )  # To update
    icon_name = models.TextField(default="")  # img name + file ext

    def __str__(self):
        return self.agent_name

    def save(self, *args, **kwargs):
        if self.last_used:
            # Set all other agents' last_used to False
            Agent.objects.filter(user=self.user, last_used=True).update(last_used=False)
        super().save(*args, **kwargs)
