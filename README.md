# Sonic Boom CLI

A simple CLI tool to scan for speaker broadcasters (Google Cast, Sonos, AirPlay, Spotify Connect) in your local network and check their group sync status.

## Prerequisites

- Python 3.8+
- pip

## Installation

```bash
# Clone the repository (if applicable)
cd Sonic_Boom

# Install dependencies
python3 -m pip install .
```

## Usage

### Scan for speakers
```bash
sonic-boom scan
```

The tool will list all discovered speakers, including any active Sonic Boom Master nodes.

### Broadcast Audio (Master)
To start broadcasting audio from your default microphone/input device:
```bash
sonic-boom master --group MyParty
```
This node will register itself via mDNS and start a UDP Multicast stream.

### Receive Audio (Slave)
To receive and play the audio broadcast on another device in the network:
```bash
sonic-boom slave
```
The slave will automatically join the multicast group and play the incoming stream.

### How it works (Master/Slave)
- **Master:** Captures audio using `PyAudio`, packs it with a sequence number and timestamp, and broadcasts it to `224.3.29.71:10000` via UDP Multicast.
- **Slave:** Listens on the multicast address, de-packets the audio, and uses a simple sequence-based sync logic to play the stream with minimal jitter.
