# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: speaker_recognition.py
# Description: Implements speaker verification using the SpeechBrain ECAPA-TDNN 
#              model to verify speaker identity based on cosine similarity.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

import os
import numpy as np
import shutil

# Monkey-patch os.symlink on Windows to bypass WinError 1314 (missing symlink privilege)
if os.name == 'nt':
    orig_symlink = os.symlink
    def symlink_fallback(src, dst, target_is_directory=False):
        try:
            orig_symlink(src, dst, target_is_directory)
        except OSError:
            # If symlinking fails due to lack of privileges, copy the file/directory instead
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    os.symlink = symlink_fallback

# Suppress SpeechBrain and PyTorch logs for cleaner execution output
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
import logging
logging.getLogger("speechbrain").setLevel(logging.ERROR)

# Pre-initialized classifier placeholder
_classifier = None

def get_speaker_classifier():
    """Lazy initialization of SpeechBrain EncoderClassifier to optimize startup time."""
    global _classifier
    if _classifier is None:
        try:
            import torch
            import torchaudio
            from speechbrain.inference.speaker import EncoderClassifier
            
            # Directory to store the pre-trained SpeechBrain models
            model_dir = r"C:\Users\Kasundi\Downloads\NoiseRM\pretrained_models\spkrec-ecapa-voxceleb"
            os.makedirs(model_dir, exist_ok=True)
            
            print("[INFO] Loading SpeechBrain speaker verification model (ECAPA-TDNN)...")
            _classifier = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=model_dir
            )
            print("[INFO] Model loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load SpeechBrain model: {e}")
            raise e
    return _classifier

def extract_embedding(audio_path):
    """
    Loads a 16kHz audio file and extracts its speaker verification embedding (192-D).
    
    Parameters:
    - audio_path: Absolute path to the WAV file.
    
    Returns:
    - 1D numpy array representing the speaker's voice embedding.
    """
    try:
        import soundfile as sf
        import torch
        import torchaudio
        
        # Load model
        classifier = get_speaker_classifier()
        
        # Load audio file using soundfile to bypass torchaudio/torchcodec backend errors on Windows
        data, fs = sf.read(audio_path)
        
        # Ensure mono channel format
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
            
        # Convert to PyTorch tensor with shape [1, samples]
        signal = torch.tensor(data, dtype=torch.float32).unsqueeze(0)
        
        # Resample to 16kHz if necessary (SpeechBrain requires 16000 Hz)
        if fs != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=fs, new_freq=16000)
            signal = resampler(signal)
            
        # Encode the batch of audio signals (shape: [1, time_steps])
        with torch.no_grad():
            embeddings = classifier.encode_batch(signal)
            
        # Extract, squeeze, and convert to numpy array
        embedding_np = embeddings.squeeze().cpu().numpy()
        
        # Normalize the embedding to unit length
        norm = np.linalg.norm(embedding_np)
        if norm > 0:
            embedding_np = embedding_np / norm
            
        return embedding_np
    except Exception as e:
        print(f"[ERROR] Error extracting speaker embedding from {audio_path}: {e}")
        return None

def enroll_user(audio_path, save_path=r"C:\Users\Kasundi\Downloads\NoiseRM\user_embedding.npy"):
    """
    Enrolls a user by extracting their voice embedding and saving it to disk.
    
    Parameters:
    - audio_path: WAV audio path of the user's registration command.
    - save_path: Path where the voice embedding will be saved.
    
    Returns:
    - True if successful, False otherwise.
    """
    print(f"[INFO] Enrolling speaker using audio file: {audio_path}")
    embedding = extract_embedding(audio_path)
    
    if embedding is not None:
        try:
            np.save(save_path, embedding)
            print(f"[OK] Voice embedding saved successfully to: {save_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save embedding file: {e}")
            return False
    else:
        print("[ERROR] Embedding extraction failed during enrollment.")
        return False

def verify_speaker(test_audio_path, enrollment_path=r"C:\Users\Kasundi\Downloads\NoiseRM\user_embedding.npy", threshold=0.68):
    """
    Verifies if the speaker in the test audio matches the enrolled speaker.
    
    Parameters:
    - test_audio_path: WAV audio path of the wake word command.
    - enrollment_path: Saved registered user embedding path.
    - threshold: Cosine similarity threshold (0.0 to 1.0). Usually 0.70 - 0.78 is ideal.
    
    Returns:
    - Tuple: (is_matched, similarity_score)
    """
    if not os.path.exists(enrollment_path):
        print(f"[ERROR] Enrollment file not found at: {enrollment_path}. Please register first.")
        return False, 0.0
        
    test_embedding = extract_embedding(test_audio_path)
    if test_embedding is None:
        print("[ERROR] Failed to extract embedding from test audio.")
        return False, 0.0
        
    try:
        # Load registered voice print
        registered_embedding = np.load(enrollment_path)
        
        # Calculate cosine similarity (embeddings are already unit normalized)
        similarity = np.dot(registered_embedding, test_embedding)
        
        is_matched = bool(similarity >= threshold)
        print(f"[INFO] Speaker match test: Similarity={similarity:.4f} (Threshold={threshold:.2f}) -> Match={is_matched}")
        return is_matched, similarity
    except Exception as e:
        print(f"[ERROR] Speaker verification failed: {e}")
        return False, 0.0

if __name__ == "__main__":
    print("Speaker recognition module loaded.")
