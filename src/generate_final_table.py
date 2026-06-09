import os
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import librosa
import scipy.signal as signal
import noisereduce as nr
import speech_recognition as sr
import sounddevice as sd
import warnings

warnings.filterwarnings('ignore')

# --- Configuration ---
SAMPLE_RATE = 16000
NOISE_SNR = 10
CONFIDENCE_THRESHOLD = 75.0
RECORD_DURATION = 3.0

# --- Noise & Filters ---
def add_white_noise(clean, snr=10):
    noise = np.random.normal(0, 1, len(clean))
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0: return clean
    k = np.sqrt(signal_power / (10**(snr/10) * noise_power))
    return clean + (noise * k)

def apply_wiener(audio): return signal.wiener(audio, mysize=29)

def apply_bandpass(audio, lowcut=300, highcut=3400):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, [lowcut/nyq, highcut/nyq], btype='band')
    return signal.filtfilt(b, a, audio)

def apply_rnnoise(audio):
    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=False)

def apply_highpass(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

# --- STT & AI Models ---
recognizer = sr.Recognizer()

def get_stt_success(audio_data):
    audio_data = audio_data / np.max(np.abs(audio_data))
    audio_int16 = np.int16(audio_data * 32767)
    audio_obj = sr.AudioData(audio_int16.tobytes(), SAMPLE_RATE, 2)
    try:
        recognizer.recognize_google(audio_obj, language="si-LK")
        return True
    except:
        return False

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(parent_dir, "Deploy_To_RaspberryPi", "light_model.tflite")
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def get_intent_success(audio):
    audio_data = np.asarray(audio, dtype=np.float32).flatten()
    mfcc = librosa.feature.mfcc(y=audio_data, sr=SAMPLE_RATE, n_mfcc=40)
    mfcc = mfcc[:, :44]
    if mfcc.shape[1] < 44:
        pad_width = 44 - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    mfcc = mfcc.reshape(1, 40, 44, 1).astype(np.float32)
    
    interpreter.set_tensor(input_details[0]['index'], mfcc)
    interpreter.invoke()
    prediction = interpreter.get_tensor(output_details[0]['index'])
    
    confidence = float(np.max(prediction)) * 100
    return confidence > CONFIDENCE_THRESHOLD

# --- Main Experiment ---
def main():
    print("="*80)
    print("LIVE FINAL THESIS CONTRIBUTION TABLE GENERATOR")
    print("="*80)
    
    methods = {
        "Wiener": apply_wiener,
        "Bandpass": apply_bandpass,
        "RNNoise": apply_rnnoise,
        "HighPass": apply_highpass
    }
    
    # metrics[method] = [stt_count, intent_count]
    metrics = {m: [0, 0] for m in methods.keys()}
    
    num_tests = 0
    
    while True:
        try:
            choice = input(f"\nPress Enter to record a {RECORD_DURATION}s live sample (or type 'q' to quit and generate table): ")
            if choice.lower() == 'q':
                break
                
            print("Recording in 3... 2... 1...")
            audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            clean = audio.flatten()
            
            # Simple silence check
            if np.max(np.abs(clean)) < 0.02:
                print("Audio too silent. Please try again.")
                continue
                
            num_tests += 1
            print(f"Processing Live Sample #{num_tests}...")
            
            noisy = add_white_noise(clean, snr=NOISE_SNR)
            
            for m_name, m_func in methods.items():
                filtered = m_func(noisy)
                if get_stt_success(filtered): metrics[m_name][0] += 1
                if get_intent_success(filtered): metrics[m_name][1] += 1
                
            print("Completed testing this sample.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error processing audio: {e}")
            continue

    if num_tests == 0:
        print("No samples recorded. Exiting.")
        return

    print("\n" + "="*80)
    print(f"FINAL PIPELINE METRICS (Over {num_tests} Live Samples)")
    print(f"{'Method':<15} | {'STT Accuracy':<15} | {'Intent Accuracy':<15} | {'Device Success Rate':<15}")
    print("-" * 70)
    
    stt_accuracies = []
    intent_accuracies = []
    method_names = list(methods.keys())
    
    for m_name in method_names:
        stt_acc = (metrics[m_name][0] / num_tests) * 100
        intent_acc = (metrics[m_name][1] / num_tests) * 100
        dev_acc = intent_acc
        
        stt_accuracies.append(stt_acc)
        intent_accuracies.append(intent_acc)
        
        print(f"{m_name:<15} | {stt_acc:>14.1f}% | {intent_acc:>14.1f}% | {dev_acc:>18.1f}%")

    # Generate Graph
    output_dir = "Report_Graphs"
    os.makedirs(output_dir, exist_ok=True)
    
    x = np.arange(len(method_names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, stt_accuracies, width, label='Google STT Accuracy', color='#1f77b4', edgecolor='black')
    rects2 = ax.bar(x + width/2, intent_accuracies, width, label='Hardware Activation Success', color='#2ca02c', edgecolor='black')

    ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Standard STT vs Localized Hardware AI (Over {num_tests} Live Samples)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(method_names, fontsize=11)
    ax.legend()
    ax.set_ylim(0, 115)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    for rects in [rects1, rects2]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    filepath = os.path.join(output_dir, 'live_stt_vs_hardware_accuracy.png')
    plt.savefig(filepath, dpi=300)
    print(f"\n📊 Graph saved to: {filepath}")
    plt.close()

if __name__ == "__main__":
    main()
