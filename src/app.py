import os
import json
import sqlite3
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt

from flask_cors import CORS
import librosa
import numpy as np
import speaker_biometrics
import database
import nlp_classifier
import speech_recognition as sr
import numpy as np

app = Flask(__name__)
CORS(app) # Allow web dashboard to communicate with local API

# =========================
# CONFIGURATION
# =========================
MQTT_BROKER = "127.0.0.1"  # Assuming Mosquitto runs on the RPi
MQTT_PORT = 1883
MQTT_TOPIC_SET = "home/devices/{device_id}/ch1/set"
MQTT_TOPIC_STATUS = "home/devices/+/ch1/status"

DB_PATH = "home_state.db"

# ... (Database and MQTT setup remains unchanged) ...
# To save space and ensure clean diffs, I will inject the endpoints directly below.

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_state (
            device_id TEXT PRIMARY KEY,
            state TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def update_device_state(device_id, state):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO device_state (device_id, state) VALUES (?, ?)', (device_id, state))
    conn.commit()
    conn.close()

def get_all_device_states():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT device_id, state FROM device_state')
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

init_db()
database.init_db() # Also init the biometrics database

# =========================
# MQTT SETUP
# =========================
mqtt_client = mqtt.Client(client_id="rpi_flask_server")

def on_connect(client, userdata, flags, rc):
    print(f"📡 Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_STATUS)

def on_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split("/")
        device_id = topic_parts[2]
        payload = msg.payload.decode()
        update_device_state(device_id, payload)
    except Exception as e:
        print(f"❌ Error processing MQTT message: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start() 
except Exception as e:
    print(f"WARNING: Could not connect to MQTT Broker at {MQTT_BROKER}: {e}")

# =========================
# FLASK REST API
# =========================

@app.route('/api/users/enroll', methods=['POST'])
def enroll_user():
    """Web Dashboard: Registers a new user's voice biometric"""
    if 'audio' not in request.files or 'name' not in request.form:
        return jsonify({"error": "Missing audio file or name"}), 400
        
    name = request.form['name']
    audio_file = request.files['audio']
    
    # Save temporarily to process
    temp_path = "temp_enroll.wav"
    audio_file.save(temp_path)
    
    embedding = speaker_biometrics.extract_voice_fingerprint(audio_path=temp_path)
    
    if embedding is None:
        return jsonify({"error": "Could not extract voice features. Try speaking louder."}), 400
        
    database.add_user(name, embedding)
    os.remove(temp_path)
    
    return jsonify({"success": True, "message": f"User {name} enrolled successfully!"}), 200

@app.route('/api/voice/test', methods=['POST'])
def test_voice():
    """Web Dashboard: Tests the full AI pipeline via web recording"""
    if 'audio' not in request.files:
        return jsonify({"error": "Missing audio file"}), 400
        
    audio_file = request.files['audio']
    temp_path = "temp_test.wav"
    audio_file.save(temp_path)
    
    # Load audio
    audio_data, _ = librosa.load(temp_path, sr=16000, mono=True)
    
    # 1. Check Biometrics
    users = database.get_all_users()
    is_authorized, user_name = speaker_biometrics.verify_speaker(incoming_audio_data=audio_data, database_users=users)
    
    # 2. Extract Command
    recognizer = sr.Recognizer()
    # Convert float32 numpy array to 16-bit PCM bytes for SpeechRecognition
    audio_data_int16 = (audio_data * 32767).astype(np.int16)
    audio_data_obj = sr.AudioData(audio_data_int16.tobytes(), 16000, 2)
    
    command_str = "UNKNOWN"
    sinhala_text = ""
    confidence = 0.0
    device_id, action = None, None
    
    try:
        sinhala_text = recognizer.recognize_google(audio_data_obj, language="si-LK")
        device_id, action = nlp_classifier.classify_command(sinhala_text)
        if device_id and action:
            command_str = f"Turn {action} the {device_id.replace('_1', '')}"
            confidence = 100.0
    except sr.UnknownValueError:
        command_str = "UNKNOWN_AUDIO"
    except sr.RequestError:
        command_str = "API_ERROR"
    
    os.remove(temp_path)
    
    return jsonify({
        "authorized": is_authorized,
        "user_name": user_name,
        "command": command_str,
        "sinhala": sinhala_text,
        "device_id": device_id,
        "action": action,
        "confidence": confidence
    }), 200

@app.route('/api/devices/control', methods=['POST'])
def control_device():
    data = request.json
    if not data or 'device_id' not in data or 'action' not in data:
        return jsonify({"error": "Missing device_id or action"}), 400

    device_id = data['device_id']
    action = data['action']
    
    topic = MQTT_TOPIC_SET.format(device_id=device_id)
    mqtt_client.publish(topic, action)
    
    return jsonify({"success": True, "message": f"Command {action} sent to {device_id} via MQTT"}), 200

@app.route('/api/devices/state', methods=['GET'])
def dashboard_state():
    states = get_all_device_states()
    return jsonify({"devices": states}), 200

if __name__ == '__main__':
    print("[START] Starting Flask Server (MQTT Hub) on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
