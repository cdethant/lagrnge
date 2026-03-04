# Lagrange - Raspberry Pi Docker Server Stack

Lagrange, the precursor to hamilton, is the hardware layer to the docker ecosystem for signal processing, agent finetuning, network backend, and general database needs of my workflow/tinkering.

## Setting up the hard drive
Lagrange is designated to operate on btrfs. However, Pi OS requires ext4 for its root, meaning we need to partition the drive 3 ways into fat32, ext4, and btrfs for boot, root, and data.

1. Use '''lsblk''' to identify the name of the drive.
2. Create partitions '''sudo fdisk /dev/sdX'''
    Once in, hit '''g''' and then '''n''' to create a new partition.
    Use the defaults number and sector, then designate the size using +[SIZE]

    For my stack, I used '''1: +512M''', '''2: +55G''', '''3: remaining size'''
3. Format the partitions accordingly:
    ''' # 1. Format the boot partition as FAT32
        sudo mkfs.vfat -F32 /dev/sdX1

        # 2. Format the root partition as ext4
        sudo mkfs.ext4 /dev/sdX2

        # 3. Format the data partition as btrfs
        sudo mkfs.btrfs -f /dev/sdX3'''

4. 

