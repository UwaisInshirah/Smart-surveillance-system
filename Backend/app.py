from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp
from routes.event_routes import event_bp
import os

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

# ---------------------------
# Register Blueprints
# ---------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(event_bp)

@app.route("/")
def home():
    return {"message": "Flask backend running successfully"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)