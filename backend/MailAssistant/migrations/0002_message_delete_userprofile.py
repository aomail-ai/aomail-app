# Generated by Django 4.1.10 on 2023-09-13 20:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MailAssistant', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=200)),
            ],
        ),
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
