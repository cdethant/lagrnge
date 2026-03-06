import adi
import time
import numpy as np

# Connect to the PlutoSDR over its default IP
sdr = adi.Pluto("ip:192.168.2.1")

# Configure SDR properties
sdr.sample_rate = int(2.5e6)
sdr.tx_rf_bandwidth = int(1e6)
sdr.tx_lo = int(2.4e9)
sdr.tx_hardwaregain_chan0 = -20

sdr.rx_lo = int(2.4e9)
sdr.rx_rf_bandwidth = int(1e6)
sdr.rx_buffer_size = 1000
sdr.gain_control_mode_chan0 = "manual"
sdr.rx_hardwaregain_chan0 = 20

# Create a simple sine wave for TX
fs = sdr.sample_rate
fc = 100000  # 100 kHz offset
N = 1000
t = np.arange(N) / fs
samples = 0.5 * np.exp(2.0j * np.pi * fc * t)
samples *= 2**14 # Scale to 16-bit range

print("Transmitting signal...")
sdr.tx_cyclic_buffer = True # Transmit continuously
sdr.tx(samples)

time.sleep(2) # Give the SDR a moment to start looping the TX

print("Receiving signal...")
rx_data = sdr.rx()

print(f"Received {len(rx_data)} complex samples.")
print(f"Sample preview: {rx_data[:5]}")

# Clean up
sdr.tx_destroy_buffer()
print("TX/RX Test Complete.")