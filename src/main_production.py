import os
import sys
import time
import numpy as np
import sounddevice as sd
import requests

import database
import speaker_biometrics
from wakeword_engine import WakeWordDetector
import speech_recognition as sr
import nlp_classifier
import pyttsx3

def speak(text):
    try:
        engine = pyttsx3.init() 
        voices = engine.getProperty('voices')
        for voice in voices:
            if "Zira" in voice.name or "female" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {e}")

# Configuration
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.5   # 0.5s sliding window for Wake Word
RECORD_DURATION = 4.0  # 4.0s recording for full sentence commands
FLASK_API_BASE = "http://192.168.8.199:5000/channels"

# Map human-readable device names to the UUIDs from your existing Flask server
DEVICE_UUIDS = {
    "light_1": "89093657-17c4-4b1c-9cfe-16037a5b21d0",
    # Add your Fan and Curtain UUIDs here when you train them!
    "fan_1": "01d574ae-f9e4-42de-b238-0c9e220ef0f4",
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
    print("🚀 PROJECT FLOW AI ASSISTANT (Google STT + Biometrics) 🚀")
    print("="*50)

    database.init_db()
    wakeword = WakeWordDetector()
    
    # Initialize the Google Speech Recognizer
    recognizer = sr.Recognizer()

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
            
            # --- STAGE 2 & 3: RECORD COMMAND ---
            print("🎤 Listening for a command (speak now)...")
            # Record a 4.0s chunk for BOTH Biometrics and Command
            command_audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            
            # --- STAGE 2: BIOMETRICS ---
            users = database.get_all_users()
            is_authorized, user_name = speaker_biometrics.verify_speaker(incoming_audio_data=command_audio.flatten(), database_users=users)

            if not is_authorized:
                print("🚫 Intruder Alert: Unrecognized voice. Ignoring.")
                speak("I don't know you.")
                time.sleep(1) # Cooldown
                continue

            print(f"✅ Identity Verified: Welcome, {user_name}!")
            speak(f"Hello {user_name}.")
            
            # --- STAGE 3: SPEECH-TO-TEXT & CLASSIFICATION ---
            
            print("🧠 Transcribing with Google Speech Recognition (Sinhala)...")
            # Convert float32 numpy array to 16-bit PCM bytes for SpeechRecognition
            audio_data_int16 = (command_audio.flatten() * 32767).astype(np.int16)
            audio_data_obj = sr.AudioData(audio_data_int16.tobytes(), SAMPLE_RATE, 2)
            
            try:
                # Using the free Google Web Speech API, set natively to Sinhala
                transcription = recognizer.recognize_google(audio_data_obj, language="si-LK")
                
                # Translate to English for debugging
                from deep_translator import GoogleTranslator
                english_translation = GoogleTranslator(source='si', target='en').translate(transcription)
                
                print(f"🗣️ You said (Sinhala): '{transcription}'")
                print(f"🌍 English Meaning: '{english_translation}'")
                
                device_id, action = nlp_classifier.classify_command(transcription)
                
                if device_id and action:
                    print(f"🎯 Action Resolved: Turn {action} the {device_id}")
                    speak(f"Turning {action} the {device_id.replace('_1', '')}")
                    send_to_flask(device_id, action)
                    time.sleep(2) # Cooldown after successful command
                else:
                    print("❓ Unknown voice command or no device recognized.")
                    time.sleep(1)
            except sr.UnknownValueError:
                print("❓ Could not understand audio.")
                time.sleep(1)
            except sr.RequestError as e:
                print(f"❌ Could not request results from Google Speech Recognition service; {e}")
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down system...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
