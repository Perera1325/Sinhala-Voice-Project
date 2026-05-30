import os
import sys
import time
import numpy as np
import tensorflow as tf
import librosa
import requests
import sounddevice as sd

# =========================
# CONFIGURATION
# =========================
SAMPLE_RATE = 16000
DURATION = 3
CONFIDENCE_THRESHOLD = 75.0  # Must be >75% sure it's the Sinhala command

# Hardware IP addresses (ESP32 / Flask)
ESP32_API_URL = "http://192.168.1.13:5000/channels/b21642ae-34f1-485c-b459-351bafcdf920/control"

# =========================
# INITIALIZE AI MODEL
# =========================
print("Loading Sinhala AI Model...")
interpreter = tf.lite.Interpreter(model_path="light_model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
print("✅ Model Ready!")

def extract_mfcc(audio_data, sample_rate, n_mfcc=40, n_frames=44):
    """Processes the audio exactly as the model expects"""
    audio_data = np.asarray(audio_data, dtype=np.float32).flatten()
    mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=n_mfcc)
    mfcc = mfcc[:, :n_frames]
    
    if mfcc.shape[1] < n_frames:
        pad_width = n_frames - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    return mfcc

def turn_light_on_physically():
    """Sends the command to the ESP32 Relay"""
    print("🔌 Triggering ESP32 Relay...")
    try:
        response = requests.post(ESP32_API_URL, json={"value": "ON"}, timeout=3)
        if response.status_code == 200:
            print("✅ PHYSICAL LIGHT TURNED ON!")
        else:
            print(f"⚠️ ESP32 returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to reach ESP32: {e}")

def play_sinhala_response():
    """Plays a voice saying 'Hari, light eka damma'"""
    # If you have a .wav file with your own voice saying "Hari", put it here:
    response_file = "hari_response.wav"
    if os.path.exists(response_file):
        try:
            import soundfile as sf
            data, fs = sf.read(response_file)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            print(f"Could not play audio response: {e}")
    else:
        print("🔊 (Assistant says: 'Hari, light eka damma!')")

# =========================
# MAIN LOOP
# =========================
print("\n" + "="*40)
print("🎙️ Offline Sinhala Assistant Active")
print("="*40)

while True:
    try:
        print("\n⏳ Listening... Say 'light eka danna' (Press Ctrl+C to stop)")
        
        # Record audio
        audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()  # Wait for 3 seconds of audio to record
        
        # Process the voice
        audio_data = audio.flatten()
        
        # Check if it's completely silent (ignore if no one is talking)
        if np.max(np.abs(audio_data)) < 0.02:
            continue
            
        mfcc = extract_mfcc(audio_data, SAMPLE_RATE)
        input_data = mfcc.reshape(1, 40, 44, 1).astype(np.float32)

        # AI Inference
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        prediction = interpreter.get_tensor(output_details[0]['index'])
        
        confidence = float(np.max(prediction)) * 100
        predicted_index = np.argmax(prediction)

        if predicted_index == 0 and confidence > CONFIDENCE_THRESHOLD:
            print(f"\n🧠 Sinhala Detected: LIGHT_ON ({confidence:.1f}%)")
            
            # 1. Answer back with voice
            play_sinhala_response()
            
            # 2. Trigger the hardware relay
            turn_light_on_physically()
            
            # Wait a moment before listening again
            time.sleep(2)
        else:
            print(f"🤷 Unknown/Noise (Confidence: {confidence:.1f}%)")

    except KeyboardInterrupt:
        print("\nStopping assistant...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
