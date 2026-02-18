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


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in environment variables or .env file.")


NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not NEWS_API_KEY:
    print("Warning: NEWS_API_KEY not found in environment variables or .env file.")

OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

if not OANDA_API_KEY:
    print("Warning: OANDA_API_KEY not found in environment variables or .env file.")
if not OANDA_ACCOUNT_ID:
    print("Warning: OANDA_ACCOUNT_ID not found in environment variables or .env file.")

# AI Model Definitions
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-3-preview")
CEREBRAS_MODEL_ID = os.getenv("CEREBRAS_MODEL_ID", "gpt-oss-120b")
GROQ_MODEL_ID = os.getenv("GROQ_MODEL_ID", "moonshotai/kimi-k2-instruct-0905")
OPENROUTER_MODEL_ID = os.getenv("OPENROUTER_MODEL_ID", "stepfun/step-3.5-flash:free")
