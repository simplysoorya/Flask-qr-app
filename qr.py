from flask import Flask, render_template, request, send_from_directory
import pyqrcode
import os
from datetime import datetime
from cryptography.fernet import Fernet
from config import load_key, get_db_connection
from werkzeug.utils import secure_filename
from user_agents import parse

app = Flask(__name__)
app.secret_key = "1c48b9bd05a8f25e7780f3ccaa61171e"

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi','mp3'}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load encryption key
cipher = Fernet(load_key())

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    else:
        filepath = None

    encrypted_message = cipher.encrypt(message.encode()).decode()
    encrypted_password = cipher.encrypt(password.encode()).decode()
    encrypted_decoy_message = cipher.encrypt(decoy_message.encode()).decode()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (encrypted_message, password, decoy_message, filename) VALUES (%s, %s, %s, %s)",
        (encrypted_message, encrypted_password, encrypted_decoy_message, filename)
    )
    message_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    local_ip = "192.168.1.4"  # Replace with your local IP

    qr_data = f"{decoy_message}\nCrypto World: http://{local_ip}:5000/decrypt/{message_id}"
    qr = pyqrcode.create(qr_data)

    qr_folder = "static"
    os.makedirs(qr_folder, exist_ok=True)
    qr_path = os.path.join(qr_folder, f"qr_{message_id}.png")
    qr.png(qr_path, scale=8)

    return render_template("qr_display.html", qr_code=qr_path, filename=filename)

@app.route("/decrypt/<int:message_id>", methods=["GET", "POST"])
def decrypt_message(message_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "GET":
        visitor_ip = request.remote_addr
        access_time = datetime.now()
        user_agent_str = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_str)

        device_type = user_agent.device.family
        os_info = f"{user_agent.os.family} {user_agent.os.version_string}"
        browser_info = f"{user_agent.browser.family} {user_agent.browser.version_string}"
        architecture = user_agent.device.brand or "Unknown"

        print(f"[ACCESS LOG] ID: {message_id} | IP: {visitor_ip} | Time: {access_time}")
        print(f"Device: {device_type} | OS: {os_info} | Browser: {browser_info} | Architecture: {architecture}")

        cursor.execute(
            """
            UPDATE messages
            SET ip_address=%s, access_time=%s, device_type=%s, os_info=%s, browser_info=%s, architecture=%s
            WHERE id=%s AND ip_address IS NULL
            """,
            (visitor_ip, access_time, device_type, os_info, browser_info, architecture, message_id)
        )
        conn.commit()

    if request.method == "POST":
        entered_password = request.form["password"]

        # PARAMETERIZED SELECT query
        cursor.execute(
            "SELECT encrypted_message, password, decoy_message, viewed, ip_address, access_time, filename FROM messages WHERE id=%s",
            (message_id,)
        )
        data = cursor.fetchone()

        if not data:
            cursor.close()
            conn.close()
            return "Invalid QR Code or message does not exist."

        encrypted_message, stored_password, encrypted_decoy_message, viewed, ip_address, access_time, filename = data
        stored_password = cipher.decrypt(stored_password.encode()).decode()
        decoy_message = cipher.decrypt(encrypted_decoy_message.encode()).decode()

        if viewed:
            cursor.close()
            conn.close()
            return "This message has already been viewed and self-destructed."

        if entered_password == stored_password:
            decrypted_message = cipher.decrypt(encrypted_message.encode()).decode()
            cursor.execute("UPDATE messages SET viewed=1 WHERE id=%s", (message_id,))
            conn.commit()
            cursor.close()
            conn.close()

            return render_template(
                "message.html",
                message=decrypted_message,
                self_destruct=True,
                filename=filename
            )
        else:
            cursor.close()
            conn.close()
            return render_template("message.html", message=decoy_message, self_destruct=False)

    cursor.close()
    conn.close()
    return render_template("auth.html", message_id=message_id)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
