# Entire qr.py with security improvements
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for, abort, make_response
import pyqrcode
import os
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename
from user_agents import parse
from dotenv import load_dotenv
import psycopg2

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_key_for_dev_only")

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mp3'}
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "your_email@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
DATABASE_URL = os.environ.get("DATABASE_URL")

def load_key():
    key_path = "secret.key"
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
    else:
        with open(key_path, "rb") as key_file:
            key = key_file.read()
    return key

cipher = Fernet(load_key())

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def add_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self';"
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_qr():
    message = request.form["message"]
    password = request.form["password"]
    decoy_message = request.form["decoy_message"]

    uploaded_file = request.files.get("file")
    filename = None
    if uploaded_file and allowed_file(uploaded_file.filename):
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded_file.save(filepath)

    encrypted_message = cipher.encrypt(message.encode()).decode()
    encrypted_password = cipher.encrypt(password.encode()).decode()
    encrypted_decoy_message = cipher.encrypt(decoy_message.encode()).decode()
    expiry_time = datetime.utcnow() + timedelta(hours=24)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages (encrypted_message, password, decoy_message, filename, expiry_time)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (encrypted_message, encrypted_password, encrypted_decoy_message, filename, expiry_time)
    )
    message_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    qr_url = url_for("decrypt_message", message_id=message_id, _external=True)
    qr_data = f"{decoy_message}\nCrypto World: {qr_url}"
    qr = pyqrcode.create(qr_data)

    qr_folder = "static"
    os.makedirs(qr_folder, exist_ok=True)
    qr_path = os.path.join(qr_folder, f"qr_{message_id}.png")
    qr.png(qr_path, scale=8)

    return render_template("qr_display.html", qr_code=qr_path, filename=filename, qr_url=qr_url)

@app.route("/send_email", methods=["POST"])
def send_email():
    to_email = request.form["email"]
    qr_path = request.form["qr_path"]
    qr_url = request.form["qr_url"]
    send_qr_email(to_email, qr_path, qr_url)
    return "✅ Email sent successfully!"

def send_qr_email(to_email, qr_path, qr_url):
    msg = EmailMessage()
    msg['Subject'] = "Encrypted QR Message from Crypto World"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content(f"Scan the attached QR or visit the URL to view your secure message:\n\n{qr_url}")
    with open(qr_path, 'rb') as img:
        msg.add_attachment(img.read(), maintype='image', subtype='png', filename=os.path.basename(qr_path))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

@app.route("/decrypt/<int:message_id>", methods=["GET", "POST"])
def decrypt_message(message_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT encrypted_message, password, decoy_message, viewed, filename, expiry_time FROM messages WHERE id=%s", (message_id,))
    data = cursor.fetchone()

    if not data:
        cursor.close()
        conn.close()
        return "Invalid QR Code."

    encrypted_message, stored_password, encrypted_decoy_message, viewed, filename, expiry_time = data

    # Expiry check
    if datetime.utcnow() > expiry_time:
        cursor.execute("DELETE FROM messages WHERE id=%s", (message_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return "⚠️ This link has expired."

    if request.method == "GET":
        visitor_ip = request.remote_addr
        access_time = datetime.now()
        user_agent_str = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_str)
        device_type = user_agent.device.family
        os_info = f"{user_agent.os.family} {user_agent.os.version_string}"
        browser_info = f"{user_agent.browser.family} {user_agent.browser.version_string}"
        architecture = user_agent.device.brand or "Unknown"

        cursor.execute("""
            UPDATE messages
            SET ip_address=%s, access_time=%s, device_type=%s, os_info=%s, browser_info=%s, architecture=%s
            WHERE id=%s AND ip_address IS NULL
        """, (visitor_ip, access_time, device_type, os_info, browser_info, architecture, message_id))
        conn.commit()

    attempts_key = f"attempts_{message_id}"
    block_time_key = f"block_time_{message_id}"

    if attempts_key not in session:
        session[attempts_key] = 0

    if request.method == "POST":
        entered_password = request.form["password"]

        if block_time_key in session and time.time() < session[block_time_key]:
            return f"Temporarily blocked. Try again in {int(session[block_time_key] - time.time())} seconds."

        stored_password = cipher.decrypt(stored_password.encode()).decode()
        decoy_message = cipher.decrypt(encrypted_decoy_message.encode()).decode()

        if viewed:
            return "This message has already been viewed and self-destructed."

        if entered_password == stored_password:
            decrypted_message = cipher.decrypt(encrypted_message.encode()).decode()
            cursor.execute("UPDATE messages SET viewed=TRUE WHERE id=%s", (message_id,))
            conn.commit()
            return render_template("message.html", message=decrypted_message, self_destruct=True, filename=filename)
        else:
            session[attempts_key] += 1
            if session[attempts_key] == 3:
                session[block_time_key] = time.time() + 180
                return "⚠️ Wrong password 3 times. Wait 3 minutes."

            if session[attempts_key] >= 6:
                cursor.execute("DELETE FROM messages WHERE id=%s", (message_id,))
                conn.commit()
                return "Too many failed attempts. Message deleted."

            return render_template("message.html", message=decoy_message, self_destruct=False)

    return render_template("auth.html", message_id=message_id)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT viewed, expiry_time FROM messages WHERE filename=%s", (filename,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not data:
        abort(404)

    viewed, expiry_time = data
    if viewed or datetime.utcnow() > expiry_time:
        return "⛔ File is no longer available."

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
