import os
import sys
import time
import numpy as np
import sounddevice as sd
import requests

import database
import speaker_biometrics
from wakeword_engine import WakeWordDetector
import command_recognizer

# Configuration
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.5   # 0.5s sliding window for Wake Word
RECORD_DURATION = 1.5  # 1.5s recording for the TFLite KWS Light Command
FLASK_API_BASE = "http://192.168.1.13:5000/channels"

# Map human-readable device names to the UUIDs from your existing Flask server
DEVICE_UUIDS = {
    "light_1": "b21642ae-34f1-485c-b459-351bafcdf920",
    # Add your Fan and Curtain UUIDs here when you train them!
    "fan_1": "YOUR-FAN-UUID-HERE",
    "curtain_1": "YOUR-CURTAIN-UUID-HERE"
}

def send_to_flask(device_id, action):
    """Sends the command to your existing UUID-based Flask Server."""
    uuid = DEVICE_UUIDS.get(device_id)
    if not uuid:
        print(f"❌ Unknown device_id: {device_id}")
        return

    url = f"{FLASK_API_BASE}/{uuid}/control"
    payload = {"value": action}
    
    try:
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            print(f"✅ Successfully sent {action} to {device_id} at {url}")
        else:
            print(f"⚠️ Flask rejected command: {response.text}")
    except Exception as e:
        print(f"❌ Failed to reach existing Flask server at {url}: {e}")

def main():
    print("\n" + "="*50)
    print("🚀 PROJECT FLOW AI ASSISTANT (TFLite CNN) 🚀")
    print("="*50)

    database.init_db()
    wakeword = WakeWordDetector()

    while True:
        try:
            print("\n💤 Sleeping... Listening for 'Hey Kasu'...")
            
            # --- STAGE 1: WAKE WORD ---
            audio_chunk = sd.rec(int(CHUNK_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            
            is_awake = wakeword.process_audio_stream(audio_chunk.flatten())
            
            # Remove this forced override once you train the Wake Word CNN
            is_awake = True if np.max(np.abs(audio_chunk)) > 0.05 else False 
            
            if not is_awake:
                continue

            print("🔔 WAKE WORD DETECTED! ('Hey Kasu')")
            
            # --- STAGE 2: BIOMETRICS ---
            users = database.get_all_users()
            is_authorized, user_name = speaker_biometrics.verify_speaker(incoming_audio_data=audio_chunk.flatten(), database_users=users)

            if not is_authorized:
                print("🚫 Intruder Alert: Unrecognized voice. Ignoring.")
                time.sleep(1) # Cooldown
                continue

            print(f"✅ Identity Verified: Welcome, {user_name}! Listening for light command...")

            # --- STAGE 3: TFLite COMMAND RECOGNITION ---
            print("⏳ You have 10 seconds to give a command...")
            
            command_detected = False
            start_time = time.time()
            
            # Listen in a loop for up to 10 seconds
            while time.time() - start_time < 10:
                # Record a 1.5s chunk
                command_audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
                sd.wait()
                
                command, confidence = command_recognizer.recognize_command(command_audio.flatten())
                
                if command == "LIGHT_ON":
                    print(f"🧠 Command Detected: {command} ({confidence:.1f}%)")
                    send_to_flask("light_1", "ON")
                    command_detected = True
                    time.sleep(2) # Cooldown after successful command
                    break
                elif command == "LIGHT_OFF":
                    print(f"🧠 Command Detected: {command} ({confidence:.1f}%)")
                    send_to_flask("light_1", "OFF")
                    command_detected = True
                    time.sleep(2)
                    break
                # If UNKNOWN, loop continues silently until 10 seconds is up
                
            if not command_detected:
                print("⏰ Timeout: No command heard within 10 seconds. Going back to sleep...")

        except KeyboardInterrupt:
            print("\nShutting down system...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
