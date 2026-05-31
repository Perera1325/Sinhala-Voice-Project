import time
import sounddevice as sd
import sys

# Ensure src directory is in path
sys.path.append("src")
import speaker_biometrics
import database

import pyttsx3

SAMPLE_RATE = 16000
RECORD_DURATION = 5  # Record for 5 seconds to get a solid voice print

def speak(text):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if "Zira" in voice.name or "female" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.say(text)
    engine.runAndWait()

def main():
    print("\n" + "="*50)
    print("🎙️ VOICE BIOMETRICS ENROLLMENT 🎙️")
    print("="*50)
    
    # Speak the introductory message
    speak("I am your virtual assistant. You can register your voice to my system and assist with me!")

    # Ensure database exists
    database.init_db()

    # Get name from command line argument or fallback to input
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:]).strip()
    else:
        name = input("\nEnter your name (e.g., Kasundi): ").strip()
        
    if not name:
        print("Name cannot be empty. Exiting.")
        return

    print(f"\nHello {name}! Get ready to record your voice.")
    print("Please read the following sentence clearly:")
    print(">> 'The quick brown fox jumps over the lazy dog. Hello system, this is my voice.' <<")
    
    speak(f"Hello {name}. Please press enter, then read the sentence on the screen clearly to record your voice.")
    
    input("\nPress ENTER when you are ready to start recording...")

    print("\n🎤 Recording in...")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
        
    print("🔴 RECORDING NOW (5 seconds)... Speak!")
    
    audio_data = sd.rec(int(RECORD_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    
    print("✅ Recording complete. Processing your voice print...")
    
    # Flatten the audio data for the biometrics script
    audio_flat = audio_data.flatten()
    
    fingerprint = speaker_biometrics.extract_voice_fingerprint(audio_data=audio_flat)
    
    if fingerprint is None:
        print("❌ Failed to extract voice print. You might not have spoken loudly enough, or the audio was too short.")
        print("Please run the script again.")
        return
        
    database.add_user(name, fingerprint)
    
    print(f"\n🎉 Success! '{name}' has been securely enrolled in the voice database.")
    print("You can now run `python src\\main_production.py` and the system will recognize you!")

if __name__ == "__main__":
    main()
