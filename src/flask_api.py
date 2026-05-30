import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import database
import speaker_biometrics

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# =========================
# FLUTTER APP API ROUTES
# =========================

@app.route('/api/users/enroll', methods=['POST'])
def enroll_user():
    """
    Called by the Flutter app to register a new family member.
    Requires 'name' and 'audio_file' (wav).
    """
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    if 'name' not in request.form:
        return jsonify({"error": "No user name provided"}), 400

    file = request.files['audio_file']
    name = request.form['name']

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    print(f"🎙️ Enrolling new user: {name}")
    
    # Extract biometric fingerprint
    fingerprint = speaker_biometrics.extract_voice_fingerprint(audio_path=filepath)
    
    # Delete temporary upload file
    if os.path.exists(filepath):
        os.remove(filepath)

    if fingerprint is None:
        return jsonify({"error": "Failed to extract biometrics. Audio might be too short or silent."}), 400

    # Save to database
    database.add_user(name, fingerprint)
    
    return jsonify({"success": True, "message": f"Successfully registered {name}"}), 201

@app.route('/api/users', methods=['GET'])
def list_users():
    """Returns a list of all registered family members."""
    users = database.get_all_users()
    # Strip out the massive embedding arrays to keep JSON clean
    clean_users = [{"id": u["id"], "name": u["name"]} for u in users]
    return jsonify({"users": clean_users}), 200

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Deletes a family member's access."""
    database.delete_user(user_id)
    return jsonify({"success": True, "message": f"User {user_id} deleted."}), 200

@app.route('/api/devices/control', methods=['POST'])
def manual_override():
    """
    Manual device control from the app (fallback if voice fails).
    Expects JSON: {"device": "light", "action": "on"}
    """
    data = request.json
    device = data.get("device")
    action = data.get("action")
    
    # Here you would trigger your ESP32 MQTT logic
    print(f"📱 App Override: Turning {device} {action.upper()}")
    
    return jsonify({"success": True, "message": f"{device} turned {action}"}), 200

if __name__ == '__main__':
    print("🚀 Starting Smart Home AI Server for Flutter App...")
    # Run on 0.0.0.0 so the mobile app on the same WiFi can reach it
    app.run(host='0.0.0.0', port=5000, debug=True)
