import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt

print("Loading data...")
data = np.load('/home/ethant/Projects/lagrnge/noaa_recording.npy')

# Sample rate from the SDR configuration
sample_rate = 1_000_000  # 1 MSPS

print("FM Demodulation...")
# FM Demodulation: phase difference between adjacent samples
fm_demod = np.angle(data[1:] * np.conj(data[:-1]))

print("Decimation...")
# Decimate down to a manageable audio sample rate, e.g., 40 kHz (1M / 25)
decimation_factor = 25
audio_rate = sample_rate // decimation_factor
fm_audio = signal.decimate(fm_demod, decimation_factor)

print("AM Demodulation (Envelope Detection)...")
# APT is AM modulated on a 2400 Hz subcarrier.
am_demod = np.abs(fm_audio)

# Low-pass filter to extract the image envelope (max component is ~2080 Hz)
nyq = audio_rate / 2.0
b, a = signal.butter(4, 2080.0 / nyq, btype='low')
envelope = signal.filtfilt(b, a, am_demod)

print("Formatting image...")
# NOAA APT transmits 2 lines per second, 2080 pixels per line (4160 pixels/sec total).
# We resample our audio-rate envelope exactly to 4160 Hz to match 1 pixel = 1 sample.
target_rate = 4160 
num_samples = int(len(envelope) * target_rate / audio_rate)
pixels = signal.resample(envelope, num_samples)

# Normalize pixel values
pixels = pixels - np.min(pixels)
pixels = pixels / (np.max(pixels) + 1e-6)

# Reshape into an image where each row is 2080 pixels
lines = len(pixels) // 2080
image_data = pixels[:lines * 2080].reshape((lines, 2080))

print(f"Generated {lines} lines of image data.")

# Save the image
plt.figure(figsize=(10, 10))
plt.imshow(image_data, cmap='gray', aspect='auto')
plt.title('Decoded NOAA APT Image')
plt.axis('off')
plt.tight_layout()
plt.savefig('noaa_output.png', dpi=300)
print("Saved image to noaa_output.png")
