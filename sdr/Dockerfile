FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies required for downloading and extracting Conda
RUN apt-get update && apt-get install -y \
    wget \
    bzip2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install the ARM64 (Raspberry Pi) version of Radioconda
RUN wget -O radioconda.sh https://github.com/radioconda/radioconda-installer/releases/download/2025.03.14/radioconda-2025.03.14-Linux-aarch64.sh && \
    bash radioconda.sh -b -p /opt/radioconda && \
    rm radioconda.sh

# Add the new Radioconda environment to the system PATH
ENV PATH="/opt/radioconda/bin:$PATH"

# Set up the workspace
WORKDIR /workspace