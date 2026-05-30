import os
import time
import numpy as np
import librosa
import joblib
import sounddevice as sd
import tensorflow as tf
import requests

from config import (
    MODELS_DIR, SAMPLE_RATE, DURATION, N_MFCC, N_FFT, HOP_LENGTH, MAX_PAD_LEN,
    CLASSES, CONFIDENCE_THRESHOLD, RMS_ENERGY_THRESHOLD, 
    FLASK_API_URL, MQTT_BROKER, MQTT_PORT, MQTT_TOPIC
)

# Initialize TFLite model
tflite_model_path = os.path.join(MODELS_DIR, "light_model.tflite")
if not os.path.exists(tflite_model_path):
    print(f"Error: {tflite_model_path} not found.")
    exit(1)

interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Load scaler
scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
if not os.path.exists(scaler_path):
    print(f"Error: {scaler_path} not found. Must use the exact scaler from training.")
    exit(1)
scaler = joblib.load(scaler_path)

def send_flask_request():
    try:
        response = requests.post(FLASK_API_URL, json={"command": "LIGHT_ON"}, timeout=2)
        print(f"Flask API Response: {response.status_code}")
    except Exception as e:
        print(f"Flask API Error: {e}")

def send_mqtt_command():
    try:
        import paho.mqtt.client as mqtt
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 2)
        client.publish(MQTT_TOPIC, "ON")
        client.disconnect()
        print("MQTT Command Sent.")
    except Exception as e:
        print(f"MQTT Error: {e}")

def process_audio_buffer(audio_data):
    """
    Processes a raw audio buffer exactly the same way as train_model.py
    """
    # Calculate RMS energy for thresholding to avoid processing pure silence
    rms_energy = np.sqrt(np.mean(audio_data**2))
    
    if rms_energy < RMS_ENERGY_THRESHOLD:
        # Too quiet, ignore
        return None, rms_energy
        
    # Extract MFCC
    mfcc = librosa.feature.mfcc(
        y=audio_data, 
        sr=SAMPLE_RATE, 
        n_mfcc=N_MFCC, 
        n_fft=N_FFT, 
        hop_length=HOP_LENGTH
    )
    
    # Transpose and pad exactly like training
    mfcc = mfcc.T
    
    if mfcc.shape[0] > MAX_PAD_LEN:
        mfcc = mfcc[:MAX_PAD_LEN, :]
    elif mfcc.shape[0] < MAX_PAD_LEN:
        mfcc = np.pad(mfcc, ((0, max(0, MAX_PAD_LEN - mfcc.shape[0])), (0, 0)), "constant")
        
    # Flatten and apply scaler
    features = mfcc.shape[1]
    mfcc_flattened = mfcc.reshape(-1, features)
    mfcc_scaled = scaler.transform(mfcc_flattened) # USE TRANSFORM, NOT FIT_TRANSFORM
    
    # Reshape for model input
    input_tensor = mfcc_scaled.reshape(1, MAX_PAD_LEN, features, 1).astype(np.float32)
    return input_tensor, rms_energy

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Audio Status: {status}")
        
    # Squeeze channel dimension
    audio_data = indata[:, 0]
    
    input_tensor, rms = process_audio_buffer(audio_data)
    
    if input_tensor is None:
        return # Silence
        
    # Inference
    interpreter.set_tensor(input_details[0]['index'], input_tensor)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])[0]
    
    predicted_class_id = np.argmax(output_data)
    confidence = output_data[predicted_class_id]
    predicted_label = CLASSES[predicted_class_id]
    
    # Debug Output Requested by User
    print("-" * 30)
    print(f"Audio RMS Energy : {rms:.5f}")
    print(f"Tensor Shape     : {input_tensor.shape}")
    print(f"Raw Probabilities: {output_data}")
    print(f"Predicted Class  : {predicted_label} ({predicted_class_id})")
    print(f"Confidence       : {confidence:.2%}")
    
    # Thresholding Logic
    if predicted_class_id == 0 and confidence > CONFIDENCE_THRESHOLD:
        print("\n>>> COMMAND DETECTED: LIGHT_ON <<<")
        print(">>> Executing Actions...\n")
        send_flask_request()
        send_mqtt_command()
        # Sleep to avoid double triggering
        time.sleep(2.0) 
    else:
        # If the confidence is too low or it's classified as unknown
        print(">>> UNKNOWN / NO ACTION")
        
def main():
    print("Starting Offline Sinhala/Singlish AI Home Assistant...")
    print(f"Listening at {SAMPLE_RATE}Hz. Press Ctrl+C to stop.")
    
    # We record DURATION seconds of audio at a time
    blocksize = int(SAMPLE_RATE * DURATION)
    
    try:
        # Use sd.InputStream for continuous block-by-block processing
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=blocksize,
            callback=audio_callback
        ):
            while True:
                sd.sleep(1000)
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nMicrophone Error: {e}")

if __name__ == "__main__":
    main()
