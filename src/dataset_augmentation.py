import os
import glob
import numpy as np
import librosa
import soundfile as sf
from tqdm import tqdm
from config import DATA_SET_DIR, AUGMENTED_DIR, SAMPLE_RATE

def add_noise(data, noise_factor=0.005):
    noise = np.random.randn(len(data))
    augmented_data = data + noise_factor * noise
    return augmented_data

def time_stretch(data, rate=1.0):
    return librosa.effects.time_stretch(y=data, rate=rate)

def pitch_shift(data, sampling_rate, n_steps=2.0):
    return librosa.effects.pitch_shift(y=data, sr=sampling_rate, n_steps=n_steps)

def change_volume(data, volume_factor=1.0):
    return data * volume_factor

def augment_class(class_name, target_count=1000):
    source_dir = os.path.join(DATA_SET_DIR, class_name)
    target_dir = os.path.join(AUGMENTED_DIR, class_name)
    
    os.makedirs(target_dir, exist_ok=True)
    
    original_files = glob.glob(os.path.join(source_dir, "*.wav"))
    
    if not original_files:
        print(f"Warning: No wav files found in {source_dir}")
        return

    print(f"Found {len(original_files)} original files in {class_name}. Augmenting to {target_count}...")
    
    # First, copy original files to the new directory
    count = 0
    for f in original_files:
        data, _ = librosa.load(f, sr=SAMPLE_RATE)
        out_path = os.path.join(target_dir, f"orig_{os.path.basename(f)}")
        sf.write(out_path, data, SAMPLE_RATE)
        count += 1
        
    # Then generate augmented versions until we hit target_count
    with tqdm(total=target_count, initial=count) as pbar:
        while count < target_count:
            # Pick a random original file
            f = np.random.choice(original_files)
            data, _ = librosa.load(f, sr=SAMPLE_RATE)
            
            # Apply a random sequence of augmentations
            aug_type = np.random.choice(['noise', 'stretch', 'pitch', 'volume', 'combined'])
            
            if aug_type == 'noise':
                data = add_noise(data, noise_factor=np.random.uniform(0.001, 0.01))
            elif aug_type == 'stretch':
                data = time_stretch(data, rate=np.random.uniform(0.8, 1.2))
            elif aug_type == 'pitch':
                data = pitch_shift(data, SAMPLE_RATE, n_steps=np.random.uniform(-3, 3))
            elif aug_type == 'volume':
                data = change_volume(data, volume_factor=np.random.uniform(0.5, 1.5))
            else:
                # Combined
                data = change_volume(data, volume_factor=np.random.uniform(0.8, 1.2))
                data = add_noise(data, noise_factor=np.random.uniform(0.001, 0.005))
                data = pitch_shift(data, SAMPLE_RATE, n_steps=np.random.uniform(-1, 1))

            out_path = os.path.join(target_dir, f"aug_{aug_type}_{count}.wav")
            sf.write(out_path, data, SAMPLE_RATE)
            count += 1
            pbar.update(1)

def main():
    if not os.path.exists(DATA_SET_DIR):
        print(f"Error: Dataset directory {DATA_SET_DIR} does not exist.")
        return
        
    print("Starting data augmentation...")
    augment_class("LIGHT_ON", 1000)
    augment_class("UNKNOWN", 1000)
    print("Data augmentation complete! Augmented dataset saved to:", AUGMENTED_DIR)

if __name__ == "__main__":
    main()
