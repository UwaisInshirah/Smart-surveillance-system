import jwt
import datetime
import bcrypt
import re

from flask import Blueprint, request, jsonify, current_app
from database import get_db_connection

auth_bp = Blueprint("auth", __name__)

# ---------------------------------------
# 1️⃣ Register Route
# ---------------------------------------
@auth_bp.route('/register', methods=['POST'])
def register():

    data = request.get_json() or {}

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    # Validation
    if name == "":
        return jsonify({"message": "Full Name is required."}), 400

    if email == "":
        return jsonify({"message": "Email is required."}), 400

    if "@" not in email:
        return jsonify({"message": "Email must contain '@'."}), 400

    if password == "":
        return jsonify({"message": "Password is required."}), 400

    password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
    if not re.match(password_pattern, password):
        return jsonify({
            "message": "Password must be 8+ characters with uppercase, lowercase, number & special character."
        }), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if email exists
    cur.execute("SELECT * FROM User WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"message": "Email already registered."}), 400

    # Hash password
    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Insert user
    cur.execute(
        "INSERT INTO User (Name, Email, Password) VALUES (%s, %s, %s)",
        (name, email, hashed_password)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Registration successful."}), 201


# ---------------------------------------
# 2️⃣ Login Route
# ---------------------------------------
@auth_bp.route('/login', methods=['POST'])
def login():

    data = request.get_json() or {}

    email = data.get('email', '').strip()
    password = data.get('password', '')

    if email == "" or password == "":
        return jsonify({"message": "Email and Password are required."}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT Password FROM User WHERE email = %s", (email,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if not result:
        return jsonify({"message": "Invalid email or password."}), 401

    stored_password = result['Password']

    if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):

        token = jwt.encode({
            'email': email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({
            "message": "Login successful.",
            "token": token
        }), 200

    else:
        return jsonify({"message": "Invalid email or password."}), 401