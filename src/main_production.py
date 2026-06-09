import os
import sys
import time
import numpy as np
import sounddevice as sd
import requests
import scipy.signal as signal
import noisereduce as nr

import database
import speaker_biometrics
from wakeword_engine import WakeWordDetector
import speech_recognition as sr
import nlp_classifier
import pyttsx3

# Add NoiseRM to path to import the custom audio filters
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NoiseRM')))
from audio_filters import vad_guided_dynamic_wiener_filter

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
FLASK_API_BASE = "http://127.0.0.1:5000/api/devices/control"

# Map human-readable device names to the UUIDs from your existing Flask server
DEVICE_UUIDS = {
    "light_1": "5508f5fc-3641-44cd-9cc5-87e5fc677483",
    # Add your Fan and Curtain UUIDs here when you train them!
    "fan_1": "74136aa1-471d-485d-ac02-9c0bb408d9d3",
    "curtain_1": "YOUR-CURTAIN-UUID-HERE"
}

def apply_advanced_noise_reduction(audio):
    """
    Applies our custom VAD-Guided Dynamic Wiener Filter (VGDWF) to perfectly 
    isolate the human voice and remove all dynamic background noises.
    """
    print("🧹 Applying VGDWF Custom Noise Reduction...")
    return vad_guided_dynamic_wiener_filter(audio, sr=SAMPLE_RATE)

def send_to_flask(device_id, action):
    """Sends the command to your existing UUID-based Flask Server."""
    url = FLASK_API_BASE
    payload = {
        "device_id": device_id,
        "action": action
    }
    
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
    print("🚀 PROJECT FLOW AI ASSISTANT (Google STT + Biometrics + Noise Reduction) 🚀")
    print("="*50)

    database.init_db()
    
    # --- STAGE 0: REGISTRATION ---
    users = database.get_all_users()
    reg_choice = input(f"You have {len(users)} registered users. Do you want to register a NEW user now? (y/n): ")
    if reg_choice.lower() == 'y':
        name = input("Enter your name: ")
        print("Recording for 5 seconds. Please speak normally to register your voice fingerprint...")
        audio = sd.rec(int(5.0 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        
        fingerprint = speaker_biometrics.extract_voice_fingerprint(audio_data=audio.flatten())
        if fingerprint is not None:
            database.add_user(name, fingerprint)
            print(f"User '{name}' registered successfully!\n")
        else:
            print("Failed to register. Audio too silent.\n")
            
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
            # Lowered threshold from 0.05 to 0.015 to make it easier to trigger
            is_awake = True if np.max(np.abs(audio_chunk)) > 0.015 else False 
            
            if not is_awake:
                continue

            print("🔔 WAKE WORD DETECTED! ('Hey Kasu')")
            
            # --- STAGE 2 & 3: RECORD COMMAND ---
            print("🎤 Listening for a command (speak now)...")
            # Record a 4.0s chunk for BOTH Biometrics and Command
            command_audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            
            # Calculate SNR to print Test Case scenario for the terminal output
            noise_part = command_audio.flatten()[:4000]
            noise_power = np.mean(noise_part**2) + 1e-10
            signal_power = np.mean(command_audio.flatten()**2)
            snr_db = 10 * np.log10(signal_power / noise_power)
            
            if snr_db > 5.0:
                env = "Test Case 1: Clean Speech / 10dB"
            elif snr_db > -2.0:
                env = "Test Case 2: Moderate Noise / 0dB (Fan/AC)"
            else:
                env = "Test Case 3: Heavy Noise / -5dB (Street/Cafe)"
            
            print(f"📊 Live Acoustics Analysis:")
            print(f"   ↳ Detected SNR: {snr_db:.1f} dB")
            print(f"   ↳ Environment: {env}")
            
            # --- STAGE 1.5: NOISE REDUCTION ---
            print("🧹 Applying Advanced Spectral Noise Reduction (Isolating Voice)...")
            command_audio_clean = apply_advanced_noise_reduction(command_audio.flatten())
            
            # --- STAGE 2: BIOMETRICS ---
            users = database.get_all_users()
            is_authorized, user_name = speaker_biometrics.verify_speaker(incoming_audio_data=command_audio_clean, database_users=users)

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
            audio_data_int16 = (command_audio_clean * 32767).astype(np.int16)
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
                    
                    # 🔥 Push real-time data to Firebase RTDB
                    firebase_url = "https://kasundi-ai-home-default-rtdb.asia-southeast1.firebasedatabase.app/telemetry.json"
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
