#!/bin/bash

# Start PostgreSQL
sudo service postgresql start

# Get the absolute path
ABS_PATH=$(pwd)

# Activate Python environment and execute backend commands
source "$ABS_PATH/backend/MailAssistant-venv/bin/activate"

# Run backend setup commands
cd backend
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py runserver_plus 9000 --cert-file creds/localhost.crt & # Run the backend server in the background
#python3 manage.py runserver 9000 &  # Run the backend server in the background

# Move to the frontend directory, install dependencies, and start the server
cd ../frontend
npm install
npm run serve