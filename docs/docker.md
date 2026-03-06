# Docker Configuration on Lagrnge

Lagrnge is designed to host a massive Docker ecosystem for signal processing, AI agent fine-tuning, network backends, and databases. Because these workloads are extremely disk-intensive and generate massive amounts of small files, we engineered the 450GB `/data` partition to use `btrfs` compression. 

To take full advantage of this, we need to completely migrate Docker's default installation (which usually lives in `/var/lib/docker` on your small `ext4` root partition) over to the BTRFS `/data` partition.

## Step 1: Install Docker natively

If you haven't already, install Docker and the necessary BTRFS utilities:
```bash
# Update and install dependencies
sudo apt-get update
sudo apt-get install btrfs-progs

# Download and run the official convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add yourself to the docker group so you don't need sudo
sudo usermod -aG docker $USER
```
*(Remember to log out and log back in for the group change to take effect).*

## Step 2: Stop the Docker Service

Before we move its brain, we need to shut Docker down completely:
```bash
sudo systemctl stop docker
sudo systemctl stop docker.socket
```

## Step 3: Configure the Daemon for BTRFS and `/data`

Docker stores all of its images, container layers, and volumes in the "Data Root". We want to instruct Docker to use `/data/docker` instead of the root drive, and definitively tell it to use the `btrfs` storage driver (which handles snapshotting and layering perfectly).

Create or edit the Docker configuration file:
```bash
sudo nano /etc/docker/daemon.json
```

Add the following JSON configuration:
```json
{
  "data-root": "/data/docker",
  "storage-driver": "btrfs",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "20m",
    "max-file": "3"
  }
}
```
*Note: I also added `log-opts` to prevent runaway container logs from filling up your drive over time. It limits each container to keeping exactly three 20MB log files.*

## Step 4: Create the Directory Structure and Start Docker

Since we just told Docker to live in `/data/docker`, let's migrate any existing data and create our overarching directory structure!

```bash
# Migrate existing Docker data (if any) to the new location
sudo rsync -aP /var/lib/docker/ /data/docker/

# Create project-specific volume directories for your stack
sudo mkdir -p /data/sdr         # Signal processing data
sudo mkdir -p /data/agents      # AI fine-tuning & checkpoints
sudo mkdir -p /data/network     # Network backend volumes

sudo chown -R root:root /data/docker
```

Now, start Docker back up:
```bash
sudo systemctl start docker
```

## Step 5: Verify the Configuration

To double-check that Docker is securely using your `/data` partition and the BTRFS driver, run:
```bash
docker info | grep -E 'Storage Driver|Docker Root Dir'
```

It should return:
```plaintext
 Storage Driver: btrfs
 Docker Root Dir: /data/docker
```

## Why this architecture?
By pointing the Docker root strictly to `/data/docker`, every single Docker image you pull (PyTorch, SDR toolkits, network backends) will permanently reside on the 450GB side of your SSD. Furthermore, the `btrfs` storage driver allows Docker to instantly spin up hundreds of identical containers for your signal processing and agent networks using Copy-on-Write (zero space duplication), while BTRFS transparently compresses everything in the background via `compress=zstd`!
