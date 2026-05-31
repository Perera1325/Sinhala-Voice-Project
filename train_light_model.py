import os
import glob
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import librosa
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import train_test_split

# =========================
# CONFIGURATION
# =========================
SAMPLE_RATE = 16000
DURATION = 3.0  
N_MFCC = 40
N_FRAMES = 94   # (16000 * 3) / 512 = ~94 frames

DATASET_DIR = "Data_set"
CLASSES = {"UNKNOWN": 0, "LIGHT_ON": 1}
SCREENSHOTS_DIR = "screenshots"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# =========================
# FEATURE EXTRACTION
# =========================
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

print("Loading Dataset for 'Light On' Function...")
for class_name, class_label in CLASSES.items():
    class_dir = os.path.join(DATASET_DIR, class_name)
    if not os.path.exists(class_dir):
        print(f"Directory {class_dir} not found. Skipping...")
        continue

    files = glob.glob(os.path.join(class_dir, "*.wav"))
    print(f"Found {len(files)} files for class: {class_name}")
    
    for f in files:
        mfcc = extract_mfcc(f)
        if mfcc is not None:
            X.append(mfcc)
            y.append(class_label)

if len(X) == 0:
    print("❌ No data found! Exiting.")
    exit(1)

X = np.array(X)[..., np.newaxis]  # Add channel dimension
y = np.array(y)

print(f"Dataset Shape: {X.shape}")

# Split into train and test sets (80% Train, 20% Test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Training Samples: {len(X_train)} | Testing Samples: {len(X_test)}")

# =========================
# BUILD CNN MODEL
# =========================
model = models.Sequential([
    layers.Input(shape=(N_MFCC, N_FRAMES, 1)),
    
    layers.BatchNormalization(),
    
    layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.25),

    layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
    layers.MaxPooling2D((2, 2)),
    layers.Dropout(0.25),

    layers.Flatten(),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(2, activation='softmax')
])

model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

print("\nTraining Deep Learning Model for 'Light On' Detection...")
history = model.fit(X_train, y_train, epochs=25, batch_size=32, validation_data=(X_test, y_test))

# =========================
# EVALUATION & PLOTTING
# =========================
print("\nGenerating PhD Research Graphs...")

# 1. Accuracy Plot
plt.figure(figsize=(8, 6))
plt.plot(history.history['accuracy'], label='Training Accuracy', linewidth=2, color='blue')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy', linewidth=2, color='orange')
plt.title('Model Accuracy (Light On vs Unknown)', fontsize=14, fontweight='bold')
plt.ylabel('Accuracy', fontsize=12)
plt.xlabel('Epoch', fontsize=12)
plt.legend(loc='lower right')
plt.grid(True, linestyle='--', alpha=0.7)
acc_path = os.path.join(SCREENSHOTS_DIR, "05_Accuracy_Graph.png")
plt.savefig(acc_path, dpi=300, bbox_inches='tight')
print(f"Saved Accuracy Graph -> {acc_path}")
plt.close()

# 2. Loss Plot
plt.figure(figsize=(8, 6))
plt.plot(history.history['loss'], label='Training Loss', linewidth=2, color='red')
plt.plot(history.history['val_loss'], label='Validation Loss', linewidth=2, color='green')
plt.title('Model Loss (Categorical Cross-Entropy)', fontsize=14, fontweight='bold')
plt.ylabel('Loss', fontsize=12)
plt.xlabel('Epoch', fontsize=12)
plt.legend(loc='upper right')
plt.grid(True, linestyle='--', alpha=0.7)
loss_path = os.path.join(SCREENSHOTS_DIR, "06_Loss_Graph.png")
plt.savefig(loss_path, dpi=300, bbox_inches='tight')
print(f"Saved Loss Graph -> {loss_path}")
plt.close()

# 3. Confusion Matrix
y_pred_prob = model.predict(X_test)
y_pred = np.argmax(y_pred_prob, axis=1)

cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(7, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Unknown', 'Light On'], yticklabels=['Unknown', 'Light On'])
plt.title('Confusion Matrix: Wake Word Detection', fontsize=14, fontweight='bold')
plt.ylabel('True Label', fontsize=12)
plt.xlabel('Predicted Label', fontsize=12)
cm_path = os.path.join(SCREENSHOTS_DIR, "07_Confusion_Matrix.png")
plt.savefig(cm_path, dpi=300, bbox_inches='tight')
print(f"Saved Confusion Matrix -> {cm_path}")
plt.close()

# Print Classification Report
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Unknown', 'Light On']))

# =========================
# SAVE MODEL
# =========================
model.save("light_model.h5")

converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open("light_model.tflite", "wb") as f:
    f.write(tflite_model)

print("\nSuccess! Saved final optimized model to 'light_model.tflite'")
print("All research graphs have been saved to the 'screenshots' folder. You can now use them in your PhD report!")
