from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Message, Categories, Email, BulletPoints, Rules, Preferences

# link between data and API
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['text'] #get 'text' column

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        # Exclude the password or any other sensitive fields!

# Get categories name (GET)
class CategoryNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ('name',)  # We only want the name field

# Get data from email (GET)
class UserEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ('email_short_summary', 'content', 'subject', 'priority')

# Get all bullet points (GET)
class BulletPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulletPoints
        fields = '__all__'  # This will get all fields of BulletPoints

# Mark as read (POST)
class EmailReadUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ('read',)  # We only want the read field

# Mark as reply later (POST)
class EmailReplyLaterUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ('reply_later',)  # We only want the reply_later field

# Mark as blocked (POST)
class RuleBlockUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rules
        fields = ('block',)  # We only want the block field

# Send mails (POST)
class EmailDataSerializer(serializers.Serializer):
    receiver_email = serializers.EmailField()
    cc = serializers.ListField(child=serializers.EmailField(), required=False)
    cci = serializers.ListField(child=serializers.EmailField(), required=False)
    subject = serializers.CharField(required=False)
    message = serializers.CharField()
    attachments = serializers.ListField(child=serializers.FileField(), required=False)

# GET background color
class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preferences
        fields = ['bg_color']

# GET login from Users
class UserLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['login']