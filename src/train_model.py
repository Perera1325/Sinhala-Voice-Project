import os
import glob
import numpy as np
import librosa
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras import layers, models

from config import DATA_SET_DIR, AUGMENTED_DIR, MODELS_DIR, CLASSES, NUM_CLASSES, EPOCHS, BATCH_SIZE

SAMPLE_RATE = 16000

def extract_mfcc(audio_data, sample_rate, n_mfcc=40, n_frames=44):
    """
    EXACT copy of the feature extraction from the user's inference script.
    """
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

def prepare_dataset():
    X = []
    y = []
    
    dataset_path = AUGMENTED_DIR if os.path.exists(AUGMENTED_DIR) else DATA_SET_DIR
    print(f"Loading data from: {dataset_path}")
    
    class_name_to_id = {v: k for k, v in CLASSES.items()}
    
    for class_name, class_id in class_name_to_id.items():
        class_dir = os.path.join(dataset_path, class_name)
        if not os.path.exists(class_dir):
            continue
            
        files = glob.glob(os.path.join(class_dir, "*.wav"))
        print(f"Processing {len(files)} files for class {class_name}...")
        
        for file in files:
            try:
                # Load audio
                audio, sr = librosa.load(file, sr=SAMPLE_RATE)
                
                # Extract features using the EXACT function from inference script
                features = extract_mfcc(audio, SAMPLE_RATE)
                
                X.append(features)
                y.append(class_id)
            except Exception as e:
                print(f"Error processing {file}: {e}")
                
    X = np.array(X)
    y = np.array(y)
    return X, y

def build_model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),
        # Crucial: BatchNormalization as the first layer handles the lack of an external scaler!
        # It normalizes the raw MFCC values during training and bakes the scaling into the TFLite model.
        layers.BatchNormalization(), 
        
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.2),
        
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.2),
        
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(NUM_CLASSES, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("Step 1: Extracting features...")
    X, y = prepare_dataset()
    
    if len(X) == 0:
        print("No valid data found.")
        return
        
    print(f"Extracted shape: {X.shape}") # Should be (num_samples, 40, 44)
    
    # Reshape for model input (add channel dimension)
    # The inference script uses shape: (1, 40, 44, 1)
    X = X[..., np.newaxis] 
    
    print(f"Final Input Shape for Model: {X.shape}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Step 2: Training model...")
    model = build_model(input_shape=(40, 44, 1))
    model.summary()
    
    model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE
    )
    
    loss, accuracy = model.evaluate(X_test, y_test)
    print(f"Test Accuracy: {accuracy * 100:.2f}%")
    
    model_path = os.path.join(MODELS_DIR, "light_model.h5")
    model.save(model_path)
    print(f"Saved model to {model_path}")
    
if __name__ == "__main__":
    main()
