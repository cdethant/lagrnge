# Lagrnge - Raspberry Pi Docker Server Stack

Lagrnge, the precursor to hamilton, is the hardware layer to the docker ecosystem for signal processing, agent finetuning, network backend, and general database needs of my workflow/tinkering.

## Setting up the hard drive
Lagrnge is designated to operate on btrfs. However, Pi OS requires ext4 for its root, meaning we need to partition the drive 3 ways into fat32, ext4, and btrfs for boot, root, and data.

1. Use `lsblk` to identify the name of the drive.
2. Create partitions `sudo fdisk /dev/sdX`
    Once in, hit `g` and then `n` to create a new partition.
    Use the defaults number and sector, then designate the size using +[SIZE]

    For my stack, I used `1: +512M`, `2: +55G`, `3: remaining size`
3. Format the partitions accordingly:
    ```bash
    # 1. Format the boot partition as FAT32
    sudo mkfs.vfat -F32 /dev/sdX1

    # 2. Format the root partition as ext4
    sudo mkfs.ext4 /dev/sdX2

    # 3. Format the data partition as btrfs
    sudo mkfs.btrfs -f /dev/sdX3
    ```

4. At this point, you will download and extract Pi OS (I used trixie lite) directly into the `/mnt` directory.

    ```bash
    # Example extraction command (requires bsdtar to preserve file attributes)
    sudo bsdtar -xpf ArchLinuxARM-rpi-aarch64-latest.tar.gz -C /mnt
    sudo sync
    ```

5. Tell the new OS about your custom partition layout so it knows how to mount the ext4 root and btrfs data partitions on boot.

    Find the UUIDs of your partitions:
    ```bash
    lsblk -f /dev/sdX
    ```

    Edit the fstab file on the SSD:
    ```bash
    sudo nano /mnt/etc/fstab
    ```

    Add the entries using the UUIDs you just gathered. It should look similar to this:
    ```plaintext
    # Boot
    UUID=XXXX-XXXX                            /boot   vfat    defaults        0       2
    # Root OS
    UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx /       ext4    defaults,noatime 0       1
    # Docker/SDR Storage
    UUID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy /data   btrfs   rw,relatime,space_cache=v2,compress=zstd 0 0
    ```

    (Note: Adding `compress=zstd` to the btrfs mount options is highly recommended for SDDs, as it saves space and reduces write amplification without noticeable CPU overhead).

6. Sync the filesystem to ensure all cache is written to the SSD, unmount everything, and safely eject the drive.
    ```bash
    sudo sync
    sudo umount -R /mnt
    ```