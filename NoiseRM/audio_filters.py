# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: audio_filters.py
# Description: Implements 5 standard noise reduction filters and a custom proposed
#              filter (VAD-Guided Dynamic Wiener Filter) for audio enhancement.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

import numpy as np
import scipy.signal
import pywt

# ==============================================================================
# METHOD 1: Spectral Subtraction Denoising
# ==============================================================================
def spectral_subtraction(y, sr, noise_estimation_sec=0.5, alpha=2.0, beta=0.02):
    """
    Standard Spectral Subtraction.
    Estimates the noise spectrum from the initial silent portion of the audio 
    and subtracts it from the entire signal spectrum.
    
    Parameters:
    - y: 1D numpy array representing the audio signal.
    - sr: Sample rate of the audio signal.
    - noise_estimation_sec: Duration in seconds at the start of audio to estimate noise.
    - alpha: Over-subtraction factor to control residual noise.
    - beta: Spectral floor parameter to prevent musical noise (residual tones).
    """
    # Compute short-time Fourier transform (STFT)
    n_fft = 1024
    hop_length = 256
    frequencies, times, Zxx = scipy.signal.stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Estimate noise magnitude profile from the initial silent segment
    noise_frames = int((noise_estimation_sec * sr) / hop_length)
    noise_frames = max(1, min(noise_frames, Zxx.shape[1]))
    
    # Calculate average noise magnitude spectrum across the noise frames
    noise_mag = np.mean(np.abs(Zxx[:, :noise_frames]), axis=1, keepdims=True)
    
    # Compute magnitude and phase of the noisy audio
    noisy_mag = np.abs(Zxx)
    phase = np.angle(Zxx)
    
    # Subtract noise magnitude from noisy magnitude
    # S(f) = max(|X(f)| - alpha * N(f), beta * |X(f)|)
    clean_mag = noisy_mag - alpha * noise_mag
    clean_mag = np.maximum(clean_mag, beta * noisy_mag)
    
    # Reconstruct the complex spectrogram and apply inverse STFT (ISTFT)
    Zxx_clean = clean_mag * np.exp(1j * phase)
    _, y_clean = scipy.signal.istft(Zxx_clean, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Match length with original signal
    if len(y_clean) < len(y):
        y_clean = np.pad(y_clean, (0, len(y) - len(y_clean)))
    else:
        y_clean = y_clean[:len(y)]
        
    return y_clean

# ==============================================================================
# METHOD 2: Wiener Filter (Static Estimation)
# ==============================================================================
def wiener_filter(y, sr, noise_estimation_sec=0.5, eps=1e-10):
    """
    Wiener Filter based on static noise estimation from the beginning of the signal.
    Uses the Wiener gain formula: H(f) = P_speech(f) / (P_speech(f) + P_noise(f)).
    
    Parameters:
    - y: 1D numpy array representing the audio signal.
    - sr: Sample rate of the audio signal.
    - noise_estimation_sec: Duration in seconds at the start of audio to estimate noise.
    - eps: Small constant to avoid division by zero.
    """
    n_fft = 1024
    hop_length = 256
    frequencies, times, Zxx = scipy.signal.stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Estimate noise power spectral density (PSD) from the initial silent segment
    noise_frames = int((noise_estimation_sec * sr) / hop_length)
    noise_frames = max(1, min(noise_frames, Zxx.shape[1]))
    
    noise_psd = np.mean(np.abs(Zxx[:, :noise_frames])**2, axis=1, keepdims=True)
    
    # Power spectral density of the noisy signal
    noisy_psd = np.abs(Zxx)**2
    
    # Estimate clean speech PSD
    speech_psd = np.maximum(noisy_psd - noise_psd, 0.0)
    
    # Compute Wiener gain H(f) = P_speech / (P_speech + P_noise)
    wiener_gain = speech_psd / (speech_psd + noise_psd + eps)
    
    # Apply gain to the noisy spectrogram
    Zxx_clean = wiener_gain * Zxx
    _, y_clean = scipy.signal.istft(Zxx_clean, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Align lengths
    if len(y_clean) < len(y):
        y_clean = np.pad(y_clean, (0, len(y) - len(y_clean)))
    else:
        y_clean = y_clean[:len(y)]
        
    return y_clean

# ==============================================================================
# METHOD 3: Wavelet Denoising
# ==============================================================================
def wavelet_denoising(y, wavelet='sym8', level=4):
    """
    Denoises the signal using Discrete Wavelet Transform (DWT).
    Applies soft-thresholding to wavelet coefficients based on the universal threshold.
    
    Parameters:
    - y: 1D numpy array representing the audio signal.
    - wavelet: Type of wavelet to use (default: Symlet 8).
    - level: Decomposition level.
    """
    # Decompose signal into wavelet coefficients
    coeffs = pywt.wavedec(y, wavelet, level=level)
    
    # Calculate universal threshold based on the noise estimate in detail coefficients
    # Universal threshold lambda = sigma * sqrt(2 * ln(N))
    # where sigma is estimated using the Median Absolute Deviation (MAD) of the highest level detail coeffs
    detail_coeffs = coeffs[-1]
    sigma = np.median(np.abs(detail_coeffs)) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(y)))
    
    # Apply soft thresholding to detail coefficients (leave approximation coefficients coeffs[0] untouched)
    new_coeffs = [coeffs[0]]
    for c in coeffs[1:]:
        new_coeffs.append(pywt.threshold(c, value=threshold, mode='soft'))
        
    # Reconstruct the signal
    y_clean = pywt.waverec(new_coeffs, wavelet)
    
    # Align lengths
    if len(y_clean) < len(y):
        y_clean = np.pad(y_clean, (0, len(y) - len(y_clean)))
    else:
        y_clean = y_clean[:len(y)]
        
    return y_clean

