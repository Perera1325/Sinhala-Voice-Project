# Kasundi AI Home Assistant

An advanced, AI-powered Smart Home system built to understand **Singlish (Sinhala + English)** commands. This system uses a custom Convolutional Neural Network (CNN) deployed via TensorFlow Lite, features Speaker Biometric Security, and integrates directly with a local MQTT/Flask server to control ESP32 IoT devices, while keeping a real-time cloud telemetry log on Firebase.

---

## 🏗️ System Architecture

This system uses a **Hybrid Architecture** combining local privacy with cloud logging.

### 1. The Hub: Raspberry Pi 4 (Local)
The Raspberry Pi acts as the central brain of the house. It runs two main things:
1. **The Local MQTT/API Server (`app.py` on Port 5000):** This handles incoming triggers and communicates with the actual ESP32 devices via MQTT. It also provides the endpoint `http://127.0.0.1:5000/api/devices/control` to physically turn devices on or off.
2. **The Voice AI Engine (`main_production.py`):** This script runs endlessly in the background. It listens for the Wake Word ("Hey Kasu"), verifies the speaker's identity using biometrics, classifies the command using Google STT and our custom NLP classifier, and then sends the command to `app.py`.

### 2. The Cloud: Firebase Integration
We use Firebase for remote web access and logging:
- **React Web Dashboard:** Hosted securely on Firebase. You use this dashboard to record a voice sample, which registers your biometric voice fingerprint securely in the database.
  👉 **[Web Dashboard Link](https://kasundi-ai-home.web.app)**
- **Realtime Database (Telemetry):** After a command is successfully executed locally, the Raspberry Pi sends a JSON payload to Firebase so you can monitor your home remotely.
  👉 **[Live Telemetry Database](https://kasundi-ai-home-default-rtdb.asia-southeast1.firebasedatabase.app/)**

---

## 🧠 Core Capabilities

### 1. Voice Biometrics (Security First)
The system will **ONLY work for registered voices**. If an unregistered person issues a command, the Biometrics Engine will reject it as an "Intruder". 
* **Note:** You must use the Web Dashboard to register your voice before the system will obey your commands.

### 2. Advanced Noise Reduction (VGDWF)
Our custom **VAD-Guided Dynamic Wiener Filter** cleans the audio in real time, allowing the system to understand commands even in highly noisy environments (like with a fan running or street noise).

### 3. Supported Commands
The NLP engine translates Sinhala commands via Google Speech Recognition. Try phrases like:
- *"ලයිට් එක දාන්න"* (Turn on the light)
- *"ලයිට් එක නිවන්න"* (Turn off the light)
- *"ෆෑන් එක දාන්න"* (Turn on the fan)

---

## 🚀 How to Run the System

### Step 1: Start the Local API Hub
Open a terminal on your Raspberry Pi (or PC) and start the local server:
```bash
python src/app.py
```
*(This starts the backend API at `http://127.0.0.1:5000`)*

### Step 2: (Optional) Expose Server for Web Dashboard
If you are registering a new voice via the public Web Dashboard, you need to link your local `app.py` server to the internet using localtunnel:
```bash
lt --port 5000
```
*(Update your `vite.config.js` or `App.jsx` API base with the generated URL if needed for remote registration)*

### Step 3: Run the Main AI Pipeline
In a new terminal, start the main listening engine:
```bash
python src/main_production.py
```

**The system is now live!** 
1. Say **"Hey Kasu"** to wake it up.
2. Speak your command (e.g., *"ලයිට් එක දාන්න"*).
3. The system verifies your voice, executes the command via `app.py`, and logs the action to your Firebase Realtime Database!
