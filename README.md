# Sonic Boom 🔊

A simple Python command-line tool for creating a local network party speaker setup. Stream audio from one computer (master) to multiple devices (slaves) over your local network with automatic synchronization.

## Features

- 🎤 **Multiple Input Sources**: Microphone, system audio (macOS), or any audio input device
- 🌐 **Network Discovery**: Automatically discover speakers including Google Cast, Sonos, AirPlay, Spotify Connect, and other Sonic Boom devices
- 🔄 **Multi-Device Sync**: Broadcast to multiple devices with automatic audio synchronization
- 📡 **Multicast Streaming**: Efficient UDP multicast for local network audio streaming
- 🎛️ **Easy Setup**: Simple CLI with friendly prompts and clear error messages

## Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **PortAudio** (required for PyAudio)

### Installing PortAudio

**macOS:**
```bash
brew install portaudio
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install portaudio-devel
```

**Windows:**
PortAudio is typically included with PyAudio installation on Windows.

## Installation

```bash
# Clone the repository
git clone https://github.com/Devn913/Sonic_Boom.git
cd Sonic_Boom

# Install with pip
pip install .

# Or install in development mode
pip install -e .
```

## Usage

### Scan for Speakers

Discover all audio devices on your local network:

```bash
sonic-boom scan
```

This will detect:
- Google Cast devices (Chromecast, Google Home)
- Sonos speakers
- AirPlay/AirPlay 2 devices
- Spotify Connect devices
- Other Sonic Boom master nodes

### Broadcast Audio (Master Mode)

Start broadcasting audio from your device:

```bash
sonic-boom master --group MyParty --name MyComputer
```

**Options:**
- `--group`: Group name for the broadcast session (default: "SonicBoomGroup")
- `--name`: Display name for this master node (default: "MasterNode")

**Steps:**
1. Choose between microphone or system audio mode
2. If using microphone, select your input device from the list
3. The master will start broadcasting to `224.3.29.71:10000` via UDP multicast

### Receive Audio (Slave Mode)

Join a broadcast and play the audio stream:

```bash
sonic-boom slave
```

The slave will:
1. Scan for available Sonic Boom master nodes
2. Display discovered masters in a table
3. Let you select which master to connect to
4. Automatically sync and play the audio stream

## Platform-Specific Setup

### macOS: Capturing System Audio

macOS doesn't allow direct capture of system audio (e.g., from Spotify, YouTube, etc.). To broadcast system audio, you need to set up a virtual audio loopback device.

#### Using BlackHole (Recommended)

**1. Install BlackHole:**
```bash
brew install blackhole-2ch
```

**2. Create a Multi-Output Device:**

a. Open **Audio MIDI Setup** (Applications → Utilities → Audio MIDI Setup)

b. Click the **+** button in the bottom left and select **Create Multi-Output Device**

c. In the Multi-Output Device settings:
   - Check both **BlackHole 2ch** and your **Built-in Output** (or external speakers)
   - This ensures you can hear the audio while also capturing it
   - Optional: Rename it to "BlackHole + Speakers"

**3. Set System Output:**

Go to **System Settings → Sound → Output** and select your new **Multi-Output Device**

**4. Use with Sonic Boom:**

```bash
sonic-boom master --group MyParty
```

When prompted:
- Select `system` mode
- Or select `mic` mode and choose the **BlackHole 2ch** device index

**5. Grant Permissions:**

macOS requires Screen Recording permission for system audio capture:
- Go to **System Settings → Privacy & Security → Screen Recording**
- Enable permission for **Terminal** (or your terminal app)
- Restart Terminal after granting permission

#### Alternative: Loopback (Commercial)

