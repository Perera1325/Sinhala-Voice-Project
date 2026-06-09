import os
import sys
import time
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix
import speech_recognition as sr
import scipy.signal as signal
from deep_translator import GoogleTranslator

import nlp_classifier

# Config
SAMPLE_RATE = 16000
RECORD_DURATION = 4.0
OUTPUT_DIR = "Report_Graphs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def apply_highpass_filter(audio, cutoff=150):
    nyq = 0.5 * SAMPLE_RATE
    b, a = signal.butter(5, cutoff/nyq, btype='high', analog=False)
    return signal.filtfilt(b, a, audio)

def main():
    print("\n" + "="*60)
    print("📊 LIVE SYSTEM METRICS GENERATOR FOR YOUR REPORT 📊")
    print("="*60)
    print("This script will record your live voice commands and automatically")
    print("generate the Accuracy Graphs, Predicted vs Actual Analysis, and")
    print("Correlation Heatmaps based purely on your real-time performance!")
    print("-"*60)
    
    try:
        num_tests = int(input("How many live tests do you want to run? (e.g., 5): "))
    except ValueError:
        print("Invalid number. Running 3 tests by default.")
        num_tests = 3

    recognizer = sr.Recognizer()
    
    actual_labels = []
    predicted_labels = []
    
    # Run the interactive tests
    for i in range(num_tests):
        print(f"\n--- TEST {i+1} of {num_tests} ---")
        
        # Ask what the user intends to do
        print("What will you do in this test?")
        print("1. Say 'Light eka danna' (Intended Action: Turn ON Light)")
        print("2. Say random noise or silence (Intended Action: None)")
        choice = input("Enter 1 or 2: ")
        
        expected_action = "light_on" if choice == "1" else "none"
        actual_labels.append(expected_action)
        
        print("\n🎤 Recording for 4 seconds... Speak now!")
        audio = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        
        print("🧹 Applying High-Pass Noise Reduction...")
        clean_audio = apply_highpass_filter(audio.flatten())
        
        print("🧠 Analyzing intent with AI...")
        
        audio_data_int16 = (clean_audio * 32767).astype(np.int16)
        audio_data_obj = sr.AudioData(audio_data_int16.tobytes(), SAMPLE_RATE, 2)
        
        predicted_action = "none"
        try:
            transcription = recognizer.recognize_google(audio_data_obj, language="si-LK")
            print(f"🗣️ Detected Sinhala: '{transcription}'")
            device_id, action = nlp_classifier.classify_command(transcription)
            
            if device_id == "light_1" and action == "ON":
                predicted_action = "light_on"
            else:
                predicted_action = "none"
        except sr.UnknownValueError:
            print("❓ Silence/Noise detected.")
            predicted_action = "none"
        except sr.RequestError:
            print("❌ STT Error.")
            predicted_action = "none"
            
        predicted_labels.append(predicted_action)
        
        if expected_action == predicted_action:
            print("✅ Result: CORRECT MATCH")
        else:
            print("❌ Result: MISMATCH")
            
        time.sleep(1)

    # Generate the requested graphs!
    print("\n" + "="*60)
    print("📈 GENERATING REPORT GRAPHS 📈")
    
    # 1. Calculate Accuracy
    correct = sum(1 for a, p in zip(actual_labels, predicted_labels) if a == p)
    accuracy_percent = (correct / num_tests) * 100
    
    print(f"System Accuracy: {accuracy_percent:.1f}%")
    
    # 2. Predicted vs Actual Analysis Table
    print("\n--- Predicted vs Actual Results ---")
    print(f"{'Test #':<10} | {'Actual Intention':<20} | {'System Prediction':<20}")
    print("-" * 55)
    for i, (act, pred) in enumerate(zip(actual_labels, predicted_labels)):
        print(f"Test {i+1:<4} | {act:<20} | {pred:<20}")
        
    # 3. Model Accuracy Graph
    fig, ax = plt.subplots(figsize=(6, 5))
    categories = ['Correct', 'Incorrect']
    counts = [correct, num_tests - correct]
    
    bars = ax.bar(categories, counts, color=['#2ca02c', '#d62728'], edgecolor='black')
    ax.set_ylabel('Number of Live Tests', fontsize=12, fontweight='bold')
    ax.set_title(f'Live System Accuracy ({accuracy_percent:.1f}%)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, num_tests + 1)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f'{int(yval)}', va='bottom', ha='center', fontsize=12, fontweight='bold')
        
    acc_path = os.path.join(OUTPUT_DIR, 'live_system_accuracy.png')
    plt.savefig(acc_path, dpi=300)
    plt.close()
    print(f"\n📊 Saved Accuracy Graph -> {acc_path}")
    
    # 4. Correlation Heatmap (Confusion Matrix)
    labels = ["none", "light_on"]
    display_labels = ["Noise/Unknown", "Light ON Command"]
    
    cm = confusion_matrix(actual_labels, predicted_labels, labels=labels)
    
    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=display_labels, yticklabels=display_labels, annot_kws={"size": 16})
    plt.title('Predicted vs Actual Correlation Heatmap', fontsize=14, fontweight='bold')
    plt.ylabel('Actual User Intention', fontsize=12, fontweight='bold')
    plt.xlabel('System Prediction', fontsize=12, fontweight='bold')
    
    cm_path = os.path.join(OUTPUT_DIR, 'live_correlation_heatmap.png')
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"📊 Saved Correlation Heatmap (Confusion Matrix) -> {cm_path}")
    
    print("\n✅ All report graphs have been successfully generated based on your live commands!")
    print("You can find them in the 'Report_Graphs' folder.")

if __name__ == "__main__":
    main()
