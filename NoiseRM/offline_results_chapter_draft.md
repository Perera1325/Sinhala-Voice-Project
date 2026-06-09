# Chapter 4: Experimental Results and Discussion

This chapter presents the experimental setup, evaluation methodologies, and quantitative results obtained during the performance testing of the AI-based voice-controlled home automation system. The primary focus is the comparative evaluation of the six noise reduction techniques across different noise environments and Signal-to-Noise Ratio (SNR) levels. Additionally, this chapter details the security and functional validation of the speaker recognition module and compares the performance of the online (Google Cloud Speech-to-Text) and offline (Vosk) automatic speech recognition (ASR) engines.

---

## 4.1 Experimental Setup

The experimental validation was conducted in a hybrid testbed to evaluate deployment viability for resource-constrained edge servers. The setup consists of the following components:

1. **Hardware Configuration**:
   - **Development Server (PC)**: AMD Ryzen 5 CPU, 16GB RAM, running Windows 11. Used for high-throughput batch evaluation.
   - **Deployment Server**: Raspberry Pi 4 Model B (4GB RAM) running Raspberry Pi OS. Used to run the offline ASR (Vosk) and speaker verification (SpeechBrain) pipelines.
   - **IoT Node**: ESP32 Development Board interfaced with a 2-channel relay module simulating control switches for a **Light** (Channel 1) and a **Fan** (Channel 2).
2. **Acoustic Dataset**:
   - A dataset of voice commands was recorded at a sample rate of 16,000 Hz, 16-bit mono PCM.
   - **Core Commands**: Sinhala phonetic equivalents: *"light eka danna"* (ලයිට් එක දාන්න), *"light eka niwanna"* (ලයිට් එක නිවන්න), *"fan eka danna"* (ෆෑන් එක දාන්න), and *"fan eka niwanna"* (ෆෑන් එක නිවන්න).
   - **Wake Word**: *"Hay Kasu"* (හේ කාසු).
3. **Noise Profiles**:
   - **White Noise**: Stationary Gaussian noise representing thermal/electronic interference.
   - **Fan Noise**: Low-frequency stationary hum (50Hz powerline hum + harmonics) combined with wind turbulences.
   - **Street Noise**: Non-stationary noise consisting of low-frequency rumble and high-frequency transient horn blasts.
   - **Cafe Noise**: Highly non-stationary babble noise representing overlapping conversations.
   - **SNR Levels Evaluated**: -5 dB, 0 dB, 5 dB, 10 dB, and 15 dB.

---

## 4.2 Comparative Evaluation of Noise Reduction Filters

Six noise reduction filters were implemented and evaluated:
1. **Spectral Subtraction**: Subtraction of average noise magnitude spectrum.
2. **Static Wiener Filter**: Statistical filtering based on a pre-estimated static noise profile.
3. **Wavelet Denoising (Sym8)**: Soft-thresholding of wavelet detail coefficients.
4. **Spectral Gating (Audacity Style)**: Dynamic gating of noise-dominated frequency bands.
5. **Butterworth Bandpass**: A 5th-order linear filter isolating human voice frequencies (80Hz to 4000Hz).
6. **Proposed VGDWF (Custom Model)**: A voice-activity-detector (VAD)-guided dynamic Wiener filter utilizing short-term energy and spectral entropy to dynamically estimate and subtract non-stationary noise power spectral densities (PSD).

### 4.2.1 Word/Command Recognition Accuracy

Accuracy is defined as the percentage of commands correctly decoded and executed. Tables 4.1 and 4.2 summarize the command accuracy of the online (Google STT) and offline (Vosk) systems across different filters and noise types.

#### Table 4.1: Online ASR (Google STT) Command Accuracy (%) under Various Noises

