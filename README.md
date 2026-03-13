# Lagrange - Raspberry Pi Docker Server Stack

Lagrange, the precursor to hamilton, is the hardware layer to the docker ecosystem for signal processing, agent finetuning, and network backend needs of my workflow/tinkering.

## Setting up the hard drive
Lagrnge is designated to operate on btrfs. However, Pi OS requires ext4 for its root, meaning we need to partition the drive 3 ways into fat32, ext4, and btrfs for boot, root, and data.

### Step 1: Flash the Official PiOS Image

Start with a completely clean slate. Download the official Raspberry Pi OS Bookworm 64-bit image. Since the official downloads are compressed (`.img.xz`), we will decompress and write it directly to the SSD in one step.

Identify your drive using `lsblk` (I will use `/dev/sdX` as a placeholder). Make absolutely sure you have the correct drive, as this will wipe it.
```bash
# Decompress and flash the image directly to the SSD
xzcat 2024-03-15-raspios-bookworm-arm64.img.xz | sudo dd of=/dev/sdX bs=4M status=progress
sudo sync
```

### Step 2: Build the Physical Roadblock

Right now, your SSD has a ~500MB FAT32 boot partition (Partition 1) and a ~4GB ext4 root partition (Partition 2). The rest of the 500GB drive is empty space. We need to cap Partition 2 at 50GB and fill the remaining space with Partition 3.
```bash
sudo parted /dev/sdX
```

Inside the `parted` prompt, run the following exact commands to manipulate the MBR table:

1. Type `resizepart 2 50GB` and press Enter. (This moves the boundary of Partition 2 to the 50GB mark, though the filesystem inside remains 4GB for now).
2. Type `mkpart primary btrfs 50GB 100%` and press Enter. (This creates Partition 3, acting as a physical wall that blocks Partition 2 from expanding any further).
3. Type `quit` and press Enter.

Now, expand the filesystem to fill this newly resized 50GB partition:
```bash
# Verify the filesystem is clean
sudo e2fsck -f /dev/sdX2

# Expand the 4GB ext4 filesystem to perfectly fill the 50GB partition
sudo resize2fs /dev/sdX2
```

### Step 3: Format the New Data Partition

Partition 3 now exists in the partition table, but it needs the btrfs filesystem applied to it.
```bash
sudo mkfs.btrfs -f /dev/sdX3
```

### Step 4: Map the Storage in fstab

We need to configure the PiOS root filesystem so it automatically mounts your new `/data` partition every time the Pi boots.

First, fetch the UUID of your new btrfs partition:
```bash
lsblk -f /dev/sdX
```

Copy the UUID for `/dev/sdX3`.

Next, mount the PiOS root and boot partitions to your host machine so you can edit their configuration files:
```bash
sudo mount /dev/sdX2 /mnt
sudo mkdir -p /mnt/data /mnt/boot/firmware
sudo mount /dev/sdX1 /mnt/boot/firmware
```

**Disable the auto-expander**:
Because you manually resized the filesystem on your host machine, the PiOS `init_resize.sh` script will fail since Partition 2 is no longer the last partition on the drive. We need to delete it.
```bash
sudo nano /mnt/boot/firmware/cmdline.txt
```
*Remove the instruction that says `init=/usr/lib/raspi-config/init_resize.sh` entirely from the line.* Save and exit.

**Edit the filesystem table**:
```bash
sudo nano /mnt/etc/fstab
```

You will see the existing `PARTUUID` entries for `/boot/firmware` and `/`. Leave those exactly as they are. Add your new btrfs partition to the bottom of the file:
```plaintext
UUID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy /data   btrfs   rw,relatime,space_cache=v2,compress=zstd 0 0
```
> **Note:** The `compress=zstd` flag is highly recommended. It transparently compresses your Docker logs and SDR data as it writes to the SSD, improving read/write lifespan and saving space with practically zero CPU overhead.

### Step 5: Unmount and First Boot

Safely unmount the SSD from your host machine.
```bash
sudo sync
sudo umount -R /mnt
```

Plug the SSD into your Raspberry Pi 5 and power it on.

Here is what happens under the hood during this first boot: The PiOS bootloader will cleanly read the native MBR partition and boot the kernel. Since you manually expanded the filesystem and removed the auto-expander string, the Pi will boot instantly. It will cleanly mount your pre-expanded 50GB `ext4` root partition and your `btrfs` partition at `/data` directly with zero issues.

### Step 6: Post-Boot BTRFS Maintenance (Mandatory)

Out of the box, Raspberry Pi OS does not include the BTRFS user-space tools. While the kernel can mount the `/data` partition flawlessly, you will need the utilities to maintain its long-term health.

Once you have logged into your Raspberry Pi, you must run the following commands:

**1. Install `btrfs-progs` & maintenance tools**
This installs the core BTRFS tools and an incredibly useful set of automation scripts (`btrfsmaintenance`) which handles background balancing. Without balancing, Docker workloads can fragment the partition and cause fake "Disk Full" errors over time.
```bash
sudo apt update
sudo apt install btrfs-progs btrfsmaintenance
```

**2. Configure and enable automatic data maintenance**
BTRFS has the amazing ability to detect and silently "heal" data corruption (bit rot) using checksums, and background balancing prevents "Disk Full" fragment errors.

Since PiOS is based on Debian, `btrfsmaintenance` uses a central configuration file rather than systemd templates. 

1. Open the automation config file:
```bash
sudo nano /etc/default/btrfsmaintenance
```

2. Inside the file, find the default mount point variables and point them solely at your `/data` partition (or simply use `"auto"` to map all btrfs drives):
```plaintext
BTRFS_SCRUB_MOUNTPOINTS="/data"
BTRFS_BALANCE_MOUNTPOINTS="/data"
```
*Save and exit the file.*

3. Tell the system to apply your new configuration and generate the background timers automatically:
```bash
sudo systemctl restart btrfsmaintenance-refresh.service
```

With these tools configured, your BTRFS space will be completely self-managed, balancing fragmentation and healing data errors entirely in the background while you focus on your Docker containers!