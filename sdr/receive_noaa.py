import adi
import time
import numpy as np

# This script configures the Adalm Pluto+ as a receiver only,
# specifically tuned to the NOAA-19 weather satellite broadcast frequency (137.100 MHz).
# It will record 10 seconds of raw IQ data to save locally for later processing.

# Connect to the PlutoSDR over its default IP
# Ensure you are connected to the SDR before running this!
print("Connecting to PlutoSDR...")
sdr = adi.Pluto("ip:192.168.2.1")

# Configure SDR properties for receiving NOAA APT (Automatic Picture Transmission)
# 137.1 MHz is NOAA-19. (NOAA-15 is 137.62 MHz, NOAA-18 is 137.9125 MHz)
freq_hz = int(137.1e6) 
sample_rate_hz = int(1e6) # 1 MSPS is plenty for the ~40 kHz FM bandwidth

print(f"Configuring receiver for {freq_hz / 1e6} MHz...")
sdr.sample_rate = sample_rate_hz
sdr.rx_lo = freq_hz
sdr.rx_rf_bandwidth = int(1e6)   # Filter bandwidth 
sdr.rx_buffer_size = 100000      # Receive large chunks per buffer
sdr.gain_control_mode_chan0 = "manual"
sdr.rx_hardwaregain_chan0 = 64   # Add some gain; pulling signals from space requires it!

# Disable TX entirely to be safe
sdr.tx_rf_bandwidth = int(1e6) 
sdr.tx_lo = int(2.4e9)
sdr.tx_hardwaregain_chan0 = -80  # Minimum gain possible
sdr.tx_destroy_buffer()

duration_seconds = 10
total_samples_needed = sample_rate_hz * duration_seconds
recorded_data = []

print(f"Starting to record {duration_seconds} seconds of data...")
samples_collected = 0

start_time = time.time()

# Loop until we have gathered the required amount of data
while samples_collected < total_samples_needed:
    # Pull an array of complex samples from the SDR
    rx_data = sdr.rx()
    recorded_data.append(rx_data)
    samples_collected += len(rx_data)
    
    # Calculate live signal power (Root Mean Square)
    # The higher this value, the stronger the signal (or noise floor)
    rms_power = np.sqrt(np.mean(np.square(np.abs(rx_data))))
    
    # Optional print to show progress and signal strength
    elapsed = time.time() - start_time
    print(f"\r{(samples_collected/total_samples_needed)*100:.1f}% ({elapsed:.1f}s) | Signal Power (RMS): {rms_power:.4f}", end="")

print("\nRecording complete! Formatting data...")

# Concatenate all buffers into one large 1D numpy array
full_recording = np.concatenate(recorded_data)

# Trim if we slightly overshot the sample count
full_recording = full_recording[:total_samples_needed] 

filename = "noaa_recording.npy"
print(f"Saving raw IQ data to {filename} ({len(full_recording)} complex samples)...")
np.save(filename, full_recording)

print("Done. Decode this baseband file using a workflow like GNU Radio or SDRangel.")