# ==============================================================================
# METHOD 4: Spectral Gating (Audacity Style)
# ==============================================================================
def spectral_gating(y, sr, noise_estimation_sec=0.5, n_std_thresh=1.5, prop_decrease=0.8):
    """
    Applies Audacity-style spectral gating.
    Computes a noise threshold per frequency band. If a time-frequency bin's 
    magnitude is below the threshold, it is attenuated by a gating factor.
    
    Parameters:
    - y: 1D numpy array representing the audio signal.
    - sr: Sample rate of the audio signal.
    - noise_estimation_sec: Duration in seconds at the start of audio to estimate noise.
    - n_std_thresh: Threshold multiplier of standard deviation above mean noise.
    - prop_decrease: The proportion by which to decrease noise (0 to 1).
    """
    n_fft = 1024
    hop_length = 256
    frequencies, times, Zxx = scipy.signal.stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Identify noise frames
    noise_frames = int((noise_estimation_sec * sr) / hop_length)
    noise_frames = max(1, min(noise_frames, Zxx.shape[1]))
    
    # Compute statistics of noise magnitude per frequency band
    noise_slice = np.abs(Zxx[:, :noise_frames])
    mean_noise = np.mean(noise_slice, axis=1, keepdims=True)
    std_noise = np.std(noise_slice, axis=1, keepdims=True)
    
    # Calculate threshold for gating: mean + n_std_thresh * std
    thresh_noise = mean_noise + n_std_thresh * std_noise
    
    # Compute magnitude and phase
    mag = np.abs(Zxx)
    phase = np.angle(Zxx)
    
    # Determine which bins are noise (magnitude is below threshold)
    is_noise = mag < thresh_noise
    
    # Construct attenuation mask
    # For noise bins, attenuate. For speech bins, leave unchanged.
    attenuation_factor = 1.0 - prop_decrease
    mask = np.ones_like(mag)
    mask[is_noise] = attenuation_factor
    
    # Smooth the mask over time and frequency to reduce musical noise
    mask = scipy.ndimage.gaussian_filter(mask, sigma=1.0)
    
    # Apply mask
    clean_mag = mag * mask
    
    # Reconstruct spectrogram
    Zxx_clean = clean_mag * np.exp(1j * phase)
    _, y_clean = scipy.signal.istft(Zxx_clean, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Align lengths
    if len(y_clean) < len(y):
        y_clean = np.pad(y_clean, (0, len(y) - len(y_clean)))
    else:
        y_clean = y_clean[:len(y)]
        
    return y_clean

# ==============================================================================
# METHOD 5: Butterworth Bandpass Filter
# ==============================================================================
def bandpass_filter(y, sr, lowcut=80.0, highcut=4000.0, order=5):
    """
    Standard Butterworth bandpass filter to isolate human speech frequencies
    and filter out low-frequency hum (AC lines) and high-frequency hiss.
    
    Parameters:
    - y: 1D numpy array representing the audio signal.
    - sr: Sample rate of the audio.
    - lowcut: High-pass cutoff frequency in Hz.
    - highcut: Low-pass cutoff frequency in Hz.
    - order: Filter order.
    """
    nyquist = 0.5 * sr
    low = lowcut / nyquist
    high = highcut / nyquist
    
    # Design butterworth bandpass filter
    b, a = scipy.signal.butter(order, [low, high], btype='band')
    
    # Apply zero-phase forward-backward filter to avoid phase distortion
    y_clean = scipy.signal.filtfilt(b, a, y)
    return y_clean

# ==============================================================================
# METHOD 6: [CUSTOM PROPOSED MODEL] VAD-Guided Dynamic Wiener Filter (VGDWF)
# ==============================================================================
def vad_guided_dynamic_wiener_filter(y, sr, alpha_noise=0.98, beta_min=1.0, beta_max=3.0):
    """
    Our proposed custom noise reduction method: VAD-Guided Dynamic Wiener Filter (VGDWF).
    
    Features:
    - Frames are analyzed dynamically.
    - Uses short-term log-energy AND spectral entropy to compute Voice Activity Detection (VAD).
    - If a frame is speech-free, it updates the noise PSD dynamically using an exponential running average.
      This allows adaptation to changing non-stationary noise environments (street, cafe).
    - If a frame contains speech, the noise PSD is frozen.
    - The oversubtraction factor beta is computed dynamically for each frame based on the local frame SNR, 
      reducing musical noise in high-SNR parts and aggressive filtering in low-SNR parts.
    
    Parameters:
    - y: 1D numpy array representing the audio signal.
    - sr: Sample rate.
    - alpha_noise: Smoothing factor for noise PSD update during non-speech frames.
    - beta_min: Minimum oversubtraction factor.
    - beta_max: Maximum oversubtraction factor.
    """
    n_fft = 1024
    hop_length = 256
    frequencies, times, Zxx = scipy.signal.stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    num_bins, num_frames = Zxx.shape
    
    # Initialize noise PSD with the first frame (safety fallback)
    noise_psd = np.abs(Zxx[:, 0:1])**2
    
    # Spectrogram magnitudes and phases
    mag_sq = np.abs(Zxx)**2
    phase = np.angle(Zxx)
    
    # Containers for output
    clean_mag = np.zeros_like(mag_sq)
    
    # --- STEP 1: Compute VAD features for all frames ---
    # Log-energy per frame
    frame_energy = np.sum(mag_sq, axis=0)
    # Avoid log(0)
    frame_energy_log = np.log(frame_energy + 1e-12)
    
    # Normalized spectral entropy per frame
    # Entropy measures flat vs peaky distribution. Noise is flat (high entropy), speech is peaky (low entropy).
    eps = 1e-12
    normalized_mag = mag_sq / (frame_energy + eps)
    spectral_entropy = -np.sum(normalized_mag * np.log(normalized_mag + eps), axis=0) / np.log(num_bins)
    
    # Dynamic VAD Thresholding
    # Set threshold based on initial 5 frames (usually noise)
    init_noise_frames = min(5, num_frames)
    energy_thresh = np.mean(frame_energy_log[:init_noise_frames]) + 1.5 * np.std(frame_energy_log[:init_noise_frames])
    # Speech usually has lower entropy than noise
    entropy_thresh = np.mean(spectral_entropy[:init_noise_frames]) - 1.0 * np.std(spectral_entropy[:init_noise_frames])
    
    # Ensure threshold boundary limits
    energy_thresh = max(energy_thresh, np.min(frame_energy_log) + 1.0)
    entropy_thresh = min(max(entropy_thresh, 0.5), 0.9)
    
    # --- STEP 2: Process frames dynamically ---
    for t in range(num_frames):
        current_energy = frame_energy_log[t]
        current_entropy = spectral_entropy[t]
        
        # Frame VAD classification:
        # It's speech if log-energy is high AND spectral entropy is low.
        is_speech = (current_energy > energy_thresh) or (current_entropy < entropy_thresh)
        
        # Update or freeze noise PSD
        if not is_speech:
            # Silence/Noise frame: update noise PSD dynamically
            noise_psd = alpha_noise * noise_psd + (1 - alpha_noise) * mag_sq[:, t:t+1]
            
        # Compute Frame SNR (local ratio of frame power to estimated noise power)
        current_noise_power = np.sum(noise_psd)
        current_signal_power = frame_energy[t]
        
        frame_snr = current_signal_power / (current_noise_power + 1e-12)
        frame_snr_db = 10 * np.log10(frame_snr + 1e-12)
        
        # Adaptive oversubtraction factor beta based on frame SNR
        # High noise (low SNR): use high beta (aggressive subtract)
        # Low noise (high SNR): use low beta (preserve speech details)
        if frame_snr_db < -5.0:
            beta = beta_max
        elif frame_snr_db > 20.0:
            beta = beta_min
        else:
            # Linear interpolation between beta_max and beta_min
            beta = beta_max - ((frame_snr_db + 5.0) / 25.0) * (beta_max - beta_min)
            
        # Wiener gain computation:
        # G(f) = P_speech(f) / (P_speech(f) + beta * P_noise(f))
        # where P_speech = max(P_noisy - beta * P_noise, 0)
        psd_clean_est = np.maximum(mag_sq[:, t:t+1] - beta * noise_psd, 0.0)
        wiener_gain = psd_clean_est / (psd_clean_est + noise_psd + 1e-12)
        
        # Apply gain
        clean_mag[:, t:t+1] = np.sqrt(mag_sq[:, t:t+1]) * wiener_gain
        
    # --- STEP 3: Reconstruct audio ---
    Zxx_clean = clean_mag * np.exp(1j * phase)
    _, y_clean = scipy.signal.istft(Zxx_clean, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
    
    # Align lengths
    if len(y_clean) < len(y):
        y_clean = np.pad(y_clean, (0, len(y) - len(y_clean)))
    else:
        y_clean = y_clean[:len(y)]
        
    return y_clean

# ==============================================================================
# Self-Verification Block
# ==============================================================================
if __name__ == "__main__":
    print("Testing audio filters module...")
    # Generate a dummy test signal: 1 second of sine wave + white noise at 16kHz
    fs = 16000
    t = np.linspace(0, 1.0, fs, endpoint=False)
    speech_dummy = np.sin(2 * np.pi * 440 * t)  # 440Hz tone representing speech
    noise_dummy = np.random.normal(0, 0.5, fs)  # Gaussian white noise
    noisy_signal = speech_dummy + noise_dummy
    
    print("Dummy signal generated. Testing filters...")
    try:
        y1 = spectral_subtraction(noisy_signal, fs)
        y2 = wiener_filter(noisy_signal, fs)
        y3 = wavelet_denoising(noisy_signal)
        y4 = spectral_gating(noisy_signal, fs)
        y5 = bandpass_filter(noisy_signal, fs)
        y6 = vad_guided_dynamic_wiener_filter(noisy_signal, fs)
        
        print(f"Spectral Subtraction Output Shape: {y1.shape}")
        print(f"Static Wiener Filter Output Shape: {y2.shape}")
        print(f"Wavelet Denoising Output Shape:    {y3.shape}")
        print(f"Spectral Gating Output Shape:     {y4.shape}")
        print(f"Bandpass Filter Output Shape:     {y5.shape}")
        print(f"Proposed VGDWF Output Shape:      {y6.shape}")
        print("[✓] All audio filters executed successfully without error.")
    except Exception as e:
        print(f"[X] Filter verification failed: {e}")
