import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables or .env file.")

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

if not CEREBRAS_API_KEY:
    print("Warning: CEREBRAS_API_KEY not found in environment variables or .env file.")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in environment variables or .env file.")
