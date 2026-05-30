import os
import sys
import time
import numpy as np
import requests
import librosa

import database
import speaker_biometrics
from wakeword_engine import WakeWordDetector
import command_recognizer

# Configuration
SAMPLE_RATE = 16000
FLASK_API_URL = "http://127.0.0.1:5000/api/devices/control"

def send_to_flask(device_id, action):
    payload = {"device_id": device_id, "action": action}
    try:
        response = requests.post(FLASK_API_URL, json=payload, timeout=2)
        if response.status_code == 200:
            print(f"[SUCCESS] Successfully passed to Flask: {payload}")
        else:
            print(f"[WARNING] Flask rejected command: {response.text}")
    except Exception as e:
        print(f"[ERROR] Failed to reach Flask server: {e}")

def main():
    print("\n" + "="*50)
    print("[START] AUTOMATED SIMULATION: AI ASSISTANT PIPELINE")
    print("="*50)

    database.init_db()
    wakeword = WakeWordDetector()

    print("\n[SIMULATION] Loading test.wav instead of using microphone...")
    audio, _ = librosa.load("test.wav", sr=SAMPLE_RATE, mono=True)
    
    # Simulate a loud noise for the wake word
    dummy_wake_audio = np.ones(8000) * 0.5 

    print("\n[SLEEP] Sleeping... Listening for 'Hey Kasu'...")
    time.sleep(1)
    
    # --- STAGE 1: WAKE WORD ---
    is_awake = True if np.max(np.abs(dummy_wake_audio)) > 0.05 else False 
    if is_awake:
        print("[WAKE] WAKE WORD DETECTED! ('Hey Kasu')")
        
        # --- STAGE 2: BIOMETRICS ---
        time.sleep(1)
        users = database.get_all_users()
        is_authorized, user_name = speaker_biometrics.verify_speaker(incoming_audio_data=audio, database_users=users)

        if is_authorized:
            print(f"[VERIFY] Identity Verified: Welcome, {user_name}! Listening for light command...")

            # --- STAGE 3: TFLite COMMAND RECOGNITION ---
            time.sleep(1)
            print("[INFO] Running MFCC feature extraction and TFLite Inference on test.wav...")
            command, confidence = command_recognizer.recognize_command(audio)
            
            if command == "LIGHT_ON":
                print(f"[ACTION] Command Detected: {command} ({confidence:.1f}%)")
                send_to_flask("light_1", "ON")
            elif command == "LIGHT_OFF":
                print(f"[ACTION] Command Detected: {command} ({confidence:.1f}%)")
                send_to_flask("light_1", "OFF")
            else:
                print(f"[UNKNOWN] UNKNOWN or Ignored Command (Confidence: {confidence:.1f}%)")

if __name__ == "__main__":
    main()
