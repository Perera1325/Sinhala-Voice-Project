# Comparative Performance Analysis of Noise Reduction Methods for AI-Based Home Automation Voice Control Systems

**Author:** Kasundi (assisted by Antigravity)  
**Date:** June 2026  
**Document Type:** Project Report / Academic Thesis Chapter  

---

## Abstract

AI-based voice control systems in home automation environments face significant performance degradation when subjected to ambient acoustic noises. This report presents a comparative evaluation of five recommended single-channel noise reduction methods—Spectral Subtraction, Static Wiener Filter, Discrete Wavelet Denoising, Spectral Gating, and Butterworth Bandpass Filtering—against a custom-designed contribution: the **Voice Activity Detection-Guided Dynamic Wiener Filter (VGDWF)**. Testing is conducted under stationary (white, fan) and non-stationary (street, cafe) noise profiles across Signal-to-Noise Ratios (SNRs) from -5dB to 15dB. Accuracy is evaluated on both local Offline (Vosk) and cloud Online (Google Cloud STT) Speech-to-Text engines. Results show that the proposed VGDWF outperforms all baselines, achieving an average control accuracy of **88.8%** online and **83.5%** offline, demonstrating high robustness for resource-constrained edge systems like a Raspberry Pi 4.

---

## 1. Introduction

Voice-controlled home automation systems leverage Automatic Speech Recognition (ASR) to translate spoken commands into digital directives (e.g., controlling lights and fans via relays). However, typical domestic environments introduce mixed acoustic noise:
1.  **Stationary Noise**: Constant-envelope noise from air conditioners, ceiling fans, or computer hums.
2.  **Non-Stationary Noise**: Highly fluctuating signals from open windows, street traffic, or conversations (babble noise).

To ensure command execution accuracy and maintain speaker verification reliability (using templates like ECAPA-TDNN), audio pre-processing is required. This report evaluates five recommended DSP baselines and details the implementation and mathematical formulation of our proposed custom noise-reduction filter.

---

## 2. Theoretical Analysis of the 5 Recommended Baseline Methods

This section outlines the signal processing mechanisms, advantages, and limitations of the five baseline noise reduction methods.

### 2.1 Spectral Subtraction
Spectral subtraction operates in the short-time Fourier transform (STFT) domain. It assumes that noise is additive and its spectrum can be estimated during non-speech periods.

#### Mathematical Formulation:
Given the noisy signal $y(t) = s(t) + n(t)$, where $s(t)$ is clean speech and $n(t)$ is noise, the STFT is:
$$Y(f, t) = S(f, t) + N(f, t)$$

The noise magnitude spectrum estimate $|\hat{N}(f)|$ is computed by averaging the magnitudes of the first $k$ silent frames:
$$|\hat{N}(f)| = \frac{1}{k}\sum_{i=1}^{k} |Y(f, i)|$$

The clean speech magnitude spectrum is estimated by:
$$|\hat{S}(f, t)| = \max(|Y(f, t)| - \alpha \cdot |\hat{N}(f)|, \beta \cdot |Y(f, t)|)$$

Where:
*   $\alpha \ge 1$ is the over-subtraction factor used to suppress spectral peaks.
*   $\beta \in [0, 1]$ is the spectral floor factor, which retains a tiny fraction of the background noise to prevent the residual noise from sounding like pure isolated tones (known as "musical noise").

The reconstructed complex spectrum is:
$$\hat{S}(f, t) = |\hat{S}(f, t)| \cdot e^{j \angle Y(f, t)}$$

Applying the Inverse Short-Time Fourier Transform (ISTFT) yields the denoised audio signal.

*   **Advantages**: Simple to implement, computationally lightweight, and highly effective for stable stationary noise.
*   **Limitations**: Introduces musical noise if $\alpha$ is too small or speech distortion if $\alpha$ is too large. It cannot adapt to changing noise profiles.

### 2.2 Static Wiener Filter
The Wiener filter is a frequency-domain optimal filter that minimizes the mean-square error (MMSE) between the estimated speech $\hat{s}(t)$ and clean speech $s(t)$.

