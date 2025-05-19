import os
import psycopg2
from cryptography.fernet import Fernet

# Load DB config from environment
PG_HOST = os.environ.get("PG_HOST")
PG_USER = os.environ.get("PG_USER")
PG_PASSWORD = os.environ.get("PG_PASSWORD")
PG_DATABASE = os.environ.get("PG_DATABASE")

# Secret key string from environment (used for Fernet)
secret_key_str = os.environ.get("SECRET_KEY")
cipher = Fernet(secret_key_str.encode())

def load_key():
    """Load encryption key from env variable instead of file."""
    return secret_key_str.encode()

def get_db_connection():
    """Establish connection to Neon PostgreSQL DB."""
    return psycopg2.connect(
        host=PG_HOST,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DATABASE,
        sslmode='require'
    )
