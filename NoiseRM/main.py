# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: main.py
# Description: Main pipeline orchestrating speaker registration, wake word spotting,
#              speaker verification, 6-method noise reduction, online/offline ASR,
#              command parsing, and MQTT-based device control.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

import os
import sys
import time
import numpy as np

# Ensure UTF-8 console output for Windows to prevent charmap encoding errors when printing Sinhala script
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        # Fallback for older Python versions
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import sounddevice as sd
import soundfile as sf

# Import local modules
import audio_filters
import speaker_recognition
import offline_recognition
import online_recognition
import requests

# System settings
BASE_DIR = r"C:\Users\Kasundi\Downloads\NoiseRM"
USER_EMBEDDING_PATH = os.path.join(BASE_DIR, "user_embedding.npy")
REGISTRATION_AUDIO = os.path.join(BASE_DIR, "user_voice_ref.wav")

# Flask Server Config
FLASK_SERVER_IP = "192.168.1.74" # Set this to your RPI4 IP address if running main.py on a different PC
FLASK_SERVER_PORT = 5000
CHANNEL_LIGHT = "5508f5fc-3641-44cd-9cc5-87e5fc677483"
CHANNEL_FAN = "74136aa1-471d-485d-ac02-9c0bb408d9d3"  # Replace with actual Fan Channel ID if different

# Configurable Delay Times (in seconds)
DELAY_ON_REGISTRATION_START = 1.0          # Pause before recording the voice enrollment profile
DELAY_AFTER_WAKEWORD_RECOGNITION = 1.5     # Delay between saying the wake word and recording the command
DELAY_AFTER_UNREGISTERED_REJECTION = 1.0   # Cool-down delay after denying an unregistered voice print
DELAY_ON_WAKEWORD_RETRY = 0.5              # Sleep interval between consecutive wake word listening attempts

# Audio feedback WAV paths
SOUND_REG_SUCCESS = os.path.join(BASE_DIR, "user_registered.wav")
SOUND_USER_RECOGNIZED = os.path.join(BASE_DIR, "user_recognised.wav")
SOUND_USER_UNRECOGNIZED = os.path.join(BASE_DIR, "user_unrecognised.wav")

# Temporary recording file paths
TEMP_WAKEWORD_WAV = os.path.join(BASE_DIR, "temp_wakeword.wav")
TEMP_COMMAND_WAV = os.path.join(BASE_DIR, "temp_command.wav")

# ==============================================================================
# AUDIO PLAYBACK HELPER (OS-PORTABLE)
# ==============================================================================
def play_audio(file_path):
    """
    Plays a WAV file. Uses native Windows winsound for efficiency, 
    and falls back to standard shell players on Linux/Raspberry Pi.
    """
    if not os.path.exists(file_path):
        print(f"[WARNING] Audio feedback file not found: {file_path}")
        return
        
    print(f"[Audio Playback] Playing: {os.path.basename(file_path)}")
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(file_path, winsound.SND_FILENAME)
    else:
        # Raspberry Pi / Linux command fallback
        import subprocess
        subprocess.call(["aplay", file_path])