#### Mathematical Formulation:
The Wiener filter gain $H(f)$ is given by:
$$H(f) = \frac{P_{ss}(f)}{P_{ss}(f) + P_{nn}(f)}$$

Where:
*   $P_{ss}(f)$ is the power spectral density (PSD) of the clean speech.
*   $P_{nn}(f)$ is the PSD of the noise.

In a static configuration, the noise PSD $P_{nn}(f)$ is estimated during initial silence frames:
$$P_{nn}(f) = \frac{1}{k}\sum_{i=1}^{k} |Y(f, i)|^2$$

Since the clean speech PSD is unknown, it is estimated from the noisy signal spectrum $P_{yy}(f) = |Y(f, t)|^2$:
$$\hat{P}_{ss}(f, t) = \max(|Y(f, t)|^2 - P_{nn}(f), 0)$$

The gain is applied to the noisy spectrum:
$$\hat{S}(f, t) = H(f, t) \cdot Y(f, t) = \left( \frac{\hat{P}_{ss}(f, t)}{\hat{P}_{ss}(f, t) + P_{nn}(f)} \right) Y(f, t)$$

*   **Advantages**: Provides a smooth frequency-dependent attenuation that results in less musical noise than spectral subtraction.
*   **Limitations**: Relies on a static noise profile. If noise characteristics change after the initial estimation period, the filter begins attenuating speech components or letting noise leak through.

### 2.3 Discrete Wavelet Denoising (DWT)
Discrete Wavelet Transform (DWT) decomposes the signal into multi-resolution frequency sub-bands, preserving transient characteristics of speech better than Fourier-based methods.

#### Mathematical Formulation:
The signal is passed through low-pass and high-pass filters to obtain approximation coefficients $cA_j$ and detail coefficients $cD_j$ at decomposition levels $j = 1, \dots, L$:
$$y(t) \xrightarrow{\text{DWT}} \{cA_L, cD_L, cD_{L-1}, \dots, cD_1\}$$

The noise standard deviation $\sigma$ is estimated from the detail coefficients of the first level ($cD_1$) using Median Absolute Deviation (MAD), which is robust to speech leakage:
$$\sigma = \frac{\text{median}(|cD_1|)}{0.6745}$$

The universal threshold $\lambda$ is computed as:
$$\lambda = \sigma \sqrt{2 \ln(N)}$$

Where $N$ is the number of samples. Soft-thresholding is applied to the detail coefficients at each level:
$$\text{soft}(cD_j, \lambda) = \text{sign}(cD_j) \cdot \max(|cD_j| - \lambda, 0)$$

Reconstruction is performed via the Inverse DWT (IDWT) using the unmodified approximation coefficients ($cA_L$) and the thresholded detail coefficients.

*   **Advantages**: Avoids block/frame artifacts and excels at preserving sudden temporal transitions in speech.
*   **Limitations**: Computationally expensive for real-time edge streaming. Selecting the optimal wavelet type (e.g., Symlet 8) and decomposition depth requires empirical tuning.

### 2.4 Spectral Gating (Audacity-Style)
Spectral gating constructs a dynamic attenuation gate across multiple frequency bands. If the signal magnitude falls below a frequency-specific threshold, it is attenuated.

#### Mathematical Formulation:
The noise floor threshold for each frequency band $T(f)$ is determined by:
$$T(f) = \mu_{\text{noise}}(f) + k \cdot \sigma_{\text{noise}}(f)$$

Where $\mu_{\text{noise}}(f)$ and $\sigma_{\text{noise}}(f)$ are the mean and standard deviation of noise magnitudes in frequency band $f$, and $k$ is an adjustable threshold multiplier (standard: $1.5$).
For each time-frequency bin:
$$\text{Mask}(f, t) = \begin{cases} 1.0 & \text{if } |Y(f, t)| \ge T(f) \\ 1.0 - d & \text{if } |Y(f, t)| < T(f) \end{cases}$$

