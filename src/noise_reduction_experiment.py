import os
import matplotlib.pyplot as plt
import numpy as np
import librosa
import scipy.signal as signal
import noisereduce as nr
import sounddevice as sd
import warnings

warnings.filterwarnings('ignore')

# --- Configuration ---
SAMPLE_RATE = 16000
SNR_TARGETS = [20, 10, 5]  # Three levels of noise
RECORD_DURATION = 3.0 # seconds

# --- 1. Noise Generation Functions ---
def add_white_noise(clean, snr):
    noise = np.random.normal(0, 1, len(clean))
    return mix_noise(clean, noise, snr)

def add_brown_noise(clean, snr):
    white = np.random.normal(0, 1, len(clean))
    noise = np.cumsum(white)
    noise = noise - np.mean(noise)
    return mix_noise(clean, noise, snr)

def add_hum_noise(clean, snr, freq=120):
    t = np.arange(len(clean)) / SAMPLE_RATE
    noise = np.sin(2 * np.pi * freq * t)
    return mix_noise(clean, noise, snr)

def add_hiss_noise(clean, snr, freq=3000):
    t = np.arange(len(clean)) / SAMPLE_RATE
    noise = np.sin(2 * np.pi * freq * t)
    return mix_noise(clean, noise, snr)

def add_impulse_noise(clean, snr):
    noise = np.zeros(len(clean))
    num_impulses = int(len(clean) * 0.005) 
    indices = np.random.choice(len(clean), num_impulses, replace=False)
    noise[indices] = np.random.choice([-1, 1], num_impulses)
    return mix_noise(clean, noise, snr)

def mix_noise(clean, noise, snr):
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0:
        return clean, noise
    k = np.sqrt(signal_power / (10**(snr/10) * noise_power))
    scaled_noise = noise * k
    return clean + scaled_noise, scaled_noise

# --- 2. Noise Reduction Techniques ---
def apply_wiener_filter(audio):
    return signal.wiener(audio, mysize=29)

def apply_bandpass_filter(audio, lowcut=300, highcut=3400):
    nyq = 0.5 * SAMPLE_RATE
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(5, [low, high], btype='band')
    return signal.filtfilt(b, a, audio)

def apply_moving_average(audio, window_size=5):
    window = np.ones(window_size) / window_size
    return np.convolve(audio, window, mode='same')

def apply_spectral_subtraction(audio):
    # Using noisereduce (RNNoise-like spectral gating)
    # Using non-stationary to better adapt to varying noise
    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=False)

def apply_highpass_filter(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(5, normal_cutoff, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

# --- 3. Evaluation Metric ---
def calculate_snr(clean, processed):
    signal_power = np.sum(clean**2)
    noise_power = np.sum((processed - clean)**2)
    if noise_power == 0:
        return float('inf')
    return 10 * np.log10(signal_power / noise_power)

# --- Main Experiment ---
def main():
    print("="*80)
    print("ADVANCED NOISE REDUCTION EXPERIMENT (LIVE 75 CONDITIONS)")
    print("="*80)
    
    input(f"\nPress Enter to record a {RECORD_DURATION}s live sample for the experiment...")
    print("Recording in 3... 2... 1...")
    audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    clean_audio = audio.flatten()
    
    # Simple silence check (Lowered threshold for quieter microphones)
    if np.max(np.abs(clean_audio)) < 0.005:
        print("Audio too silent. Please restart the script and try again.")
        return
        
    print("Live sample recorded successfully!\n")
    
    noises = {
        "White Noise": add_white_noise,
        "Brown Rumble": add_brown_noise,
        "120Hz Hum": add_hum_noise,
        "3000Hz Hiss": add_hiss_noise,
        "Impulse Pops": add_impulse_noise
    }
    
    techniques = {
        "Wiener": apply_wiener_filter,
        "Bandpass": apply_bandpass_filter,
        "MovAvg": apply_moving_average,
        "DeepFilter(RNNoise)": apply_spectral_subtraction,
        "HighPass": apply_highpass_filter
    }
    
    print("Processing 75 Conditions (5 Noises x 3 SNRs x 5 Techniques) on live audio...")
    
    # Store results: results[snr][noise][tech] = average_improvement
    results = {snr: {noise: {tech: [] for tech in techniques} for noise in noises} for snr in SNR_TARGETS}
    
    try:
        for snr in SNR_TARGETS:
            for noise_name, noise_func in noises.items():
                noisy_audio, _ = noise_func(clean_audio, snr)
                initial_snr = calculate_snr(clean_audio, noisy_audio)
                
                for tech_name, tech_func in techniques.items():
                    processed_audio = tech_func(noisy_audio)
                    final_snr = calculate_snr(clean_audio, processed_audio)
                    improvement = final_snr - initial_snr
                    
                    results[snr][noise_name][tech_name].append(improvement)
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        return
            
    print("\n" + "="*80)
    print("RESULTS (SNR IMPROVEMENT in dB)")
    print("="*80)
    
    header = f"{'SNR':<5} | {'Noise Type':<15} | " + " | ".join([f"{t[:15]:<15}" for t in techniques.keys()])
    print(header)
    print("-" * len(header))
    
    overall_best = {}
    
    for snr in SNR_TARGETS:
        for noise_name in noises.keys():
            row_str = f"{str(snr)+'dB':<5} | {noise_name:<15} | "
            for tech_name in techniques.keys():
                avg_imp = np.mean(results[snr][noise_name][tech_name])
                row_str += f"{avg_imp:>15.2f} | "
                
                # track for overall best
                if tech_name not in overall_best:
                    overall_best[tech_name] = []
                overall_best[tech_name].append(avg_imp)
                
            print(row_str)
        print("-" * len(header))

    print("\n" + "="*80)
    print("OVERALL TECHNIQUE PERFORMANCE (Average across all 15 conditions):")
    
    techs = []
    avg_scores = []
    
    for tech_name, scores in overall_best.items():
        avg_score = np.mean(scores)
        techs.append(tech_name)
        avg_scores.append(avg_score)
        print(f"[{tech_name}]: {avg_score:.2f} dB")
        
    # Generate Graph
    output_dir = "Report_Graphs"
    os.makedirs(output_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(techs, avg_scores, color='#17becf', edgecolor='black')

    ax.set_ylabel('Average SNR Improvement (dB)', fontsize=12, fontweight='bold')
    ax.set_title('Overall Noise Reduction Performance (Live Audio)', fontsize=14, fontweight='bold')
    plt.xticks(rotation=15, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'+{yval:.2f}dB', va='bottom', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    filepath = os.path.join(output_dir, 'live_snr_improvement.png')
    plt.savefig(filepath, dpi=300)
    print(f"\n📊 Graph saved to: {filepath}")
    plt.close()

if __name__ == "__main__":
    main()
