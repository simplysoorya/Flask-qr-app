from cryptography.fernet import Fernet
import mysql.connector
import os

# MySQL Database Configuration
MYSQL_HOST = "localhost"      # Change this if your MySQL server is on a different host
MYSQL_USER = "root"           # Your MySQL username
MYSQL_PASSWORD = "root"  # Your MySQL password
MYSQL_DATABASE = "secure_qr"  # Database name

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
    """Establishes a connection to the MySQL database."""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

# Initialize Database (Run this once)
def init_db():
    """Creates the database and table if they do not exist."""
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