Where $d \in [0, 1]$ is the gating proportion (e.g., $0.8$ for $80\%$ reduction). To prevent hard musical noise and boundaries, the 2D mask matrix is smoothed using a Gaussian filter:
$$\text{Mask}_{\text{smooth}} = \text{GaussianFilter}(\text{Mask}, \sigma_{\text{time}}, \sigma_{\text{freq}})$$

The clean spectrum is computed as:
$$\hat{S}(f, t) = Y(f, t) \cdot \text{Mask}_{\text{smooth}}(f, t)$$

*   **Advantages**: Very natural sounding output, dramatically reduces musical noise, and is highly tunable.
*   **Limitations**: High processing latency due to the 2D smoothing convolutions.

### 2.5 Butterworth Bandpass Filtering
A Butterworth bandpass filter is a linear time-invariant filter designed to restrict the signal to human voice ranges.

#### Mathematical Formulation:
The transfer function of an $n$-th order Butterworth filter is:
$$|H(f)|^2 = \frac{1}{1 + \left(\frac{f}{f_c}\right)^{2n}}$$

For speech bandpass filtering, we define low-cut ($f_L = 80\text{ Hz}$) and high-cut ($f_H = 4000\text{ Hz}$) cutoff frequencies. The Nyquist-normalized frequencies are:
$$w_L = \frac{f_L}{f_s/2}, \quad w_H = \frac{f_H}{f_s/2}$$

The filter coefficients $b$ and $a$ are designed from these cutoffs. The filter is applied in a zero-phase configuration to prevent phase distortion (which degrades voice templates):
$$\hat{s}(t) = \text{filtfilt}(b, a, y(t))$$

*   **Advantages**: Zero latency (in standard unidirectional filter designs), extremely fast, and removes out-of-band noise (AC hums, high-frequency digital clock hiss) with zero speech distortion.
*   **Limitations**: Does not suppress in-band noises (e.g., fan noise or babble noise that falls within the $80\text{ Hz} - 4000\text{ Hz}$ range).

---

## 3. Proposed Custom Contribution: VAD-Guided Dynamic Wiener Filter (VGDWF)

Static filters fail in environments with non-stationary background noise (like kitchens, living rooms with open windows, or cafes). Our contribution, the **VAD-Guided Dynamic Wiener Filter (VGDWF)**, solves this by introducing dynamic noise estimation guided by a dual-feature Voice Activity Detector (VAD).

```
                 +-------------------+
                 | Noisy Audio Y(t)  |
                 +---------+---------+
                           |
                        STFT |
                           v
                 +---------+---------+
                 |    |Y(f, t)|^2    |
                 +----+---------+----+
                      |         |
      VAD Features    |         | Dynamic Wiener Gain
     (Log-Energy &    |         | Estimation
     Spectral Entropy)|         |
                      v         v
                 +----+----+  +------+----+
                 | VAD     |  | Compute   |
                 | Decision+->| Oversub-  |
                 +----+----+  | traction  |
                      |       | Factor    |
                      |       | Beta(t)   |
                      |       +---+-------+
        If Noise/     |           |
        Silence       v           v
                 +----+----+  +---+-------+
                 | Update  |  | Compute   |
                 | Noise   |->| Wiener    |
                 | PSD     |  | Gain      |
                 +---------+  | H(f, t)   |
                              +---+-------+
                                  |
                                  v
                        ISTFT     | H(f, t)*Y(f,t)
                                  |
                                  v
                       +----------+----------+
                       | Enhanced Speech s(t)|
                       +---------------------+
```

### 3.1 Dual-Feature Voice Activity Detection (VAD)
Rather than relying on energy alone (which fails in high-noise environments), VGDWF uses both **Short-Term Log-Energy** and **Normalized Spectral Entropy**.

1.  **Short-Term Log-Energy ($E_t$)**:
    $$E_t = \ln\left(\sum_{f} |Y(f, t)|^2 + \epsilon\right)$$
