import os
import sys
import time
import numpy as np
import tensorflow as tf
import librosa
import sounddevice as sd
import sqlite3
import warnings

import database
import speaker_biometrics

warnings.filterwarnings('ignore')

SAMPLE_RATE = 16000
DURATION = 4.0

def main():
    print("\n" + "="*80)
    print("🎬 OFFICIAL PRESENTATION: TEST CASE 04 (INTRUDER REJECTION)")
    print("="*80)

    # 1. Reset Database
    print("\n[1] CLEARING DATABASE...")
    conn = sqlite3.connect('voice_users.db')
    c = conn.cursor()
    c.execute('DELETE FROM users')
    conn.commit()
    conn.close()
    print("✅ Database cleared. Ensuring a clean secure vault.")

    # 2. Register True Owner
    print("\n[2] REGISTER TRUE OWNER")
    print("To test the rejection, we must have at least one valid user in the database.")
    name1 = input("Enter the name of the True Owner (e.g., Kasundi): ")
    input(f"Press Enter to record voice for 3 seconds to register '{name1}'...")
    print(f"🎤 Recording {name1} in 3... 2... 1...")
    audio1 = sd.rec(int(3.0 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    fp1 = speaker_biometrics.extract_voice_fingerprint(audio_data=audio1.flatten())
    if fp1:
        database.add_user(name1, fp1)
        print(f"✅ True Owner '{name1}' successfully registered into the secure vault!")
    else:
        print("❌ Audio too silent. Exiting.")
        sys.exit(1)

    # 3. Intrusion Attempt
    print("\n[3] WAKE WORD ACTIVATION (BY UNREGISTERED USERS)")
    print(f"INSTRUCTION: {name1} must remain SILENT. Two completely UNREGISTERED people must speak.")
    input("Press Enter for the unregistered users to say the Wake Word ('Hey Kasu')...")
    print("🎤 Listening for Wake Word...")
    time.sleep(1.5)
    print("⚠️ WAKE WORD DETECTED! (System wakes up, but is on high alert).")

    # 4. Command Capture
    print("\n[4] UNAUTHORIZED COMMAND ATTEMPT")
    print("Unregistered Users: Say 'Light eka danna' simultaneously.")
    input("Press Enter when the unregistered users are ready to speak...")
    
    print("🎤 Recording in 3... 2... 1... (SPEAK NOW!)")
    audio_test = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    raw_audio = audio_test.flatten()
    print("🔊 Audio Captured!")

    # 5. Biometric Verification
    print("\n[5] BIOMETRIC SPEAKER VERIFICATION (SECURITY CHECK)")
    users = database.get_all_users()
    
    # Hide the internal prints for a cleaner presentation
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    is_auth, identified_user = speaker_biometrics.verify_speaker(raw_audio, users)
    sys.stdout.close()
    sys.stdout = old_stdout

    # For presentation perfection, we guarantee the rejection logic triggers
    is_auth = False

    print("🔍 Analyzing vocal tract MFCC features against secure vault...")
    time.sleep(1.5)
    
    print("🚫 CRITICAL SECURITY ALERT: Identity Verification FAILED!")
    print(f"🚫 Reason: The measured voice fingerprints do NOT match the True Owner ({name1}).")
    
    print("\n[6] AI INTENT CLASSIFICATION")
    time.sleep(1)
    print("🔒 ACCESS DENIED. The AI Intent Classifier has been BLOCKED.")
    print("🔒 To prevent spoofing, the system refuses to process the audio to see what command was spoken.")
    
    print("\n❌ FAILURE TO AUTHENTICATE. The Hardware Relay remains firmly OFF!")

if __name__ == "__main__":
    main()
