import os
import io
import time
import numpy as np
import scipy.io.wavfile as wavfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator
import requests

# Local modules
import database
import speaker_biometrics
import nlp_classifier
from main_production import apply_advanced_noise_reduction, send_to_flask, SAMPLE_RATE

app = Flask(__name__)
CORS(app) # Allow React frontend to connect

# Initialize Database and Speech Recognizer
database.init_db()
recognizer = sr.Recognizer()

def read_audio_file(file_storage):
    """Helper to convert Flask FileStorage to flattened numpy array"""
    file_bytes = file_storage.read()
    sr_rate, audio_data = wavfile.read(io.BytesIO(file_bytes))
    
    # If stereo, convert to mono
    if len(audio_data.shape) > 1:
        audio_data = audio_data[:, 0]
        
    # Convert to float32 [-1.0, 1.0] if it's int16
    if audio_data.dtype == np.int16:
        audio_data = audio_data.astype(np.float32) / 32768.0
        
    return audio_data

@app.route('/api/enroll', methods=['POST'])
def enroll():
    if 'audio' not in request.files or 'name' not in request.form:
        return jsonify({"success": False, "message": "Missing audio or name"}), 400
        
    audio_file = request.files['audio']
    name = request.form['name']
    
    try:
        audio_data = read_audio_file(audio_file)
        
        # 1. Advanced Metrics: Calculate SNR
        noise_part = audio_data[:4000] # Assume first 250ms is background noise
        noise_power = np.mean(noise_part**2) + 1e-10
        signal_power = np.mean(audio_data**2)
        snr_db = 10 * np.log10(signal_power / noise_power)
        
        # Map to PhD Table 4.1 Results based on environment
        if snr_db > 5.0:
            env_name = "Clean / 10dB (Test Case 1)"
            accuracy_data = [
                {"name": "Spectral Sub", "acc": 93.0},
                {"name": "Wiener", "acc": 94.0},
                {"name": "Wavelet", "acc": 94.0},
                {"name": "Butterworth", "acc": 88.0},
                {"name": "VGDWF", "acc": 96.0}
            ]
        elif snr_db > -2.0:
            env_name = "Moderate Noise / 0dB (Test Case 2)"
            accuracy_data = [
                {"name": "Spectral Sub", "acc": 78.0},
                {"name": "Wiener", "acc": 80.0},
                {"name": "Wavelet", "acc": 82.0},
                {"name": "Butterworth", "acc": 68.0},
                {"name": "VGDWF", "acc": 90.0}
            ]
        else:
            env_name = "Heavy Noise / -5dB (Test Case 3)"
            accuracy_data = [
                {"name": "Spectral Sub", "acc": 65.0},
                {"name": "Wiener", "acc": 68.0},
                {"name": "Wavelet", "acc": 70.0},
                {"name": "Butterworth", "acc": 50.0},
                {"name": "VGDWF", "acc": 82.0}
            ]
            
        # 2. Voice Signature (Line Chart Data) - Mocked X-Vector traits
        signature_data = [{"band": f"{i}kHz", "amplitude": float(np.abs(np.sin(i * snr_db) * 100))} for i in range(1, 13)]
        
        # 3. Radar Chart Data (Identity Matrix)
        radar_data = [
            {"metric": "Pitch Match", "score": float(np.clip(80 + snr_db, 60, 99))},
            {"metric": "Clarity", "score": float(np.clip(95 + (snr_db * 2), 50, 99))},
            {"metric": "Stability", "score": float(np.clip(90 + snr_db, 70, 99))},
            {"metric": "Vocal Tract", "score": 92.5},
            {"metric": "Timbre", "score": 88.4}
        ]

        # Extract fingerprint
        fingerprint = speaker_biometrics.extract_voice_fingerprint(audio_data=audio_data)
        
        if fingerprint is not None:
            database.add_user(name, fingerprint)
            return jsonify({
                "success": True, 
                "message": f"Biometrics secured for {name}",
                "snr_detected": round(snr_db, 1),
                "env_name": env_name,
                "accuracy_data": accuracy_data,
                "signature_data": signature_data,
                "radar_data": radar_data
            })
        else:
            return jsonify({"success": False, "message": "Audio too silent or unclear"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize():
    if 'audio' not in request.files:
        return jsonify({"success": False, "message": "Missing audio"}), 400
        
    audio_file = request.files['audio']
    
    try:
        audio_data = read_audio_file(audio_file)
        
        # 1. Advanced Noise Reduction (VGDWF)
        print("🧹 Applying Advanced Spectral Noise Reduction...")
        clean_audio = apply_advanced_noise_reduction(audio_data)
        
        # 2. Biometric Verification
        users = database.get_all_users()
        is_authorized, user_name = speaker_biometrics.verify_speaker(incoming_audio_data=clean_audio, database_users=users)
        
        if not is_authorized:
            return jsonify({
                "success": True,
                "authorized": False,
                "user_name": None,
                "command": "UNKNOWN",
                "sinhala": "",
                "message": "You are not my assistant. Unauthorized access."
            })
            
        # 3. Speech-to-Text (Sinhala)
        # Convert to 16-bit PCM for SpeechRecognition
        audio_data_int16 = (clean_audio * 32767).astype(np.int16)
        audio_data_obj = sr.AudioData(audio_data_int16.tobytes(), SAMPLE_RATE, 2)
        
        try:
            transcription = recognizer.recognize_google(audio_data_obj, language="si-LK")
        except sr.UnknownValueError:
            return jsonify({
                "success": True,
                "authorized": True,
                "user_name": user_name,
                "command": "UNKNOWN",
                "sinhala": "Could not understand audio",
                "message": "Recognized user, but audio unclear."
            })
            
        # 4. NLP Classification
        device_id, action = nlp_classifier.classify_command(transcription)
        
        command_str = "UNKNOWN"
        if device_id and action:
            command_str = f"Turn {action} the {device_id}"
            # Trigger Hardware
            send_to_flask(device_id, action)
            
            # 🔥 Push real-time data to Firebase RTDB
            firebase_url = "https://kasundi-ai-home-default-rtdb.firebaseio.com/telemetry.json"
            try:
                requests.post(firebase_url, json={
                    "device": device_id,
                    "status": action,
                    "command_text": transcription,
                    "timestamp": {".sv": "timestamp"}
                }, timeout=2)
                print(f"🔥 Successfully synced {device_id} ({action}) to Firebase Realtime Database!")
            except Exception as fe:
                print(f"⚠️ Firebase Sync Warning: {fe}")
            
        # 5. Dynamic SNR Calculation for PhD Test Case Mapping
        # Calculate approximate SNR from the raw audio
        noise_part = audio_data[:4000] # Assume first 250ms is background noise
        noise_power = np.mean(noise_part**2) + 1e-10
        signal_power = np.mean(audio_data**2)
        snr_db = 10 * np.log10(signal_power / noise_power)
        
        # Map to PhD Table 4.1 Results based on environment
        if snr_db > 5.0:
            env_name = "Clean / 10dB (Test Case 1)"
            accuracy_data = [
                {"name": "Spectral Sub", "acc": 93.0},
                {"name": "Wiener", "acc": 94.0},
                {"name": "Wavelet", "acc": 94.0},
                {"name": "Butterworth", "acc": 88.0},
                {"name": "VGDWF (Yours)", "acc": 96.0}
            ]
        elif snr_db > -2.0:
            env_name = "Moderate Noise / 0dB (Test Case 2)"
            accuracy_data = [
                {"name": "Spectral Sub", "acc": 78.0},
                {"name": "Wiener", "acc": 80.0},
                {"name": "Wavelet", "acc": 82.0},
                {"name": "Butterworth", "acc": 68.0},
                {"name": "VGDWF (Yours)", "acc": 90.0}
            ]
        else:
            env_name = "Heavy Noise / -5dB (Test Case 3)"
            accuracy_data = [
                {"name": "Spectral Sub", "acc": 65.0},
                {"name": "Wiener", "acc": 68.0},
                {"name": "Wavelet", "acc": 70.0},
                {"name": "Butterworth", "acc": 50.0},
                {"name": "VGDWF (Yours)", "acc": 82.0}
            ]
            
        return jsonify({
            "success": True,
            "authorized": True,
            "user_name": user_name,
            "command": command_str,
            "device_id": device_id,
            "action": action,
            "sinhala": transcription,
            "snr_detected": round(snr_db, 1),
            "env_name": env_name,
            "accuracy_data": accuracy_data,
            "message": "Command Executed Successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Web API Server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
