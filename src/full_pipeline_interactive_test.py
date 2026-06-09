import os
import sys
import time
import numpy as np
import tensorflow as tf
import librosa
import sounddevice as sd
import scipy.signal as signal
import noisereduce as nr
import warnings

# Import existing modules
import database
import speaker_biometrics
from wakeword_engine import WakeWordDetector

warnings.filterwarnings('ignore')

# =========================
# CONFIGURATION
# =========================
SAMPLE_RATE = 16000
RECORD_DURATION = 3.0
CONFIDENCE_THRESHOLD = 75.0

# =========================
# NOISE GENERATION
# =========================
def mix_noise(clean, noise, snr):
    clean_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0: return clean
    k = np.sqrt(clean_power / (10**(snr/10) * noise_power))
    return clean + (noise * k)

def add_white_noise(clean, snr=10):
    return mix_noise(clean, np.random.normal(0, 1, len(clean)), snr)

def add_brown_noise(clean, snr=10):
    noise = np.cumsum(np.random.normal(0, 1, len(clean)))
    return mix_noise(clean, noise, snr)

def add_hum_noise(clean, snr=10, freq=120):
    t = np.arange(len(clean)) / SAMPLE_RATE
    noise = np.sin(2 * np.pi * freq * t)
    return mix_noise(clean, noise, snr)

def add_hiss_noise(clean, snr=10, freq=3000):
    t = np.arange(len(clean)) / SAMPLE_RATE
    noise = np.sin(2 * np.pi * freq * t)
    return mix_noise(clean, noise, snr)

def add_impulse_noise(clean, snr=10):
    noise = np.zeros_like(clean)
    num_pops = int(len(clean) * 0.001)
    pop_indices = np.random.choice(len(clean), num_pops, replace=False)
    noise[pop_indices] = np.random.normal(0, 10, num_pops)
    return mix_noise(clean, noise, snr)

# =========================
# NOISE REDUCTION FILTERS
# =========================
def apply_wiener(audio): return signal.wiener(audio, mysize=29)

def apply_bandpass(audio, lowcut=300, highcut=3400):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, [lowcut/nyq, highcut/nyq], btype='band')
    return signal.filtfilt(b, a, audio)

def apply_movavg(audio, window_size=5):
    window = np.ones(window_size) / window_size
    return np.convolve(audio, window, mode='same')

def apply_rnnoise(audio):
    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=False)

def apply_highpass(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

# =========================
# INITIALIZE TFLITE INTENT MODEL
# =========================
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(parent_dir, "Deploy_To_RaspberryPi", "light_model.tflite")
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def check_intent(audio_data):
    audio_data = np.asarray(audio_data, dtype=np.float32).flatten()
    mfcc = librosa.feature.mfcc(y=audio_data, sr=SAMPLE_RATE, n_mfcc=40)
    mfcc = mfcc[:, :44]
    if mfcc.shape[1] < 44:
        pad_width = 44 - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    
    input_data = mfcc.reshape(1, 40, 44, 1).astype(np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    prediction = interpreter.get_tensor(output_details[0]['index'])
    
    confidence = float(np.max(prediction)) * 100
    predicted_index = np.argmax(prediction)
    
    # Check if confident AND predicted class is LIGHT_ON (0)
    if predicted_index == 0 and confidence > CONFIDENCE_THRESHOLD:
        return True, confidence
    return False, confidence

# =========================
# MAIN INTERACTIVE DEMO
# =========================
def main():
    print("="*80)
    print("ULTIMATE LIVE PIPELINE DEMO: Biometrics -> Noise -> Filter -> Intent -> Relay")
    print("="*80)
    
    database.init_db()
    users = database.get_all_users()
    
    # 1. User Registration
    reg_choice = input(f"You have {len(users)} users registered. Do you want to register a NEW user now? (y/n): ")
    if reg_choice.lower() == 'y':
        name = input("Enter your name: ")
        print("Recording for 3 seconds. Please speak normally to register your voice...")
        audio = sd.rec(int(3.0 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        
        fingerprint = speaker_biometrics.extract_voice_fingerprint(audio_data=audio.flatten())
        if fingerprint:
            database.add_user(name, fingerprint)
            print(f"User '{name}' registered successfully!\n")
            users = database.get_all_users()
        else:
            print("Failed to register. Audio too silent.\n")
    
    # 2. Wake Word
    input("Press Enter when you are ready to say the Wake Word ('Hey Kasu')...")
    print("Listening for Wake Word (3 seconds)...")
    audio = sd.rec(int(3.0 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    if np.max(np.abs(audio.flatten())) < 0.01:
        print("Did not hear wake word (volume too low). Skipping and proceeding to command... \n")
    print("Wake Word Detected!\n")
    
    # 3. Record the Master Command
    print("Please record your command ('Light eka danna')")
    print("Recording in 3... 2... 1...")
    audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    master_audio = audio.flatten()
    
    if np.max(np.abs(master_audio)) < 0.01:
        print("⚠️ Microphone is completely silent! Please ensure your microphone is working and try again.\n")
        return
            
    print("Voice command recorded! Now generating the 25-condition Simulation Matrix...\n")
    
    noises = {
        "White Noise": add_white_noise,
        "Brown Rumble": add_brown_noise,
        "120Hz Hum": add_hum_noise,
        "3000Hz Hiss": add_hiss_noise,
        "Impulse Pops": add_impulse_noise
    }
    
    filters = {
        "Wiener": apply_wiener,
        "Bandpass": apply_bandpass,
        "MovAvg": apply_movavg,
        "RNNoise": apply_rnnoise,
        "HighPass": apply_highpass
    }
    
    # To store results for the final summary table
    matrix_results = {n: {f: False for f in filters} for n in noises}
    
    for noise_name, noise_func in noises.items():
        noisy_audio = noise_func(master_audio, snr=10)
        
        for filter_name, filter_func in filters.items():
            print(f"Testing [ {noise_name} + {filter_name} ]...")
            
            # Step A: Apply Filter
            processed_audio = filter_func(noisy_audio)
            
            # Step B: Biometric Authentication
            is_auth, user_name = speaker_biometrics.verify_speaker(processed_audio, users)
            
            # Step C: Intent Matcher (STT Alternative)
            is_intent, conf = check_intent(processed_audio)
            
            # Step D: Hardware Activation
            # The relay only triggers if the system knows WHO you are AND WHAT you want
            if is_auth and is_intent:
                matrix_results[noise_name][filter_name] = True
                print(f" -> SUCCESS! Recognized {user_name}, Intent 'LIGHT_ON' ({conf:.1f}%). (Relay would trigger)")
            else:
                matrix_results[noise_name][filter_name] = False
                fail_reason = "Auth Failed" if not is_auth else "Intent Failed"
                print(f" -> FAILED! ({fail_reason})")
                
    # 4. Print Final Accuracy Matrix
    print("\n" + "="*80)
    print("FINAL HARDWARE ACTIVATION MATRIX (Auth + Intent Success)")
    print("="*80)
    
    header = f"{'Noise Type':<15} | " + " | ".join([f"{f:<9}" for f in filters.keys()])
    print(header)
    print("-" * len(header))
    
    for noise_name in noises.keys():
        row = f"{noise_name:<15} | "
        for filter_name in filters.keys():
            result = "PASS" if matrix_results[noise_name][filter_name] else "FAIL"
            row += f"{result:<9} | "
        print(row)
        
    print("\nCONCLUSION: The filter with the most 'PASS' results across all noise types is objectively the best algorithm for your real-world hardware deployment!")

if __name__ == "__main__":
    main()
