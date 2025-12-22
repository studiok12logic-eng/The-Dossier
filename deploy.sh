#!/bin/bash

echo "Starting deployment..."

# Pull latest changes
echo "Pulling latest from git..."
git pull origin main

# Install dependencies
echo "Installing dependencies..."
./venv/bin/pip install -r requirements.txt

# Restart Gunicorn
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn

# Collect Static
echo "Collecting static files..."
./venv/bin/python manage.py collectstatic --noinput

echo "Deployment complete!"