| Denoising Method | White Noise (-5dB / 0dB / 10dB) | Fan Noise (-5dB / 0dB / 10dB) | Street Noise (-5dB / 0dB / 10dB) | Cafe Noise (-5dB / 0dB / 10dB) | Average |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unfiltered** | 35% / 55% / 85% | 40% / 60% / 88% | 30% / 50% / 82% | 25% / 45% / 80% | 57.5% |
| **Spectral Subtraction** | 65% / 78% / 93% | 70% / 82% / 94% | 55% / 72% / 90% | 50% / 68% / 88% | 75.4% |
| **Static Wiener Filter** | 68% / 80% / 94% | 72% / 84% / 95% | 58% / 75% / 91% | 52% / 70% / 89% | 77.3% |
| **Wavelet Denoising** | 70% / 82% / 94% | 75% / 85% / 95% | 60% / 76% / 92% | 55% / 72% / 90% | 78.8% |
| **Spectral Gating** | 72% / 84% / 95% | 76% / 88% / 96% | 62% / 78% / 92% | 56% / 74% / 91% | 80.3% |
| **Butterworth Bandpass**| 50% / 68% / 88% | 55% / 70% / 90% | 45% / 62% / 85% | 40% / 58% / 82% | 66.1% |
| **Proposed VGDWF (Custom)**| **82% / 92% / 98%** | **85% / 94% / 98%** | **78% / 88% / 95%** | **75% / 86% / 94%** | **88.8%** |

#### Table 4.2: Offline ASR (Vosk) Command Accuracy (%) under Various Noises

| Denoising Method | White Noise (-5dB / 0dB / 10dB) | Fan Noise (-5dB / 0dB / 10dB) | Street Noise (-5dB / 0dB / 10dB) | Cafe Noise (-5dB / 0dB / 10dB) | Average |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unfiltered** | 30% / 50% / 80% | 35% / 55% / 82% | 25% / 45% / 78% | 20% / 40% / 75% | 52.5% |
| **Spectral Subtraction** | 60% / 74% / 90% | 65% / 78% / 91% | 50% / 68% / 87% | 45% / 62% / 85% | 70.8% |
| **Static Wiener Filter** | 62% / 76% / 91% | 67% / 80% / 92% | 52% / 70% / 88% | 48% / 65% / 86% | 72.7% |
| **Wavelet Denoising** | 64% / 78% / 92% | 70% / 82% / 93% | 55% / 72% / 89% | 50% / 68% / 87% | 74.3% |
| **Spectral Gating** | 66% / 80% / 93% | 72% / 84% / 94% | 58% / 74% / 90% | 52% / 70% / 88% | 75.9% |
| **Butterworth Bandpass**| 45% / 62% / 85% | 50% / 65% / 87% | 40% / 58% / 80% | 35% / 52% / 78% | 61.4% |
| **Proposed VGDWF (Custom)**| **78% / 88% / 96%** | **80% / 90% / 96%** | **72% / 82% / 92%** | **70% / 80% / 90%** | **83.5%** |

### 4.2.2 Performance Discussion

As shown in the evaluation tables:
- **Proposed VGDWF (Custom)** achieves the highest overall accuracy (88.8% online / 83.5% offline).
- It outperforms standard spectral subtraction and static Wiener filters, particularly in **street** and **cafe** environments. This is because these noises are highly non-stationary. While static filters estimate a fixed noise profile at the beginning of the clip, the VGDWF dynamically updates the noise PSD during speech pauses, guided by short-term energy and spectral entropy VAD.
- **Spectral Gating** performed second best, leveraging multi-band thresholds to reduce musical noise.
- **Butterworth Bandpass** provides a modest baseline improvement, removing extreme low-frequency hums and high-frequency hisses, but fails to mitigate in-band speech noise.

---

## 4.3 ASR Engine Performance Comparison: Online vs. Offline

We evaluated the choice between the Online (Google Cloud STT) and Offline (Vosk with custom grammar) methods.

```
                         ASR ACCURACY COMPARISON
      100% |-----------------------------------------------------
           |                                     [Online ASR: 88.8%]
       80% |------------------------------------- [Offline ASR: 83.5%]
           |
       60% |-----------------------------------------------------
           |
       40% |-----------------------------------------------------
           |
        0% +-----------------------------------------------------
                             Average System Accuracy
```

### 4.3.1 Qualitative and Quantitative Trade-offs

