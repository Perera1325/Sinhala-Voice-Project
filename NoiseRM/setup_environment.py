# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: setup_environment.py
# Description: Checks and installs requirements, downloads and extracts the offline 
#              ASR Vosk model, and pre-generates the system's voice notification prompts.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

import os
import sys
import subprocess
import zipfile
import urllib.request
import shutil

# Target directory
TARGET_DIR = r"C:\Users\Kasundi\Downloads\NoiseRM"
os.makedirs(TARGET_DIR, exist_ok=True)

# List of required packages
REQUIRED_PACKAGES = [
    "numpy",
    "scipy",
    "sounddevice",
    "soundfile",
    "speechbrain",
    "gtts",
    "paho-mqtt",
    "google-cloud-speech",
    "vosk",
    "pywavelets",
    "torch",
    "torchaudio",
    "pyttsx3",
    "flask"
]

def install_packages():
    """Checks and installs required Python packages."""
    print("=== Step 1: Checking and Installing Dependencies ===")
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
            print(f"[OK] Package '{package}' is already installed.")
        except ImportError:
            print(f"[INFO] Package '{package}' not found. Installing...")
            try:
                # Install package via pip
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"[OK] Successfully installed '{package}'.")
            except Exception as e:
                print(f"[ERROR] Failed to install '{package}': {e}")

def download_vosk_model():
    """Downloads and extracts the Vosk small model for offline ASR."""
    print("\n=== Step 2: Setting up Offline ASR Vosk Model ===")
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    zip_path = os.path.join(TARGET_DIR, "vosk-model.zip")
    extracted_folder_path = os.path.join(TARGET_DIR, "vosk-model-small-en-us-0.15")
    final_model_path = os.path.join(TARGET_DIR, "vosk-model")

    if os.path.exists(final_model_path):
        print(f"[OK] Vosk model is already setup at: {final_model_path}")
        return

    print("Downloading Vosk model (approx 40MB). Please wait...")
    try:
        # Download with progress log
        urllib.request.urlretrieve(model_url, zip_path)
        print("[OK] Download completed. Extracting zip archive...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(TARGET_DIR)
            
        print("[OK] Extraction complete. Renaming directory to 'vosk-model'...")
        if os.path.exists(extracted_folder_path):
            os.rename(extracted_folder_path, final_model_path)
            
        # Clean up zip file
        os.remove(zip_path)
        print("[OK] Vosk model setup successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to setup Vosk model: {e}")

def generate_voice_notifications():
    """Generates offline notification WAV audio files using pyttsx3 or native Windows fallback."""
    print("\n=== Step 3: Generating Voice Notifications (TTS) ===")
    notifications = {
        "user_registered.wav": "User Registered",
        "user_recognised.wav": "Uthorized",
        "user_unrecognised.wav": "Not utharorized"
    }
    
    # Prioritize Windows native PowerShell speech synthesizer on Windows platform
    if sys.platform == "win32":
        print("[INFO] Windows platform detected. Using native PowerShell System.Speech Synthesizer...")
        for filename, text in notifications.items():
            filepath = os.path.join(TARGET_DIR, filename)
            print(f"Generating voice file: {filename} (using PowerShell)")
            try:
                ps_script = f"""
                Add-Type -AssemblyName System.Speech;
                $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer;
                $speak.SetOutputToWaveFile('{filepath}');
                $speak.Speak('{text}');
                $speak.Dispose();
                """
                # Run PowerShell command
                subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
                print(f"[OK] Saved voice notification to '{filepath}'")
            except Exception as ps_error:
                print(f"[ERROR] PowerShell TTS generation failed: {ps_error}")
        return
        
    # Try using pyttsx3 first on other platforms
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        
        for filename, text in notifications.items():
            filepath = os.path.join(TARGET_DIR, filename)
            
            print(f"Generating voice file: {filename} (using pyttsx3)")
            engine.save_to_file(text, filepath)
            engine.runAndWait()
            print(f"[OK] Saved voice notification to '{filepath}'")
        return
    except Exception as pyttsx3_error:
        print(f"[ERROR] pyttsx3 failed: {pyttsx3_error}")
        print("[ERROR] No voice generation fallback available for this platform. Please install 'espeak' or setup pyttsx3.")

if __name__ == "__main__":
    # install_packages()
    # download_vosk_model()
    generate_voice_notifications()
            
    print("\n=== Environment Setup Complete ===")
