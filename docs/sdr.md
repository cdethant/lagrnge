# Adalm Pluto+ SDR Setup Guide

This guide covers how to physically set up your Adalm Pluto+ Software Defined Radio and run a simple TX/RX test using Docker on the Lagrnge server.

## 1. Physical Setup

1. **Antennas**: Attach your antennas to the appropriate SMA ports on the Pluto+. Make sure to connect one to a TX (Transmit) port and one to an RX (Receive) port.
2. **Data Connection**: Use a high-quality USB Type-C cable to connect the Pluto+'s middle data port to one of the USB 3.0 (blue) ports on your Raspberry Pi.
3. **Power**: The Pluto+ typically draws more power than a standard USB port can reliably provide during heavy TX. Connect a separate power supply (5V/2A minimum) to the dedicated Power-only USB-C port on the side of the Pluto+.
4. **Boot Up**: Wait for the Pluto+ to initialize. The LED indicator should stop flashing and remain solid when it is ready.

## 2. Host Verification

By default, the Adalm Pluto+ creates a network-over-USB interface (usually configured to `192.168.2.1`).

On your Lagrnge host, verify the connection:
```bash
# Check if the USB device is recognized
lsusb | grep "Analog Devices"

# Check if the network interface was created and ping it
ping -c 4 192.168.2.1
```

## 3. Docker TX/RX Test

To send a simple TX/RX through the SDR, we'll use a Docker container with the necessary IIO (Industrial I/O) utilities and Python bindings pre-installed, such as `radioconda`. 

*(Note: The `lagrnge` repository structure here differs from the absolute `/data/...` partition setup described in your Docker configuration guide. We will mount your current working directory instead).*

### Build the Radioconda Image

As there is no official pre-built `radioconda` image on Docker Hub, you first need to build it directly on the Lagrnge host (e.g., your Raspberry Pi) using the provided `Dockerfile`. This Dockerfile will download and install the aarch64 version of Radioconda.

```bash
# Build the Docker image natively on the host
docker build -t radioconda_local -f sdr/DockerFile .
```

### Create and Upload the Test Script

First, create a simple Python test script in your project directory (e.g., `sdr/hello_world.py`).

If you are developing locally and the SDR is connected to a remote host (like a Raspberry Pi), you can upload the script via SSH using `rsync` (available via WSL or Git Bash on Windows):

```bash
# Upload hello_world.py to the Lagrnge host
rsync -avz sdr/hello_world.py user@<REMOTE_IP>:/path/to/lagrnge/sdr/
```

Example `sdr/hello_world.py` script:

```python
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
```

### Run the Docker Container

Since the Pluto+ communicates via an IP address on its virtual USB network interface (`192.168.2.1`), we give the container access to the host's networking. We will use the `radioconda_local` image you just built, which includes Native GNU Radio, `pyadi-iio`, and all the required C libraries.

Run the container from your project directory:

```bash
docker run -it --rm \
  --network host \
  -v $(pwd):/workspace \
  -w /workspace \
  radioconda_local \
  python sdr/hello_world.py
```

**What this does:**
1. `--network host`: Allows the container to communicate with the Pluto+ on `192.168.2.1` seamlessly, leveraging the host Pi's routing table.
2. `-v $(pwd):/workspace`: Mounts your current Lagrnge project repository—where you created `sdr/hello_world.py`—into the container at `/workspace`.
3. `-w /workspace`: Sets the current directory inside the container.
4. `python sdr/hello_world.py`: Runs your test script using Radioconda's robust preset python environment.

If successful, you will see the script transmit a tone, pull the buffer, and print out complex data points, confirming the SDR hardware and Docker stack are successfully connected!
