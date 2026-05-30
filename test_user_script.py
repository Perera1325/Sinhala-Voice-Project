import os
import sys

# Force sounddevice to false for cloud testing
has_sounddevice = False

from scipy.io.wavfile import write, read

import numpy as np
import tensorflow as tf
import librosa

# =========================
# SETTINGS
# =========================

SAMPLE_RATE = 16000
DURATION = 3

# =========================
# LOAD TFLITE MODEL
# =========================

interpreter = tf.lite.Interpreter(
    model_path="light_model.tflite"
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()

output_details = interpreter.get_output_details()

print("✅ Model loaded")

# =========================
# RECORD AUDIO
# =========================

if has_sounddevice:

    print("\n🎤 Say LIGHT ON command...")

    import sounddevice as sd
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )

    sd.wait()

    write(
        "test.wav",
        SAMPLE_RATE,
        audio
    )

    print("✅ Audio recorded")

else:

    if os.path.exists("test.wav"):

        print("\n⚠️ sounddevice not available. Loading existing test.wav")

        file_sample_rate, audio = read("test.wav")

        if audio.ndim > 1:
            audio = audio[:, 0]

        if np.issubdtype(audio.dtype, np.integer):
            audio = audio.astype(np.float32) / np.iinfo(audio.dtype).max
        else:
            audio = audio.astype(np.float32)

        if file_sample_rate != SAMPLE_RATE:
            print(f"⚠️ Loaded WAV sample rate is {file_sample_rate}, expected {SAMPLE_RATE}")

        print("✅ Audio loaded from test.wav")

    else:

        print("❌ Missing sounddevice and no test.wav file found.")
        sys.exit(1)

# =========================
# EXTRACT MFCC
# =========================

def extract_mfcc(audio_data, sample_rate, n_mfcc=40, n_frames=44):

    audio_data = np.asarray(
        audio_data,
        dtype=np.float32
    ).flatten()

    mfcc = librosa.feature.mfcc(
        y=audio_data,
        sr=sample_rate,
        n_mfcc=n_mfcc
    )

    mfcc = mfcc[:, :n_frames]

    if mfcc.shape[1] < n_frames:

        pad_width = n_frames - mfcc.shape[1]

        mfcc = np.pad(
            mfcc,
            pad_width=((0, 0), (0, pad_width)),
            mode='constant'
        )

    return mfcc

# =========================
# PREPARE INPUT
# =========================

audio_data = audio.flatten()

mfcc = extract_mfcc(audio_data, SAMPLE_RATE)

input_data = mfcc.reshape(
    1,
    40,
    44,
    1
).astype(np.float32)

# =========================
# RUN INFERENCE
# =========================

interpreter.set_tensor(
    input_details[0]['index'],
    input_data
)

interpreter.invoke()

prediction = interpreter.get_tensor(
    output_details[0]['index']
)

print("\nRaw Prediction:")
print(prediction)

print("Shape:", prediction.shape)

for i, score in enumerate(prediction[0]):
    print(f"Class {i}: {score:.6f}")

confidence = float(np.max(prediction)) * 100

predicted_index = np.argmax(prediction)

# =========================
# OUTPUT
# =========================

if predicted_index == 0:

    label = "LIGHT_ON"

else:

    label = "UNKNOWN"

print(f"\n🧠 Prediction: {label}")

print(f"📊 Confidence: {confidence:.2f}%")

# =========================
# CONTROL LIGHT
# =========================

import requests

if label == "LIGHT_ON" and confidence > 40:
    print("💡 LIGHT ON SENT (Mocked for testing)")
else:
    print("⚠️ Command ignored")
