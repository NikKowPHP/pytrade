FROM python:3.12-slim

# Install system dependencies
# python3-tk is required for CustomTkinter/Tkinter
# x11-apps is good for debugging X11 connections
RUN apt-get update && apt-get install -y \
    python3-tk \
    tk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variable for display (can be overridden in compose)
ENV DISPLAY=:0

# Command to run the app
CMD ["python", "main.py"]
