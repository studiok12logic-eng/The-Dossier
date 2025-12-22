#!/bin/bash

echo "Starting deployment..."

# Pull latest changes
echo "Pulling latest from git..."
git pull origin main

# Install dependencies
echo "Installing dependencies..."
./venv/bin/pip install -r requirements.txt

# Run Migrations
echo "Running migrations..."
./venv/bin/python manage.py migrate

# Restart Gunicorn
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn

# Collect Static
echo "Collecting static files..."
./venv/bin/python manage.py collectstatic --noinput

echo "Deployment complete!"
