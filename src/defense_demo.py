import os
import numpy as np
import librosa
import scipy.signal as signal
from scipy.io import wavfile
import noisereduce as nr
import warnings

warnings.filterwarnings('ignore')

# --- Configuration ---
SAMPLE_RATE = 16000
DEMO_DIR = "Demo_Audio"

# --- Noise and Filter Functions (From our experiment) ---
def add_hum_noise(clean, snr=10, freq=120):
    t = np.arange(len(clean)) / SAMPLE_RATE
    noise = np.sin(2 * np.pi * freq * t)
    
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0: return clean
    
    k = np.sqrt(signal_power / (10**(snr/10) * noise_power))
    scaled_noise = noise * k
    return clean + scaled_noise

def apply_wiener_filter(audio):
    return signal.wiener(audio, mysize=29)

def apply_bandpass_filter(audio, lowcut=300, highcut=3400):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, [lowcut/nyq, highcut/nyq], btype='band')
    return signal.filtfilt(b, a, audio)

def apply_moving_average(audio, window_size=5):
    window = np.ones(window_size) / window_size
    return np.convolve(audio, window, mode='same')

def apply_spectral_subtraction(audio):
    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=False)

def apply_highpass_filter(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

def save_audio(filename, audio_data):
    # Normalize to prevent clipping, then convert to 16-bit PCM
    audio_data = audio_data / np.max(np.abs(audio_data))
    audio_int16 = np.int16(audio_data * 32767)
    wavfile.write(os.path.join(DEMO_DIR, filename), SAMPLE_RATE, audio_int16)
    print(f"Saved: {filename}")

def main():
    print("="*60)
    print("GENERATING PROJECT DEFENSE DEMONSTRATION AUDIO")
    print("="*60)
    
    os.makedirs(DEMO_DIR, exist_ok=True)
    
    # Try to load a known good file
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_file = os.path.join(parent_dir, "test.wav")
    
    if not os.path.exists(test_file):
        print("Please place a 'test.wav' file in the main project folder.")
        return
        
    print("1. Loading Clean Audio...")
    clean_audio, _ = librosa.load(test_file, sr=SAMPLE_RATE, mono=True)
    clean_audio, _ = librosa.effects.trim(clean_audio, top_db=30)
    
    save_audio("1_clean_voice.wav", clean_audio)
    
    print("\n2. Adding 10dB of 120Hz Fan Hum...")
    noisy_audio = add_hum_noise(clean_audio, snr=10)
    save_audio("2_noisy_voice.wav", noisy_audio)
    
    print("\n3. Applying Noise Reduction Techniques...")
    save_audio("3_filtered_wiener.wav", apply_wiener_filter(noisy_audio))
    save_audio("4_filtered_bandpass.wav", apply_bandpass_filter(noisy_audio))
    save_audio("5_filtered_movavg.wav", apply_moving_average(noisy_audio))
    save_audio("6_filtered_rnnoise_proxy.wav", apply_spectral_subtraction(noisy_audio))
    save_audio("7_filtered_highpass.wav", apply_highpass_filter(noisy_audio))
    
    print("\n" + "="*60)
    print(f"Success! You can play these files directly from the '{DEMO_DIR}' folder during your defense.")
    print("="*60)

if __name__ == "__main__":
    main()
