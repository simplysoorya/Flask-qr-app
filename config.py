import os
from cryptography.fernet import Fernet
import mysql.connector

# Load MySQL credentials from environment variables
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "secure_qr")

# Load secret key from environment variable
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set in environment variables.")

cipher = Fernet(SECRET_KEY.encode())

def get_db_connection():
    """Connect to the MySQL database using environment credentials."""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

def init_db():
    """Initialize the database by creating the required table if not present."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            encrypted_message TEXT NOT NULL,
            password TEXT NOT NULL,
            decoy_message TEXT NOT NULL,
            viewed BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Run database initialization
init_db()
