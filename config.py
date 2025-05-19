from cryptography.fernet import Fernet
import psycopg2
import os

# PostgreSQL Database Configuration
PG_HOST = "ep-floral-bar-a4jjzpk0-pooler.us-east-1.aws.neon.tech"
PG_USER = "neondb_owner"
PG_PASSWORD = "npg_McXUZL08JDOH"
PG_DATABASE = "neondb"

# Path to the secret key file
KEY_FILE = r"E:\Python\secret.key"

def load_key():
    """Load the encryption key from secret.key or raise an error if not found."""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(f"Secret key file not found at {KEY_FILE}. Make sure it exists.")

    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

# Load the encryption key
key = load_key()
cipher = Fernet(key)

# Database Connection Function
def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=PG_HOST,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DATABASE,
        sslmode='require'
    )
