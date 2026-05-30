import os
import glob
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import librosa

# =========================
# CONFIGURATION FOR LID
# =========================
SAMPLE_RATE = 16000
DURATION = 3.0  # Language ID needs more time than a keyword
N_MFCC = 40
N_FRAMES = 94   # (16000 * 3) / 512 = ~94 frames

DATASET_DIR = "Data_Set_LID"
CLASSES = {"SINHALA": 0, "OTHER": 1}

def extract_mfcc(audio_path):
    try:
        audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True, duration=DURATION)
        
        # Pad with zeros if shorter than DURATION
        if len(audio) < int(SAMPLE_RATE * DURATION):
            pad_width = int(SAMPLE_RATE * DURATION) - len(audio)
            audio = np.pad(audio, (0, pad_width), mode='constant')

        mfcc = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=N_MFCC)
        mfcc = mfcc[:, :N_FRAMES]
        
        if mfcc.shape[1] < N_FRAMES:
            pad_width = N_FRAMES - mfcc.shape[1]
            mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
            
        return mfcc
    except Exception as e:
        print(f"Error processing {audio_path}: {e}")
        return None

# =========================
# LOAD DATASET
# =========================
X = []
y = []

print("Loading LID Dataset...")
for class_name, class_label in CLASSES.items():
    class_dir = os.path.join(DATASET_DIR, class_name)
    if not os.path.exists(class_dir):
        print(f"Directory {class_dir} not found. Creating it...")
        os.makedirs(class_dir)
        continue

    files = glob.glob(os.path.join(class_dir, "*.wav"))
    print(f"Found {len(files)} files for {class_name}")
    
    for f in files:
        mfcc = extract_mfcc(f)
        if mfcc is not None:
            X.append(mfcc)
            y.append(class_label)

if len(X) == 0:
    print("❌ No data found! Please add .wav files to Data_Set_LID/SINHALA and Data_Set_LID/OTHER")
    exit(1)

X = np.array(X)[..., np.newaxis]  # Add channel dimension
y = np.array(y)

print(f"Dataset Shape: {X.shape}")

# Shuffle
indices = np.arange(X.shape[0])
np.random.shuffle(indices)
X = X[indices]
y = y[indices]

# =========================
# BUILD CNN MODEL
# =========================
model = models.Sequential([
    layers.Input(shape=(N_MFCC, N_FRAMES, 1)),
    
    # Batch Normalization natively handles scaling
    layers.BatchNormalization(),
    
    layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.25),

    layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.25),

    layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.25),

    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(2, activation='softmax')
])

model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

print("Training LID Model...")
model.fit(X, y, epochs=30, batch_size=32, validation_split=0.2)

# =========================
# SAVE MODEL
# =========================
model.save("sinhala_lid_model.h5")

converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open("sinhala_lid_model.tflite", "wb") as f:
    f.write(tflite_model)

print("✅ Success! Saved sinhala_lid_model.tflite")
