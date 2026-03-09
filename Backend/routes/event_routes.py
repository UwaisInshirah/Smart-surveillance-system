import jwt
from flask import Blueprint, jsonify, request, current_app
from functools import wraps
from database import get_db_connection
import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

event_bp = Blueprint("events", __name__)

# ---------------------------------------
# 6️⃣ Upload Image From Raspberry Pi
# ---------------------------------------
@event_bp.route("/upload-image", methods=["POST"])
def upload_image():

    image = request.files.get("image")

    if not image:
        return jsonify({"message": "No image provided"}), 400

    try:
        upload_result = cloudinary.uploader.upload(image)

        image_url = upload_result["secure_url"]

        return jsonify({
            "message": "Image uploaded successfully",
            "image_url": image_url
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------
# TOKEN REQUIRED DECORATOR
# ---------------------------------------
def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        try:
            token = token.split(" ")[1]
            jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({"message": "Token is invalid or expired"}), 401

        return func(*args, **kwargs)

    return wrapper


# ---------------------------------------
# 1️⃣ Load Dummy Data Into Database
# ---------------------------------------
@event_bp.route("/load-dummy-events", methods=["GET"])
def load_dummy_events():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM DetectionEvent")
        result = cur.fetchone()
        count = result["total"]

        if count > 0:
            cur.close()
            conn.close()
            return jsonify({"message": "Dummy data already exists"}), 200

        dummy_events = [
            (
                "2025-02-07 10:30:00", "Cow", "15m", "Near",
                "Likely to cross", "Zone A",
                "/static/cow.jpeg"
            ),
            (
                "2025-02-08 11:15:00", "Dog", "Out of range", "Far",
                "Moving away", "Zone B",
                "/static/dog.jpeg"
            ),
            (
                "2025-02-10 12:05:00", "Elephant", "8m", "Very Near",
                "High risk crossing", "Zone C",
                "/static/elephant.jpeg"
            )
        ]

        for event in dummy_events:
            cur.execute("""
                INSERT INTO DetectionEvent
                (Timestamp, AnimalType, Distance, ProximityLevel,
                 PredictedBehaviour, Location, Snapshot)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, event)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "All dummy events inserted successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------
# 2️⃣ Fetch Events
# ---------------------------------------
@event_bp.route("/events", methods=["GET"])
@token_required
def get_events():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                EventID,
                Timestamp,
                AnimalType,
                Location,
                ProximityLevel,
                PredictedBehaviour
            FROM DetectionEvent
            ORDER BY Timestamp DESC
        """)

        events = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(events), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------
# 3️⃣ Sync Events From Raspberry Pi
# ---------------------------------------
@event_bp.route("/sync-events", methods=["POST"])
def sync_events():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data received"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        for event in data:
            cur.execute("""
                INSERT INTO DetectionEvent
                (Timestamp, AnimalType, Distance, ProximityLevel,
                 PredictedBehaviour, Location, Snapshot)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event.get("timestamp"),
                event.get("animal"),
                event.get("distance"),
                event.get("proximity"),
                event.get("behavior"),
                event.get("location"),
                event.get("snapshot")
            ))
            # 2️⃣ Get generated EventID (VERY IMPORTANT)
            event_id = cur.lastrowid

    # 3️⃣ Insert into Alert table (if alert message exists)
            if event.get("alert_message"):
                cur.execute("""
                    INSERT INTO Alert (Message, EventID)
                    VALUES (%s, %s)
                """, (
                    event.get("alert_message"),
                    event_id
        ))

        

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Events synced successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------
# 4️⃣ Dashboard Route
# ---------------------------------------
@event_bp.route("/dashboard", methods=["GET"])
@token_required
def dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Today detection count
        cur.execute("""
            SELECT COUNT(*) AS todayCount
            FROM DetectionEvent
            WHERE DATE(Timestamp) = CURDATE()
        """)
        result = cur.fetchone()

        # High risk area (most frequent location)
        cur.execute("""
            SELECT Location, COUNT(*) AS cnt
            FROM DetectionEvent
            GROUP BY Location
            ORDER BY cnt DESC
            LIMIT 1
        """)
        top = cur.fetchone()

        cur.close()
        conn.close()

        high_risk_area = "N/A"
        if top:
            high_risk_area = top["Location"]

        return jsonify({
            "success": True,
            "todayEvents": result["todayCount"],
            "highRiskArea": high_risk_area
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------
# 5️⃣ Get Single Event By ID
# ---------------------------------------
@event_bp.route("/events/<int:event_id>", methods=["GET"])
@token_required
def get_event_by_id(event_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM DetectionEvent WHERE EventID = %s", (event_id,))
        event = cur.fetchone()

        cur.close()
        conn.close()

        if not event:
            return jsonify({"success": False, "message": "Event not found"}), 404

        return jsonify({
            "success": True,
            "event": event
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500