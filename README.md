# Sinhala Voice-Controlled Smart Home Automation System

An advanced, AI-powered Smart Home system built to understand **Singlish (Sinhala + English)** commands. This system uses a custom Convolutional Neural Network (CNN) deployed via TensorFlow Lite, features Speaker Biometric Security, and integrates directly with a local Flask server to control ESP32 IoT devices.

---

## 🏗️ System Architecture

This system uses a **Local Network Architecture** to ensure privacy and low latency. **All devices (Raspberry Pi, Android Phone, and ESP32s) must be connected to the SAME Wi-Fi network** for the system to work.

### 1. The Hub: Raspberry Pi 4
The Raspberry Pi acts as the central brain of the house. It runs two main things:
1. **Your Existing Flask Server (Port 5000):** This is the server your Android App already talks to. It listens for HTTP requests at specific endpoints (e.g., `http://192.168.1.13:5000/channels/<UUID>/control`) and triggers the ESP32s.
2. **The Voice AI Engine (`main_production.py`):** This script runs endlessly in the background. It listens for the Wake Word, verifies the speaker's identity, classifies the command using TFLite, and then acts like a "virtual Android App" by sending the exact same HTTP requests to your Flask Server to turn the lights on/off.

### 2. The Cloud: Firebase Web Dashboard
To register new family members into the security system, we have deployed a React Web Dashboard to Firebase.
- URL: [https://kasundi-ai-home.web.app](https://kasundi-ai-home.web.app)
- You use this website to record a 3-second voice sample, which is processed and saved as a Voice Fingerprint in the Raspberry Pi's SQLite database.

---

## 🧠 Current AI Capabilities

### 1. Voice Biometrics (Security First)
The system will **ONLY work for registered voices**. If a stranger or unregistered person says the wake word and issues a command, the Biometrics Engine will reject it as an "Intruder" and ignore the command. 
* **Note:** You must use the Web Dashboard to register your voice before the system will obey your commands.

### 2. Supported Commands (Light Only)
Currently, the TensorFlow Lite model (`light_model.tflite`) has been explicitly trained **only for the Light On and Light Off functions in Singlish**.
- E.g., *"Light eka danna"*, *"Light eka on krnna"*
- To add Fan and Curtain controls, you must record audio datasets for those devices and retrain the 7-class model.

---

## 🚀 How to Implement on Raspberry Pi

Follow these exact steps to deploy the AI system onto your Raspberry Pi 4.

### Step 1: Prepare the Environment
Open a terminal on your Raspberry Pi and clone this repository:
```bash
git clone https://github.com/Perera1325/Sinhala-Voice-Project.git
cd Sinhala-Voice-Project
```

Install the required Python packages (it is highly recommended to use a virtual environment):
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt-get install portaudio19-dev  # Required for sounddevice microphone access
```

### Step 2: Start Your Existing Systems
Ensure your existing Android-compatible Flask server is running on the Pi (e.g., at `192.168.1.13:5000`) and that your ESP32 hardware is powered on and connected to the same Wi-Fi.

### Step 3: Register Your Voice
Before the AI will listen to you, you must register your voice profile.
1. In a new terminal on the Pi, run the biometrics helper server:
   ```bash
   python src/app.py
   ```
2. Link it to the internet using localtunnel:
   ```bash
   lt --port 5000
   ```
3. Update the React App (`web_dashboard/src/App.jsx`) with your new tunnel URL, rebuild, and deploy.
4. Go to the live website, navigate to the **Register** tab, and record your voice to save it to the SQLite database.

### Step 4: Run the AI Pipeline!
Once your voice is registered, you can start the main listener.
Open a terminal on the Pi and run:
```bash
python src/main_production.py
```
**The system is now live!** 
1. Say **"Hey Kasu"** to wake it up.
2. It will verify your voice biometrics against the database.
3. If verified, say **"Light eka danna"**.
4. The TFLite model will classify the command and send the UUID trigger to your existing Flask server to turn on the ESP32!

---

## 🛠️ Next Steps for Development
1. **Train a Real Wake Word Model:** The current wake word system uses an audio volume threshold as a placeholder. You need to record 100 samples of "Hey Kasu" and train a Wake Word CNN.
2. **Train Fan & Curtain:** Record datasets for the remaining commands to unlock the full 7-class potential of the AI. Update the UUID mapping in `src/main_production.py` once trained!
