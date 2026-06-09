import os
import time
import numpy as np
import matplotlib.pyplot as plt
import sounddevice as sd
import noisereduce as nr
import librosa
import librosa.display

# Config
SAMPLE_RATE = 16000
DURATION = 3.0
OUTPUT_DIR = "Report_Graphs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def mix_noise(clean, noise, snr_target=10):
    """Mixes noise into a clean signal at a specific Signal-to-Noise Ratio (SNR)."""
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0:
        return clean
    k = np.sqrt(signal_power / (10**(snr_target/10) * noise_power))
    return clean + (noise * k)

def add_household_noise(clean_audio):
    """Generates synthetic household AC hum / fan noise + some white noise."""
    t = np.arange(len(clean_audio)) / SAMPLE_RATE
    # 120Hz AC Hum + general static
    hum = np.sin(2 * np.pi * 120 * t) 
    static = np.random.normal(0, 1, len(clean_audio))
    combined_noise = hum + (static * 0.5)
    
    return mix_noise(clean_audio, combined_noise, snr_target=5)

def main():
    print("\n" + "="*70)
    print("📈 NOISE REDUCTION WAVEFORM VISUALIZER FOR REPORT 📈")
    print("="*70)
    print("This will record your voice, inject heavy background noise,")
    print("and use Advanced Spectral Gating to clean it. It will then generate")
    print("a professional waveform graph comparing all 3 stages!")
    print("-" * 70)
    
    input("Press Enter to start recording for 3 seconds. Speak a command!...")
    print("🎤 Recording in 3... 2... 1...")
    
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    clean_voice = audio.flatten()
    
    if np.max(np.abs(clean_voice)) < 0.005:
        print("⚠️ Audio too silent. Please run again and speak louder.")
        return
        
    print("✅ Recording complete.")
    
    # 1. Add Heavy Noise
    print("🌪️ Injecting heavy household noise...")
    noisy_voice = add_household_noise(clean_voice)
    
    # 2. Apply Noise Reduction
    print("🧹 Applying Advanced Spectral Gating (noisereduce)...")
    cleaned_voice = nr.reduce_noise(y=noisy_voice, sr=SAMPLE_RATE, stationary=False)
    
    # 3. Plotting the results
    print("📊 Generating professional waveform graph...")
    
    plt.figure(figsize=(12, 8))
    plt.suptitle("Advanced Spectral Gating: Noise Reduction Analysis", fontsize=16, fontweight='bold')
    
    # Subplot 1: Clean Voice
    plt.subplot(3, 1, 1)
    librosa.display.waveshow(clean_voice, sr=SAMPLE_RATE, color='#2ca02c')
    plt.title("1. Original Clean Voice (Ground Truth)", fontsize=12, fontweight='bold')
    plt.ylabel("Amplitude")
    plt.ylim([-1.0, 1.0])
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Subplot 2: Noisy Voice
    plt.subplot(3, 1, 2)
    librosa.display.waveshow(noisy_voice, sr=SAMPLE_RATE, color='#d62728')
    plt.title("2. Corrupted Voice (Heavy Background Noise Added, 5dB SNR)", fontsize=12, fontweight='bold')
    plt.ylabel("Amplitude")
    plt.ylim([-1.0, 1.0])
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Subplot 3: Cleaned Voice
    plt.subplot(3, 1, 3)
    librosa.display.waveshow(cleaned_voice, sr=SAMPLE_RATE, color='#1f77b4')
    plt.title("3. Recovered Voice (After Advanced Spectral Gating)", fontsize=12, fontweight='bold')
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Amplitude")
    plt.ylim([-1.0, 1.0])
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    filepath = os.path.join(OUTPUT_DIR, 'waveform_noise_reduction_analysis.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n🎉 Success! The professional graph has been saved to: {filepath}")

if __name__ == "__main__":
    main()