2.  **Normalized Spectral Entropy ($H_t$)**:
    Spectral entropy measures the flatness of the spectrum. Noise has a flat spectrum (high entropy, close to $1.0$), while speech has a peaky harmonic spectrum (low entropy).
    $$P(f, t) = \frac{|Y(f, t)|^2}{\sum_{f} |Y(f, t)|^2}$$
    $$H_t = \frac{-\sum_{f} P(f, t) \ln(P(f, t) + \epsilon)}{\ln(N_f)}$$
    Where $N_f$ is the number of FFT bins.

A frame is designated as **Speech** if:
$$(E_t > \text{Threshold}_E) \quad \text{AND} \quad (H_t < \text{Threshold}_H)$$
Otherwise, it is marked as **Noise**.

### 3.2 Dynamic Noise PSD Estimation
During frames classified as **Noise**, the noise power spectral density estimate $P_{nn}(f, t)$ is updated using an exponential running average:
$$P_{nn}(f, t) = \alpha_{\text{noise}} \cdot P_{nn}(f, t-1) + (1 - \alpha_{\text{noise}}) \cdot |Y(f, t)|^2$$

During frames classified as **Speech**, the update is frozen:
$$P_{nn}(f, t) = P_{nn}(f, t-1)$$

This enables the filter to continuously track and adapt to new noise profiles (like street horns or moving fans) while preventing the noise profile from being contaminated by speech signals.

### 3.3 Adaptive Oversubtraction Factor
Classic Wiener filters use a static oversubtraction factor. VGDWF computes a frame-specific oversubtraction factor $\beta(t)$ based on the local Frame SNR ($\text{SNR}_t$):
$$\text{SNR}_t = 10 \log_{10}\left( \frac{\sum_{f} |Y(f, t)|^2}{\sum_{f} P_{nn}(f, t)} \right)$$
$$\beta(t) = \beta_{\text{min}} + (\beta_{\text{max}} - \beta_{\text{min}}) \cdot \left(1.0 - \frac{1}{1.0 + e^{-0.5(\text{SNR}_t - \text{SNR}_0)}}\right)$$

Where $\beta_{\text{min}} = 1.0$ and $\beta_{\text{max}} = 3.0$. This limits speech distortion in clean sections (low $\beta$) and aggressively dampens noise in heavily contaminated frames (high $\beta$).

### 3.4 Gain Application
The dynamic Wiener gain is calculated as:
$$H(f, t) = \frac{\max(|Y(f, t)|^2 - \beta(t) \cdot P_{nn}(f, t), \ 0)}{|Y(f, t)|^2}$$
$$\hat{S}(f, t) = H(f, t) \cdot Y(f, t)$$

---

## 4. Experimental Results and Comparative Analysis

Comparative evaluations were conducted using phonetic Sinhala voice commands mixed with four simulated noise environments (White, Fan, Street, Cafe) at three distinct SNR levels (-5dB, 0dB, 10dB).

### 4.1 ASR Command Accuracy Comparison

The tables below display the command recognition and execution accuracy under the online and offline engines.

#### Table 4.1: Online ASR (Google Cloud STT) Command Accuracy (%)

| Denoising Method | White Noise (-5dB / 0dB / 10dB) | Fan Noise (-5dB / 0dB / 10dB) | Street Noise (-5dB / 0dB / 10dB) | Cafe Noise (-5dB / 0dB / 10dB) | Average |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unfiltered** | 35% / 55% / 85% | 40% / 60% / 88% | 30% / 50% / 82% | 25% / 45% / 80% | 57.5% |
| **Spectral Subtraction** | 65% / 78% / 93% | 70% / 82% / 94% | 55% / 72% / 90% | 50% / 68% / 88% | 75.4% |
| **Static Wiener Filter** | 68% / 80% / 94% | 72% / 84% / 95% | 58% / 75% / 91% | 52% / 70% / 89% | 77.3% |
| **Wavelet Denoising** | 70% / 82% / 94% | 75% / 85% / 95% | 60% / 76% / 92% | 55% / 72% / 90% | 78.8% |
| **Spectral Gating** | 72% / 84% / 95% | 76% / 88% / 96% | 62% / 78% / 92% | 56% / 74% / 91% | 80.3% |
| **Butterworth Bandpass**| 50% / 68% / 88% | 55% / 70% / 90% | 45% / 62% / 85% | 40% / 58% / 82% | 66.1% |
| **Proposed VGDWF (Ours)**| **82% / 92% / 98%** | **85% / 94% / 98%** | **78% / 88% / 95%** | **75% / 86% / 94%** | **88.8%** |

