import os
import glob
import numpy as np
import tensorflow as tf
import librosa

SAMPLE_RATE = 16000

# Load Model
interpreter = tf.lite.Interpreter(model_path="light_model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def extract_mfcc(audio_data, sample_rate, n_mfcc=40, n_frames=44):
    audio_data = np.asarray(audio_data, dtype=np.float32).flatten()
    mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=n_mfcc)
    mfcc = mfcc[:, :n_frames]
    if mfcc.shape[1] < n_frames:
        pad_width = n_frames - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    return mfcc

wav_files = glob.glob(os.path.join("WAV", "*.wav"))

if not wav_files:
    print("No WAV files found.")
    exit()

print(f"Found {len(wav_files)} files to test. Analyzing...\n")

for file_path in wav_files:
    filename = os.path.basename(file_path)
    try:
        # Robustly load and resample to 16000 Hz
        audio, file_sample_rate = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)

        audio_data = audio.flatten()
        mfcc = extract_mfcc(audio_data, SAMPLE_RATE)
        input_data = mfcc.reshape(1, 40, 44, 1).astype(np.float32)

        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        prediction = interpreter.get_tensor(output_details[0]['index'])

        confidence = float(np.max(prediction)) * 100
        predicted_index = np.argmax(prediction)
        
        label = "LIGHT_ON" if predicted_index == 0 else "UNKNOWN"
        
        print(f"File: {filename}")
        print(f"  🧠 Prediction: {label}")
        print(f"  📊 Confidence: {confidence:.2f}%")
        print("-" * 30)

    except Exception as e:
        print(f"Failed to process {filename}: {e}")
