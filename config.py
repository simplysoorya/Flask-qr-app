import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import psycopg2  # For Neon/PostgreSQL

# Load environment variables from .env file
load_dotenv()

# Retrieve values from .env
secret_key_str = os.getenv("SECRET_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
DB_URL = os.getenv("DATABASE_URL")  # for Neon DB

# Debug info
print(f"Loaded SECRET_KEY: {secret_key_str}")
print(f"Loaded EMAIL_ADDRESS: {EMAIL_ADDRESS}")
print(f"Loaded DB_URL: {DB_URL}")

# Validate secret key
if secret_key_str is None:
    raise ValueError("SECRET_KEY is missing from .env file.")

cipher = Fernet(secret_key_str.encode())

# Access the Fernet cipher from other files
def load_key():
    return cipher

# PostgreSQL connection (Neon)
def get_db_connection():
    if DB_URL is None:
        raise ValueError("DATABASE_URL is missing in .env file.")
    return psycopg2.connect(DB_URL)

# Expose email credentials
# You can hardcode the email if you prefer (since you said it should not be in HTML)
EMAIL_ADDRESS = "sooryanarayana2004@gmail.com"
