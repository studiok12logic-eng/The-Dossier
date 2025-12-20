#!/bin/bash

echo "Starting deployment..."

# Pull latest changes
echo "Pulling latest from git..."
git pull origin main

# Restart Gunicorn
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn

# Collect Static (Optional but good practice)
# echo "Collecting static files..."
# python3 manage.py collectstatic --noinput

echo "Deployment complete!"
