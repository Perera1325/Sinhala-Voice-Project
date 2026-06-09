import sys
import os
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import warnings

warnings.filterwarnings('ignore')

# Import the 6 analytical filters you built in NoiseRM
sys.path.append(os.path.join(os.path.dirname(__file__), 'NoiseRM'))
import audio_filters as af

SAMPLE_RATE = 16000
RECORD_DURATION = 3.0
NOISE_SNR = 5 # dB (High noise environment)

def add_white_noise(clean, snr=5):
    noise = np.random.normal(0, 1, len(clean))
    signal_power = np.mean(clean**2)
    noise_power = np.mean(noise**2)
    if noise_power == 0: return clean
    k = np.sqrt(signal_power / (10**(snr/10) * noise_power))
    return clean + (noise * k)

def recognize_audio(audio_data):
    recognizer = sr.Recognizer()
    audio_data = audio_data / np.max(np.abs(audio_data))
    audio_int16 = np.int16(audio_data * 32767)
    audio_obj = sr.AudioData(audio_int16.tobytes(), SAMPLE_RATE, 2)
    try:
        text = recognizer.recognize_google(audio_obj, language="si-LK")
        return "PASS", text
    except sr.UnknownValueError:
        return "FAIL", "(Rejected due to Noise)"
    except sr.RequestError:
        return "ERROR", "API Connectivity Error"

def main():
    print("="*80)
    print("🚀 LIVE NOISE REDUCTION BENCHMARKING SYSTEM 🚀")
    print("="*80)
    print("This script will record your voice, deliberately inject loud background noise,")
    print("and run it through all 5 baseline methods + your custom VGDWF method to")
    print("compare their live accuracy in real-time!")
    
    while True:
        try:
            input(f"\nPress Enter to record a {RECORD_DURATION}s voice command (or Ctrl+C to quit)...")
            print("🎙️ Recording in 3... 2... 1... SPEAK NOW!")
            
            audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            clean = audio.flatten()
            
            if np.max(np.abs(clean)) < 0.01:
                print("⚠️ Audio too quiet. Please speak louder next time.")
                continue
                
            print("✅ Recording complete. Injecting 5dB White Noise...")
            noisy = add_white_noise(clean, snr=NOISE_SNR)
            
            print("⚙️ Processing through 6 analytical filters (This may take a few seconds)...")
            
            # Apply all 6 filters from your audio_filters.py
            start = time.time()
            y1 = af.spectral_subtraction(noisy, SAMPLE_RATE)
            y2 = af.wiener_filter(noisy, SAMPLE_RATE)
            y3 = af.wavelet_denoising(noisy)
            y4 = af.spectral_gating(noisy, SAMPLE_RATE)
            y5 = af.bandpass_filter(noisy, SAMPLE_RATE)
            y6 = af.vad_guided_dynamic_wiener_filter(noisy, SAMPLE_RATE)
            print(f"⏱️ Filtering completed in {time.time()-start:.2f} seconds.")
            
            print("☁️ Evaluating accuracy via Google STT engine...")
            
            results = [
                ["1. Clean Audio (Baseline)", *recognize_audio(clean)],
                ["2. Noisy Audio (5dB)", *recognize_audio(noisy)],
                ["3. Spectral Subtraction", *recognize_audio(y1)],
                ["4. Static Wiener Filter", *recognize_audio(y2)],
                ["5. Wavelet Denoising", *recognize_audio(y3)],
                ["6. Spectral Gating", *recognize_audio(y4)],
                ["7. Butterworth Bandpass", *recognize_audio(y5)],
                ["8. Custom Method (VGDWF)", *recognize_audio(y6)]
            ]
            
            print("\n" + "="*80)
            print("📊 LIVE ACCURACY COMPARISON TABLE")
            print("="*80)
            
            print(f"{'Method'.ljust(30)} | {'Status'.ljust(6)} | {'Transcribed Text'}")
            print("-" * 80)
            for row in results:
                method, res, text = row
                if "Custom" in method:
                    print(f"🌟 {method.ljust(27)} | {res.ljust(6)} | {text}")
                else:
                    print(f"{method.ljust(30)} | {res.ljust(6)} | {text}")
            print("="*80)
            
        except KeyboardInterrupt:
            print("\nExiting Benchmarking System...")
            sys.exit(0)
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
