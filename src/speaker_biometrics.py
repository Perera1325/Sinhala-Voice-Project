import numpy as np
import librosa
from scipy.spatial.distance import cosine

# Configuration
SAMPLE_RATE = 16000
N_MFCC = 40
MATCH_THRESHOLD = 0.80  # Increased security threshold to 80% to reject strangers

def extract_voice_fingerprint(audio_path=None, audio_data=None):
    """
    Extracts a highly unique mathematical fingerprint (embedding) from an audio sample.
    """
    try:
        if audio_path:
            audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
        elif audio_data is not None:
            audio = np.asarray(audio_data, dtype=np.float32).flatten()
        else:
            raise ValueError("Must provide either audio_path or audio_data")

        # Ignore silence: only extract features from non-silent parts
        audio, _ = librosa.effects.trim(audio, top_db=40)
        
        if len(audio) < SAMPLE_RATE * 0.5:
            print("⚠️ Audio too short for biometric extraction")
            return None

        # Extract MFCCs
        mfcc = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=N_MFCC)
        
        # CRITICAL FIX: Drop the 0th coefficient (mfcc[1:]) 
        # The 0th coefficient represents overall volume/energy. If included, it forces 
        # all human voices to score 95%+ similarity. Dropping it forces the math to 
        # look at the actual vocal tract shape.
        voice_fingerprint = np.mean(mfcc[1:], axis=1)
        
        # Normalize the vector for cosine similarity
        norm = np.linalg.norm(voice_fingerprint)
        if norm > 0:
            voice_fingerprint = voice_fingerprint / norm
            
        return voice_fingerprint.tolist()

    except Exception as e:
        print(f"[ERROR] Error extracting biometrics: {e}")
        return None

def verify_speaker(incoming_audio_data, database_users):
    """
    Compares the incoming live audio against all registered users in the database.
    Returns (True, user_name) if a match is found. 
    If no users exist, returns True for testing purposes.
    """
    if not database_users:
        print("⚠️ No users registered in database. Denying access.")
        return False, None

    live_fingerprint = extract_voice_fingerprint(audio_data=incoming_audio_data)
    
    if live_fingerprint is None:
        return False, None

    best_match_name = None
    best_similarity = 0.0

    for user in database_users:
        user_name = user["name"]
        registered_fingerprint = np.array(user["embedding"])
        
        distance = cosine(live_fingerprint, registered_fingerprint)
        similarity = 1.0 - distance
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match_name = user_name

    print(f"[AUTH] Checking Voice Biometrics... [DB Size: {len(database_users)}] Best match is {best_match_name} at {best_similarity*100:.1f}%")

    if best_similarity >= MATCH_THRESHOLD:
        return True, best_match_name
    else:
        return False, None
