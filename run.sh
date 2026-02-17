#!/bin/bash

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    read -p "Enter your Gemini API Key: " api_key
    echo "GEMINI_API_KEY=$api_key" > .env
fi

# Run the application
# Using python3 directly as we installed dependencies with --user or system 
# (depending on previous steps, but assuming 'python3' has access to them)
python3 main.py
