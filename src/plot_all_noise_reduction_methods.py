import os
import numpy as np
import matplotlib.pyplot as plt
import sounddevice as sd
import noisereduce as nr
import librosa
import librosa.display
import scipy.signal as signal

# Config
SAMPLE_RATE = 16000
DURATION = 3.0
OUTPUT_DIR = "Report_Graphs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# NOISE INJECTION
# ==========================================
def mix_noise(clean, noise, snr_target=10):
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0:
        return clean
    k = np.sqrt(signal_power / (10**(snr_target/10) * noise_power))
    return clean + (noise * k)

def add_household_noise(clean_audio):
    """Generates synthetic household AC hum + white noise at 5dB SNR."""
    t = np.arange(len(clean_audio)) / SAMPLE_RATE
    hum = np.sin(2 * np.pi * 120 * t) 
    static = np.random.normal(0, 1, len(clean_audio))
    return mix_noise(clean_audio, hum + (static * 0.5), snr_target=5)

# ==========================================
# 5 NOISE REDUCTION METHODS
# ==========================================
def apply_wiener_filter(audio):
    return signal.wiener(audio, mysize=29)

def apply_bandpass_filter(audio, lowcut=300, highcut=3400):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, [lowcut/nyq, highcut/nyq], btype='band')
    return signal.filtfilt(b, a, audio)

def apply_moving_average(audio, window_size=5):
    window = np.ones(window_size) / window_size
    return np.convolve(audio, window, mode='same')

def apply_spectral_gating(audio):
    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=False)

def apply_highpass_filter(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

# ==========================================
# PLOTTING FUNCTION
# ==========================================
def generate_graph(clean, noisy, cleaned, method_name, command_text):
    plt.figure(figsize=(12, 8))
    plt.suptitle(f"{method_name} Analysis | Command: '{command_text}'", fontsize=16, fontweight='bold')
    
    # Clean Voice
    plt.subplot(3, 1, 1)
    librosa.display.waveshow(clean, sr=SAMPLE_RATE, color='#2ca02c')
    plt.title("1. Original Clean Voice (Ground Truth)", fontsize=12, fontweight='bold')
    plt.ylabel("Amplitude")
    plt.ylim([-1.0, 1.0])
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Noisy Voice
    plt.subplot(3, 1, 2)
    librosa.display.waveshow(noisy, sr=SAMPLE_RATE, color='#d62728')
    plt.title("2. Corrupted Voice (Heavy Background Noise Added, 5dB SNR)", fontsize=12, fontweight='bold')
    plt.ylabel("Amplitude")
    plt.ylim([-1.0, 1.0])
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Cleaned Voice
    plt.subplot(3, 1, 3)
    librosa.display.waveshow(cleaned, sr=SAMPLE_RATE, color='#1f77b4')
    plt.title(f"3. Recovered Voice (After {method_name})", fontsize=12, fontweight='bold')
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Amplitude")
    plt.ylim([-1.0, 1.0])
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    filename = method_name.replace(" ", "_").lower() + "_analysis.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"📊 Saved: {filepath}")

# ==========================================
# MAIN ROUTINE
# ==========================================
def main():
    print("\n" + "="*70)
    print("📈 COMPREHENSIVE NOISE REDUCTION VISUALIZER 📈")
    print("="*70)
    
    command_text = input("What command will you speak? (e.g., 'Light eka danna'): ")
    
    input("Press Enter to start recording for 3 seconds...")
    print("🎤 Recording in 3... 2... 1...")
    
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    clean_voice = audio.flatten()
    
    if np.max(np.abs(clean_voice)) < 0.005:
        print("⚠️ Audio too silent. Please run again and speak louder.")
        return
        
    print("✅ Recording complete.")
    
    print("🌪️ Injecting heavy household noise...")
    noisy_voice = add_household_noise(clean_voice)
    
    techniques = {
        "Spectral Gating": apply_spectral_gating,
        "High-Pass Filter": apply_highpass_filter,
        "Band-Pass Filter": apply_bandpass_filter,
        "Wiener Filter": apply_wiener_filter,
        "Moving Average Smoothing": apply_moving_average
    }
    
    print("\nApplying all 5 methods and generating graphs...")
    for method_name, method_func in techniques.items():
        cleaned_voice = method_func(noisy_voice)
        generate_graph(clean_voice, noisy_voice, cleaned_voice, method_name, command_text)
        
    print("\n🎉 Success! All 5 graphs have been generated for your report.")

if __name__ == "__main__":
    main()
