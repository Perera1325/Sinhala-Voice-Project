import os
import sys
import time
import numpy as np
import tensorflow as tf
import librosa
import requests
import sounddevice as sd
import scipy.signal as signal
import warnings

# Import your custom modules
import database
import speaker_biometrics

warnings.filterwarnings('ignore')

# =========================
# CONFIGURATION
# =========================
SAMPLE_RATE = 16000
DURATION = 3
CONFIDENCE_THRESHOLD = 75.0  # Must be >75% sure it's the Sinhala command

# Hardware IP addresses (ESP32 Web Server)
# Make sure this matches your ESP32's IP address on the network
ESP32_API_URL = "http://192.168.1.13:5000/channels/b21642ae-34f1-485c-b459-351bafcdf920/control"

# =========================
# WINNING NOISE REDUCTION METHOD
# =========================
def apply_highpass_filter(audio, cutoff=150):
    """
    Applies the High-Pass filter (Best method from our 75-condition analysis 
    for real-world home appliance noise like fans/AC hums).
    """
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

# =========================
# INITIALIZE TFLITE AI MODEL
# =========================
print("Loading Sinhala AI Intent Model...")
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(parent_dir, "Deploy_To_RaspberryPi", "light_model.tflite")

try:
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    print("✅ Model Ready!")
except Exception as e:
    print(f"❌ Could not load TFLite model at {model_path}. Error: {e}")
    sys.exit(1)

def extract_mfcc(audio_data, sample_rate, n_mfcc=40, n_frames=44):
    audio_data = np.asarray(audio_data, dtype=np.float32).flatten()
    mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=n_mfcc)
    mfcc = mfcc[:, :n_frames]
    
    if mfcc.shape[1] < n_frames:
        pad_width = n_frames - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    return mfcc

def turn_light_on_physically():
    print(f"🔌 Triggering ESP32 Relay over Network via Channel ID...")
    try:
        response = requests.post(ESP32_API_URL, json={"value": "ON"}, timeout=3)
        if response.status_code == 200:
            print("✅ PHYSICAL LIGHT TURNED ON!")
        else:
            print(f"⚠️ ESP32 returned status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to reach ESP32 at {ESP32_API_URL}: {e}")
        print("💡 Make sure your ESP32 is powered on and connected to the same Wi-Fi!")

# =========================
# MAIN LIVE LOOP
# =========================
def main():
    print("\n" + "="*80)
    print("🚀 ULTIMATE DEPLOYMENT: BIOMETRICS + NOISE REDUCTION + INTENT + HARDWARE 🚀")
    print("="*80)

    # 1. User Registration Flow
    database.init_db()
    users = database.get_all_users()
    
    reg_choice = input(f"You have {len(users)} users registered. Do you want to register a NEW user now? (y/n): ")
    if reg_choice.lower() == 'y':
        name = input("Enter your name: ")
        print("Recording for 3 seconds. Please speak normally to register your voice...")
        audio = sd.rec(int(3.0 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        
        fingerprint = speaker_biometrics.extract_voice_fingerprint(audio_data=audio.flatten())
        if fingerprint:
            database.add_user(name, fingerprint)
            print(f"✅ User '{name}' registered successfully!\n")
            users = database.get_all_users()
        else:
            print("❌ Failed to register. Audio too silent.\n")

    print("\n" + "="*80)
    print("SYSTEM ACTIVE. Awaiting Commands...")
    
    while True:
        try:
            print("\n⏳ Listening... Say 'light eka danna'")
            
            # 2. Record audio from microphone
            audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            audio_data = audio.flatten()
            
            # Ignore complete silence so the console doesn't spam
            if np.max(np.abs(audio_data)) < 0.01:
                continue
                
            print("🔊 Voice captured!")
            
            # 3. APPLY NOISE REDUCTION BEFORE BIOMETRICS/AI
            print("🧹 Applying HighPass Noise Reduction...")
            clean_audio_data = apply_highpass_filter(audio_data)
            
            # 4. BIOMETRIC AUTHENTICATION
            is_auth, user_name = speaker_biometrics.verify_speaker(clean_audio_data, users)
            if not is_auth:
                print("🚫 Intruder Alert: Unrecognized voice. Denying hardware access.")
                time.sleep(1)
                continue
                
            print(f"✅ Identity Verified: Welcome, {user_name}!")
                
            # 5. AI INTENT MATCHING
            mfcc = extract_mfcc(clean_audio_data, SAMPLE_RATE)
            input_data = mfcc.reshape(1, 40, 44, 1).astype(np.float32)

            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            prediction = interpreter.get_tensor(output_details[0]['index'])
            
            confidence = float(np.max(prediction)) * 100
            predicted_index = np.argmax(prediction)

            if predicted_index == 0 and confidence > CONFIDENCE_THRESHOLD:
                print(f"🧠 Sinhala Command Detected: LIGHT_ON (Confidence: {confidence:.1f}%)")
                
                # 6. TRIGGER HARDWARE
                turn_light_on_physically()
                
                # Cooldown so it doesn't trigger 5 times in a row
                time.sleep(3)
            else:
                print(f"🤷 Unknown Command/Noise (Confidence: {confidence:.1f}%)")

        except KeyboardInterrupt:
            print("\nStopping assistant...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