# ==============================================================================
# AUDIO RECORDING HELPER
# ==============================================================================
def record_audio(output_path, duration_seconds, sample_rate=16000):
    """
    Records mono audio from the default microphone and saves it as a 16-bit WAV file.
    Falls back to generating synthetic speech/dummy WAV if no audio device is available.
    """
    print(f"[Microphone] Recording for {duration_seconds} seconds... SPEAK NOW!")
    try:
        # Record at 16kHz mono (Standard for SpeechBrain and Vosk)
        recording = sd.rec(
            int(duration_seconds * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            dtype='float32'
        )
        # Block execution until recording finishes
        sd.wait()
        print("[Microphone] Recording stopped.")
        
        # Normalize audio levels (scale to peak at 0.9 to boost quiet signals)
        max_val = np.max(np.abs(recording))
        if max_val > 1e-4:
            recording = (recording / max_val) * 0.9
            print(f"[Microphone] Audio normalized (amplified by {0.9/max_val:.1f}x to peak at 0.9).")
        else:
            print("[WARNING] Recorded audio is completely silent. Normalization skipped.")
            
        # Save the recorded audio
        sf.write(output_path, recording, sample_rate)
        print(f"[Microphone] Audio saved to: {output_path}")
    except Exception as e:
        print(f"[WARNING] Microphone error: {e}")
        print("[INFO] Falling back to generating a simulated voice signal...")
        
        # Generate a synthetic wav file of speech using powershell/TTS
        # If it's registration audio, say 'Hay Kasu - Light eka danna'
        # If it's command audio, say 'Light eka danna'
        # If it's wakeword, say 'Hay Kasu'
        text_to_speak = "Hay Kasu"
        if "ref" in output_path or "registration" in output_path:
            text_to_speak = "Hay Kasu. Light eka danna."
        elif "command" in output_path:
            text_to_speak = "Light eka danna"
            
        success = False
        if sys.platform == "win32":
            try:
                import subprocess
                ps_script = f"""
                Add-Type -AssemblyName System.Speech;
                $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer;
                $speak.SetOutputToWaveFile('{output_path}');
                $speak.Speak('{text_to_speak}');
                $speak.Dispose();
                """
                subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
                success = True
            except Exception:
                pass
                
        if not success:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.save_to_file(text_to_speak, output_path)
                engine.runAndWait()
                success = True
            except Exception:
                pass
                
        if success:
            print(f"[Simulated Audio] Synthesized voice for text '{text_to_speak}' saved to: {output_path}")
        else:
            # Absolute fallback: write random/silent audio sequence so the code runs without failure
            silent_audio = np.zeros(int(duration_seconds * sample_rate))
            sf.write(output_path, silent_audio, sample_rate)
            print(f"[Simulated Audio] Silent dummy file saved to: {output_path}")

# ==============================================================================
# COMMAND PARSING LOGIC
# ==============================================================================
def parse_and_execute_command(text, mode="offline"):
    """
    Parses command text and publishes the execution action via MQTT to the ESP32.
    Supports both offline phonetic English and online Sinhala scripts.
    
    Parameters:
    - text: Transcribed text string.
    - mode: "offline" or "online"
    """
    text_lower = text.lower().strip()
    
    # Defaults
    device = None
    action = None
    
    if mode == "online":
        # Sinhala Script parsing
        print(f"[Parser] Parsing online Sinhala text: '{text}'")
        
        # Resolve device
        if "ලයිට්" in text_lower or "light" in text_lower:
            device = "light"
        elif "ෆෑන්" in text_lower or "fan" in text_lower:
            device = "fan"
            
        # Resolve action
        if "දාන්න" in text_lower or "ඔන්" in text_lower or "danna" in text_lower:
            action = "ON"
        elif "නිවන්න" in text_lower or "ඕෆ්" in text_lower or "niwanna" in text_lower:
            action = "OFF"
            
    else:
        # Offline phonetic English parsing
        print(f"[Parser] Parsing offline phonetic text: '{text_lower}'")
        
        # Resolve device
        if "light" in text_lower or "like" in text_lower or "right" in text_lower:
            device = "light"
        elif "fan" in text_lower or "pan" in text_lower or "ten" in text_lower or "sam" in text_lower:
            device = "fan"
            
        # Resolve action (robust mapping for Vosk phonetics)
        if any(w in text_lower for w in ["danna", "down", "on", "done", "then", "can", "data", "don"]):
            action = "ON"
        elif any(w in text_lower for w in ["niwanna", "near", "no", "off", "want", "went", "winner", "only", "one", "net", "wanna", "nirvana"]):
            action = "OFF"
            
    # Route command to Flask server running on RPI4
    if device and action:
        print(f"[Parser] SUCCESS: Identified Device = {device.upper()} | Action = {action}")
        # Determine channel ID based on device
        channel_id = CHANNEL_LIGHT if device == "light" else CHANNEL_FAN
        
        url = (
            f"http://{FLASK_SERVER_IP}:{FLASK_SERVER_PORT}/channels/{channel_id}/control"
            f"?command={action}&Command={action}&action={action}&state={action}&status={action}"
            f"&Status={action}&value={action}&Value={action}&cmd={action}&Cmd={action}"
            f"&payload={action}&device={device}"
        )
        
        payload = {
            "action": action,
            "command": action,
            "Command": action,
            "state": action,
            "status": action,
            "Status": action,
            "value": action,
            "Value": action,
            "cmd": action,
            "Cmd": action,
            "payload": action,
            "device": device,
            "device_id": device + "_1"
        }
        
        success = False
        
        # 1. Send as Form Data (x-www-form-urlencoded)
        try:
            print(f"[HTTP Client] Attempting Form Data POST to {url}")
            response = requests.post(url, data=payload, timeout=5.0)
            print(f"[HTTP Client] Form Data Response status: {response.status_code}")
            if response.status_code == 200:
                print(f"[HTTP Client] Form Data Response text: {response.text}")
                success = True
        except Exception as e:
            print(f"[WARNING] Form Data request failed: {e}")
            
        # 2. Send as JSON Payload
        try:
            print(f"[HTTP Client] Attempting JSON POST to {url}")
            response = requests.post(url, json=payload, timeout=5.0)
            print(f"[HTTP Client] JSON Response status: {response.status_code}")
            if response.status_code == 200:
                print(f"[HTTP Client] JSON Response text: {response.text}")
                success = True
        except Exception as e:
            print(f"[WARNING] JSON request failed: {e}")
            
        return success
    else:
        print(f"[Parser] FAILED: Could not resolve device or action in transcribed text: '{text}'")
        return False

# ==============================================================================
# PIPELINE ENHANCEMENT (COMPARE ALL FILTERS)
# ==============================================================================
def apply_all_noise_reduction_methods(noisy_wav_path, sample_rate=16000):
    """
    Applies all 6 noise reduction filters to the recorded noisy command,
    saves the enhanced outputs, and transcribes each using offline Vosk to demonstrate comparison.
    """
    print("\n--- Running Noise Reduction Comparative Benchmark ---")
    # Load noisy file
    y, sr = sf.read(noisy_wav_path)
    
    # Define filters to run
    filters = {
        "1. Spectral Subtraction": lambda: audio_filters.spectral_subtraction(y, sr),
        "2. Static Wiener Filter": lambda: audio_filters.wiener_filter(y, sr),
        "3. Wavelet Denoising": lambda: audio_filters.wavelet_denoising(y),
        "4. Spectral Gating (Audacity)": lambda: audio_filters.spectral_gating(y, sr),
        "5. Butterworth Bandpass": lambda: audio_filters.bandpass_filter(y, sr),
        "6. proposed VGDWF (Custom)": lambda: audio_filters.vad_guided_dynamic_wiener_filter(y, sr)
    }
    
    transcriptions_offline = {}
    
    # Process each filter
    for name, filter_func in filters.items():
        clean_filepath = os.path.join(BASE_DIR, f"temp_clean_{name.split('.')[0]}.wav")
        start_time = time.time()
        
        # Apply filter
        y_clean = filter_func()
        duration_ms = (time.time() - start_time) * 1000
        
        # Save clean audio
        sf.write(clean_filepath, y_clean, sr)
        
        # Transcribe offline (Vosk)
        text_off = offline_recognition.transcribe_offline(clean_filepath)
        transcriptions_offline[name] = text_off
        
        print(f"[Filter Stats] {name}: Processing Time = {duration_ms:.1f}ms")
        
    # Print comparison table to console
    print("\n" + "="*60)
    print(f"{'FILTER METHOD':<30} | {'OFFLINE RESULT (VOSK)':<25}")
    print("="*60)
    for name in filters.keys():
        print(f"{name:<30} | {transcriptions_offline[name]:<25}")
    print("="*60 + "\n")
    
    # Return path of proposed custom model output for execution pipeline
    return os.path.join(BASE_DIR, "temp_clean_6.wav")

# ==============================================================================
# MAIN SYSTEM ROUTINE
# ==============================================================================
def get_registered_users(base_dir):
    """Discovers all registered user names based on files matching *_embedding.npy."""
    users = []
    if os.path.exists(base_dir):
        for filename in os.listdir(base_dir):
            if filename.endswith("_embedding.npy"):
                username = filename[:-14] # strip "_embedding.npy"
                if username:
                    users.append(username)
    return sorted(users)

# ==============================================================================
# MAIN SYSTEM ROUTINE
# ==============================================================================
def main():
    print("======================================================================")
    print("       AI BASED VOICE CONTROLLED HOME AUTOMATION SYSTEM (SINHALA)     ")
    print("======================================================================")
    
    # --------------------------------------------------------------------------
    # USER DATABASE & STARTUP PHASE
    # --------------------------------------------------------------------------
    registered_users = get_registered_users(BASE_DIR)
    
    # 1. Register first user if database is empty
    if not registered_users:
        print("\n=== User Profile Registration ===")
        print("No registered users found. You must enroll the first user profile to start.")
        username = ""
        while not username:
            try:
                username = input("Enter username to register: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[System] Registration cancelled. Exiting.")
                sys.exit(0)
            if not username:
                print("[ERROR] Username cannot be empty. Please enter a valid name.")
                
        user_emb_path = os.path.join(BASE_DIR, f"{username}_embedding.npy")
        
        # Delete existing registration file if it exists to allow re-registration
        if os.path.exists(user_emb_path):
            try:
                os.remove(user_emb_path)
            except Exception:
                pass

        print(f"\n[Registration] Please record your voice to register the profile for '{username}'.")
        print("[Registration] You will have 5 seconds to record your voice print.")
        print("[Registration] Say: 'Hay Kasu' or similar voice sequence to enroll.")
        input("Press ENTER to start voice recording... ")
        
        # Record registration audio
        record_audio(REGISTRATION_AUDIO, duration_seconds=5.0)
        
        # Denoise registration audio using VGDWF
        print("[DSP] Denoising registration voice print (VGDWF filtering)...")
        y_reg, sr_reg = sf.read(REGISTRATION_AUDIO)
        y_reg_clean = audio_filters.vad_guided_dynamic_wiener_filter(y_reg, sr_reg)
        sf.write(REGISTRATION_AUDIO, y_reg_clean, sr_reg)
        
        # Enroll user using SpeechBrain
        success = speaker_recognition.enroll_user(REGISTRATION_AUDIO, user_emb_path)
        if success:
            print("\nSuccessfully Registered")
            play_audio(SOUND_REG_SUCCESS)
            # Update the registered users list
            registered_users = get_registered_users(BASE_DIR)
        else:
            print("[ERROR] Enrollment failed. Exiting.")
            sys.exit(1)
            
    # 2. Offer option to register another user (preserves database)
    while True:
        registered_users = get_registered_users(BASE_DIR)
        print("\n" + "="*50)
        print(f"Registered Users in Database: {', '.join(registered_users)}")
        print("="*50)
        
        try:
            choice = input("Do you want to register another user? (y/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n[System] Exiting Voice Control System. Goodbye!")
            sys.exit(0)
            
        if choice in ["y", "yes"]:
            print("\n=== Register Another User ===")
            username = ""
            while not username:
                try:
                    username = input("Enter username to register: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\n[System] Registration cancelled.")
                    break
                if not username:
                    print("[ERROR] Username cannot be empty. Please enter a valid name.")
                    
            if not username:
                continue
                
            user_emb_path = os.path.join(BASE_DIR, f"{username}_embedding.npy")
            
            if os.path.exists(user_emb_path):
                try:
                    os.remove(user_emb_path)
                except Exception:
                    pass

            print(f"\n[Registration] Please record your voice to register the profile for '{username}'.")
            print("[Registration] You will have 5 seconds to record your voice print.")
            print("[Registration] Say: 'Hay Kasu' or similar voice sequence to enroll.")
            input("Press ENTER to start voice recording... ")
            
            # Record registration audio
            record_audio(REGISTRATION_AUDIO, duration_seconds=5.0)
            
            # Denoise registration audio using VGDWF
            print("[DSP] Denoising registration voice print (VGDWF filtering)...")
            y_reg, sr_reg = sf.read(REGISTRATION_AUDIO)
            y_reg_clean = audio_filters.vad_guided_dynamic_wiener_filter(y_reg, sr_reg)
            sf.write(REGISTRATION_AUDIO, y_reg_clean, sr_reg)
            
            # Enroll user using SpeechBrain
            success = speaker_recognition.enroll_user(REGISTRATION_AUDIO, user_emb_path)
            if success:
                print("\nSuccessfully Registered")
                play_audio(SOUND_REG_SUCCESS)
            else:
                print("[ERROR] Enrollment failed. Returning to menu...")
        elif choice in ["n", "no"]:
            break
        else:
            print("[ERROR] Invalid choice. Please enter 'y' or 'n'.")
            
    # --------------------------------------------------------------------------
    # VOICE CONTROL LOOP
    # --------------------------------------------------------------------------
    print("\n=== Voice Control System Activated ===")
    
    while True:
        try:
            print("\n" + "-"*60)
            print("[Command Execution Mode]")
            print("Press ENTER to use your MICROPHONE, or type the command manually:")
            
            try:
                user_input = input(">> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[System] Exiting Voice Control System. Goodbye!")
                break
            
            is_matched = False
            matched_user = None
            trigger_command = False
            cmd_text = ""
            
            # Text manual path
            if user_input:
                cmd_text = user_input
                print(f"[Command] Manual text command input: '{cmd_text}'")
                print("[Security Simulation] Select speaker identity to simulate:")
                
                # Fetch fresh list of registered users
                registered_users = get_registered_users(BASE_DIR)
                for idx, user in enumerate(registered_users, 1):
                    print(f"  {idx}. Registered User: {user} (Access Granted)")
                print(f"  {len(registered_users) + 1}. Unregistered User (Access Denied)")
                
                try:
                    sim_choice = input(f"Enter option (1-{len(registered_users) + 1}): ").strip()
                    choice_idx = int(sim_choice)
                    if 1 <= choice_idx <= len(registered_users):
                        is_matched = True
                        matched_user = registered_users[choice_idx - 1]
                        trigger_command = True
                    else:
                        is_matched = False
                        trigger_command = True
                except (ValueError, KeyboardInterrupt, EOFError):
                    is_matched = False
                    trigger_command = True
            
            # Live microphone path
            else:
                print("\n[Listen] Ready for voice command. Please speak control input:")
                print("--> 'Light eka danna' / 'Light eka niwanna'")
                print("--> 'Fan eka danna' / 'Fan eka niwanna'")
                
                # Record command segment
                record_audio(TEMP_COMMAND_WAV, duration_seconds=4.0)
                
                # Apply all 6 noise reduction methods and get path of clean custom VGDWF output
                clean_command_wav = apply_all_noise_reduction_methods(TEMP_COMMAND_WAV)
                
                # Check speaker verification directly on the recorded command audio against all registered users
                print("[Security] Verifying speaker identity against all database voice profiles...")
                is_matched = False
                matched_user = None
                best_similarity = -1.0
                
                registered_users = get_registered_users(BASE_DIR)
                for r_user in registered_users:
                    emb_path = os.path.join(BASE_DIR, f"{r_user}_embedding.npy")
                    matched, similarity = speaker_recognition.verify_speaker(
                        test_audio_path=clean_command_wav, 
                        enrollment_path=emb_path,
                        threshold=0.50 # Using 0.50 as a robust threshold for text-independent command matching
                    )
                    if matched and similarity > best_similarity:
                        is_matched = True
                        matched_user = r_user
                        best_similarity = similarity
                
                trigger_command = True
                
            if trigger_command:
                if is_matched:
                    # Case 1: Registered User Matches
                    print("\n" + "#"*60)
                    print(f"   [AUTHORIZED] Voice Print MATCHED! (User: {matched_user}) Access Granted.   ")
                    print("#"*60)
                    play_audio(SOUND_USER_RECOGNIZED)
                    
                    if user_input:
                        # Manual execution
                        parse_and_execute_command(cmd_text, mode="offline")
                    else:
                        # Live microphone execution (transcribe using Vosk ASR)
                        print("[ASR] Deciphering final clean command offline...")
                        offline_text = offline_recognition.transcribe_offline(clean_command_wav)
                        parse_and_execute_command(offline_text, mode="offline")
                else:
                    # Case 2: Speaker mismatch (Unauthorized)
                    print("\n" + "!"*60)
                    print("   [ACCESS DENIED] Speaker Verification Mismatch (Unauthorized).   ")
                    print("!"*60)
                    play_audio(SOUND_USER_UNRECOGNIZED)
                    print("[Security] Unauthorized voice detected. Command execution rejected.")
                    time.sleep(DELAY_AFTER_UNREGISTERED_REJECTION)
                    
        except KeyboardInterrupt:
            print("\n[System] Exiting Voice Control System. Goodbye!")
            break
        except Exception as e:
            print(f"[ERROR] Exception in main loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
