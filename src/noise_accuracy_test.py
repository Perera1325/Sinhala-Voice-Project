import os
import matplotlib.pyplot as plt
import numpy as np
import librosa
import scipy.signal as signal
import noisereduce as nr
import speech_recognition as sr
import sounddevice as sd
import warnings

warnings.filterwarnings('ignore')

# --- Configuration ---
SAMPLE_RATE = 16000
NOISE_SNR = 10 # dB
RECORD_DURATION = 3.0 # seconds

# --- Noise and Filter Functions ---
def add_white_noise(clean, snr=10):
    noise = np.random.normal(0, 1, len(clean))
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0: return clean
    k = np.sqrt(signal_power / (10**(snr/10) * noise_power))
    return clean + (noise * k)

def apply_bandpass_filter(audio, lowcut=300, highcut=3400):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, [lowcut/nyq, highcut/nyq], btype='band')
    return signal.filtfilt(b, a, audio)

def apply_spectral_subtraction(audio):
    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=False)

def apply_highpass_filter(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

# --- Speech Recognition Function ---
recognizer = sr.Recognizer()

def recognize_audio(audio_data):
    """Returns True if Google STT successfully transcribes ANY Sinhala text, False otherwise"""
    # Normalize and convert to 16-bit PCM bytes required by speech_recognition
    audio_data = audio_data / np.max(np.abs(audio_data))
    audio_int16 = np.int16(audio_data * 32767)
    
    # Create AudioData object (1 channel, 2 bytes width = 16 bit)
    audio_obj = sr.AudioData(audio_int16.tobytes(), SAMPLE_RATE, 2)
    
    try:
        # We don't care what the text is for this test, just that it wasn't rejected as noise
        _ = recognizer.recognize_google(audio_obj, language="si-LK")
        return True
    except sr.UnknownValueError:
        return False
    except sr.RequestError:
        return False

# --- Main Experiment ---
def main():
    print("="*70)
    print("LIVE SPEECH-TO-TEXT ACCURACY COMPARISON EXPERIMENT")
    print("="*70)
    
    results = {
        "Clean Audio": 0,
        "Noisy (10dB White Noise)": 0,
        "Bandpass Filtered": 0,
        "Spectral Gated (RNNoise)": 0,
        "High-Pass Filtered": 0
    }
    
    num_tests = 0
    
    while True:
        try:
            choice = input(f"\nPress Enter to record a {RECORD_DURATION}s live sample (or type 'q' to quit and see results): ")
            if choice.lower() == 'q':
                break
                
            print("Recording in 3... 2... 1...")
            audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            clean = audio.flatten()
            
            # Ensure user actually spoke
            if np.max(np.abs(clean)) < 0.005:
                print("⚠️ Audio too silent. Please speak louder next time.")
                continue
                
            num_tests += 1
            print(f"Processing Live Sample #{num_tests}...")
            
            # Generate states
            noisy = add_white_noise(clean, snr=NOISE_SNR)
            bandpass = apply_bandpass_filter(noisy)
            gated = apply_spectral_subtraction(noisy)
            highpass = apply_highpass_filter(noisy)
            
            # Test States
            if recognize_audio(clean): results["Clean Audio"] += 1
            if recognize_audio(noisy): results["Noisy (10dB White Noise)"] += 1
            if recognize_audio(bandpass): results["Bandpass Filtered"] += 1
            if recognize_audio(gated): results["Spectral Gated (RNNoise)"] += 1
            if recognize_audio(highpass): results["High-Pass Filtered"] += 1
            
            print("Completed testing this sample.")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error processing audio: {e}")
            continue
            
    if num_tests == 0:
        print("No samples recorded. Exiting.")
        return
        
    print("\n" + "="*70)
    print(f"FINAL STT RECOGNITION ACCURACY (Over {num_tests} Live Samples)")
    print("="*70)
    
    conditions = []
    accuracies = []
    
    for condition, success_count in results.items():
        accuracy = (success_count / num_tests) * 100
        conditions.append(condition)
        accuracies.append(accuracy)
        print(f"{condition:<30} : {accuracy:>6.1f}%")

    # Generate Graph
    output_dir = "Report_Graphs"
    os.makedirs(output_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(conditions, accuracies, color=['#2ca02c', '#d62728', '#ff7f0e', '#ff7f0e', '#ff7f0e'], edgecolor='black')

    ax.set_ylabel('Recognition Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Live Google STT Performance Degradation (Over {num_tests} Samples)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 115)
    plt.xticks(rotation=15, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.1f}%', va='bottom', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    filepath = os.path.join(output_dir, 'live_stt_degradation.png')
    plt.savefig(filepath, dpi=300)
    print(f"\n📊 Graph saved to: {filepath}")
    plt.close()

if __name__ == "__main__":
    main()