[Loopback by Rogue Amoeba](https://rogueamoeba.com/loopback/) is a commercial alternative with more features and easier configuration.

### Linux: Capturing System Audio

#### Using PulseAudio Loopback Module

**1. Load the loopback module:**
```bash
pactl load-module module-loopback latency_msec=1
```

**2. Find your audio devices:**
```bash
pactl list sources short
```

**3. Start Sonic Boom and select the appropriate loopback device:**
```bash
sonic-boom master
```

**4. Unload the module when done:**
```bash
pactl unload-module module-loopback
```

#### Using ALSA (Alternative)

Create a loopback interface:
```bash
sudo modprobe snd-aloop
```

### Windows: Capturing System Audio

#### Using VB-Audio Virtual Cable

**1. Download and install:**
- Download [VB-CABLE Virtual Audio Device](https://vb-audio.com/Cable/)
- Install the driver (requires admin rights)
- Restart your computer

**2. Set up audio routing:**
- Right-click the speaker icon in system tray → **Sounds**
- Go to the **Playback** tab
- Set **CABLE Input** as your default playback device
- Go to the **Recording** tab
- Right-click **CABLE Output** → **Properties** → **Listen** tab
- Check "Listen to this device" and select your actual speakers

**3. Use with Sonic Boom:**
```bash
sonic-boom master
```
Select the **CABLE Output** device when prompted.

## Network Configuration

### Multicast Configuration

Sonic Boom uses UDP multicast for efficient local network streaming:
- **Multicast Group**: `224.3.29.71`
- **Port**: `10000`
- **Audio Format**: 16-bit PCM, 22050 Hz, Stereo

### Firewall Settings

Make sure your firewall allows:
- **UDP port 10000** (for audio streaming)
- **mDNS/Bonjour port 5353** (for device discovery)
- **Multicast traffic** on your local network interface

**macOS:**
```bash
# Allow incoming connections for Python (if prompted by firewall)
# System Settings → Network → Firewall → Options
```

**Linux (ufw):**
```bash
sudo ufw allow 10000/udp
sudo ufw allow 5353/udp
```

**Windows:**
```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="Sonic Boom" dir=in action=allow protocol=UDP localport=10000
```

### Router Configuration

Some routers may block or limit multicast traffic:
1. Check if IGMP snooping is enabled (recommended for multicast)
2. Ensure devices are on the same subnet
3. Some guest/IoT networks may isolate devices

## Troubleshooting

### No Audio Devices Found

**Error**: "No audio input devices found"

**Solutions**:
- Ensure a microphone or audio input device is connected
- Check that audio drivers are properly installed
- Try running: `python -m sounddevice` to test audio setup

### Permission Denied (macOS)

**Error**: "System audio capture failed"

**Solutions**:
- Grant Screen Recording permission in System Settings → Privacy & Security
- Restart Terminal after granting permission
- Check that BlackHole is properly installed: `ls /Library/Audio/Plug-Ins/HAL/`

### No Speakers Discovered

**Error**: "No speaker broadcasters found"

**Solutions**:
- Ensure devices are on the same local network
- Check that mDNS/Bonjour is not blocked by firewall
- Verify multicast is enabled on your router
- Try increasing scan timeout: `sonic-boom scan --timeout 10`

### Network Connection Failed

**Error**: "Network Error" or "Multicast may not be supported"

**Solutions**:
- Check firewall settings (see Network Configuration above)
- Ensure multicast is not blocked by router
- Verify devices are on same subnet
- Try disabling VPN if active
- Some enterprise networks may block multicast

### Audio Stuttering or Dropouts

**Symptoms**: Choppy audio, glitches, or silence

**Solutions**:
- Move closer to WiFi router for better signal
- Reduce WiFi congestion (use 5GHz band if possible)
- Close bandwidth-heavy applications
- The 400ms buffer should handle most jitter, but severe packet loss will cause issues

### PyAudio Installation Fails

**Error**: "Failed building wheel for pyaudio"

**Solutions**:
- Install PortAudio first (see Prerequisites)
- On macOS: `brew install portaudio && pip install pyaudio`
- On Linux: `sudo apt-get install portaudio19-dev python3-pyaudio`
- On Windows: Try `pip install pipwin && pipwin install pyaudio`

## Technical Details

### Audio Pipeline

**Master (Broadcaster):**
1. Captures audio from input device (22050 Hz, 16-bit PCM, stereo)
2. Adds sequence number and timestamp to each audio chunk
3. Broadcasts via UDP multicast to 224.3.29.71:10000

**Slave (Receiver):**
1. Joins multicast group and listens for packets
2. Buffers incoming audio with 400ms latency for jitter absorption
3. Uses priority queue ordered by sequence numbers
4. Plays audio through output device with automatic sync

### Synchronization Strategy

- **Sequence Numbers**: Each packet has a monotonically increasing sequence number
- **Jitter Buffer**: 400ms initial buffer absorbs network timing variations
- **Packet Ordering**: Priority queue ensures packets play in correct order
- **Late Packet Dropping**: Packets arriving after their sequence are discarded
- **Silence Fill**: Missing packets filled with silence to prevent audio glitches

## Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Master    │                    │   Slave 1   │
│             │                    │             │
│  ┌───────┐  │                    │  ┌───────┐  │
│  │ Audio │  │                    │  │ Audio │  │
│  │ Input │──┼───┐            ┌───┼─▶│Output │  │
│  └───────┘  │   │            │   │  └───────┘  │
└─────────────┘   │            │   └─────────────┘
                  │            │
                  ▼            │   ┌─────────────┐
            ┌──────────┐       │   │   Slave 2   │
            │ Multicast│       │   │             │
            │  Group   │───────┤   │  ┌───────┐  │
            │224.3.29.7│       │   │  │ Audio │  │
            └──────────┘       └───┼─▶│Output │  │
                  │                │  └───────┘  │
                  │                └─────────────┘
                  │
                  │                ┌─────────────┐
                  │                │   Slave N   │
                  │                │             │
                  │                │  ┌───────┐  │
                  │                │  │ Audio │  │
                  └────────────────┼─▶│Output │  │
                                   │  └───────┘  │
                                   └─────────────┘
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is provided as-is for educational and personal use.

## Acknowledgments

- Uses [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) for cross-platform audio I/O
- Uses [Zeroconf](https://github.com/python-zeroconf/python-zeroconf) for network device discovery
- macOS system audio capture via ScreenCaptureKit framework