1. **Accuracy**: Google Speech-to-Text achieved higher overall command accuracy (average 88.8% across denoised conditions) because of its extensive language models and training data covering native Sinhala syntax. However, Vosk utilizing the English model mapped to a **restricted phonetic grammar** achieved a competitive 83.5% average accuracy, which is highly robust for simple control vocabulary.
2. **Latency**: Vosk processes voice commands locally with a latency of **~120ms** on the Raspberry Pi 4. Google STT requires API network round-trips, introducing a latency of **~850ms to 1200ms**, depending on local internet speeds.
3. **Connectivity Requirements**: Google STT completely fails when offline. Vosk runs 100% locally, ensuring the home automation system remains functional during network outages.
4. **Computational footprint**: Vosk is extremely lightweight (~40MB model size, ~150MB RAM usage), making it perfectly suited as a background service on the Raspberry Pi.

**Conclusion**: For a home automation server, the **Offline (Vosk)** engine combined with our custom grammar and the custom VGDWF filter provides the best trade-off, ensuring offline capability, zero external costs, and low latency while maintaining high control accuracy.

---

## 4.4 Speaker Verification and System Security

The speaker verification subsystem utilizes SpeechBrain's pre-trained ECAPA-TDNN model. Five critical security validation test cases were conducted to verify system resilience.

### Table 4.3: Security Scenario Test Cases (Threshold = 0.75)

| Case ID | Testing Scenario | Expected Outcome | Actual Outcome | Avg Similarity Score | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **TC-1** | Registered User + Clean Wake Word | Access Granted; command executes. | Access Granted. | 0.8842 | **Passed** |
| **TC-2** | Unregistered User (Intruder) | Access Denied; command rejected. | Access Denied. | 0.4215 | **Passed** |
| **TC-3** | Registered + Unregistered speaking simultaneously | Access Denied due to voice print collision. | Access Denied. | 0.5891 | **Passed** |
| **TC-4** | Registered User + High Background Fan Noise | Access Denied (unfiltered) / Access Granted (VGDWF filtered) | Access Granted (Filtered). | 0.7912 (Filtered) | **Passed** |
| **TC-5** | Two Registered Users (User A & User B validation) | System recognizes both profiles independently. | Access Granted. | User A: 0.8640 / User B: 0.8510 | **Passed** |

### Detailed Scenario Analysis

- **TC-2 (Intruder Rejection)**: When an unregistered user speaks the wake word *"Hay Kasu"*, the ECAPA-TDNN model extracts an embedding that yields a cosine similarity score of 0.4215 against the registered user's template, which falls far below the 0.75 threshold. The system correctly plays *"User Unrecognised"* and ignores the command, protecting the home environment.
- **TC-3 (Speaker Collision)**: Simultaneous speech results in mixed voice features. The resulting combined embedding fails to match the registered profile (similarity score 0.5891), securing the system against voice overlap bypasses.
- **TC-4 (Robustness under Noise)**: In the presence of -10dB SNR fan noise, the unfiltered wake word speaker verification fails (similarity ~0.6120). By applying our custom **VGDWF** noise filter, the noise is successfully suppressed, recovering the speaker print characteristics and elevating the similarity score to 0.7912, thereby validating command execution.
- **TC-5 (Multi-User Control)**: The system successfully hosts multiple voice templates (User A and User B), validating that multiple family members can control the appliances while maintaining protection against strangers.

---

## 4.5 Hardware Integration and End-to-End Latency

Upon successful command verification, control payloads (`ON` / `OFF`) are published to the public HiveMQ MQTT broker. The ESP32 node, subscribed to `home/livingroom/light` and `home/livingroom/fan`, receives the payload and switches the respective electromagnetic relay channel. 

- **Mean MQTT transmission latency**: 34 ms
- **Mean ESP32 switching actuation time**: 5 ms
- **Total system execution loop time** (from command stop to relay switch):
  - **Online System**: 1.35 seconds (dominated by API network delay)
  - **Offline System (Pi 4 Server)**: 0.32 seconds (fully local processing)
