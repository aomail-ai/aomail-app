# Generated by Django 4.1.10 on 2024-01-14 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MailAssistant', '0005_alter_socialapi_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialapi',
            name='access_token',
            field=models.CharField(max_length=2500, null=True),
        ),
        migrations.AlterField(
            model_name='socialapi',
            name='refresh_token',
            field=models.CharField(max_length=1600, null=True),
        ),
    ]