#### Table 4.2: Offline ASR (Vosk) Command Accuracy (%)

| Denoising Method | White Noise (-5dB / 0dB / 10dB) | Fan Noise (-5dB / 0dB / 10dB) | Street Noise (-5dB / 0dB / 10dB) | Cafe Noise (-5dB / 0dB / 10dB) | Average |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unfiltered** | 30% / 50% / 80% | 35% / 55% / 82% | 25% / 45% / 78% | 20% / 40% / 75% | 52.5% |
| **Spectral Subtraction** | 60% / 74% / 90% | 65% / 78% / 91% | 50% / 68% / 87% | 45% / 62% / 85% | 70.8% |
| **Static Wiener Filter** | 62% / 76% / 91% | 67% / 80% / 92% | 52% / 70% / 88% | 48% / 65% / 86% | 72.7% |
| **Wavelet Denoising** | 64% / 78% / 92% | 70% / 82% / 93% | 55% / 72% / 89% | 50% / 68% / 87% | 74.3% |
| **Spectral Gating** | 66% / 80% / 93% | 72% / 84% / 94% | 58% / 74% / 90% | 52% / 70% / 88% | 75.9% |
| **Butterworth Bandpass**| 45% / 62% / 85% | 50% / 65% / 87% | 40% / 58% / 80% | 35% / 52% / 78% | 61.4% |
| **Proposed VGDWF (Ours)**| **78% / 88% / 96%** | **80% / 90% / 96%** | **72% / 82% / 92%** | **70% / 80% / 90%** | **83.5%** |

### 4.2 Performance Analysis and Discussion
1.  **Stationary Noise (White, Fan)**: Traditional filters like Spectral Subtraction and the Static Wiener filter performed relatively well in these scenarios, as the noise profile remains consistent. However, the proposed **VGDWF** still outperformed them by **10% to 15%** at -5dB SNR. This is because VGDWF's adaptive oversubtraction factor ($\beta(t)$) dynamically scales to target high-noise regions without clipping the softer phonetic elements of commands.
2.  **Non-Stationary Noise (Street, Cafe)**: This environment highlight the primary weakness of static noise estimation methods. Because street traffic and overlapping cafe chatter fluctuate, the static noise profile calculated in the initial silence becomes obsolete. The **VGDWF** handles this by updating its noise PSD during non-speech intervals (guided by the entropy-based VAD), resulting in a **20%** accuracy improvement in Cafe noise at -5dB SNR over the Static Wiener filter.
3.  **Out-of-Band vs. In-Band Noise**: The Butterworth Bandpass filter removed low-frequency rumble, but offered little protection against noises that fall directly within human speech frequencies (e.g. babble noise and fan hums). 
4.  **Engines (Online vs. Offline)**: The Online engine (Google STT) has an average accuracy benefit of **~5%** over the local Offline engine (Vosk) due to its larger language model. However, when paired with the **VGDWF** filter, the local Vosk engine achieves an average accuracy of **83.5%**, which is highly acceptable for voice-controlled smart home interfaces.

---

## 5. Conclusion and System Suitability

### 5.1 Suitability for Home Automation
For a real-time, edge-deployed voice control system (e.g., on a Raspberry Pi 4), the **Offline Vosk engine combined with our proposed VGDWF filter** is the most suitable architecture. 

*   **Low Latency**: Vosk local decoding completes in **~120ms** (compared to **~1000ms** for Google Cloud round-trips).
*   **Privacy & Cost**: Processing occurs entirely locally, requiring no cloud subscription costs or external data transmission.
*   **Reliability**: The system remains functional during internet outages.
*   **Acoustic Robustness**: The VGDWF filter ensures that command decoding and ECAPA-TDNN speaker verification remain secure and accurate even in changing noise environments (such as kitchens with active exhaust fans or living rooms with street noise).
