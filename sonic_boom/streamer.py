import pyaudio
import socket
import struct
import time
import threading
from rich.console import Console

console = Console()

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 2 # Default to Stereo for better quality (System Audio/Spotify)
RATE = 44100
CHUNK = 1024
MULTICAST_GROUP = '224.3.29.71'
PORT = 10000

from .system_audio import SystemAudioCapture

class AudioMaster:
    def __init__(self, group_name="DefaultGroup", device_index=None, capture_mode="pyaudio"):
        self.group_name = group_name
        self.p = pyaudio.PyAudio()
        self.device_index = device_index
        self.capture_mode = capture_mode # "pyaudio" or "system"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        self.running = False
        self.sequence = 0
        self.system_capture = None

    @staticmethod
    def list_devices():
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels']
                })
        p.terminate()
        return devices

    def _broadcast_loop(self, stream_to_close=None):
        try:
            while self.running:
                if self.capture_mode == "system":
                    data = self.system_capture.read(CHUNK * 4) # 4 bytes per sample (Stereo 16-bit)
                else:
                    data = stream_to_close.read(CHUNK, exception_on_overflow=False)
                    
                    # If input is mono but we want to broadcast stereo, duplicate the channel
                    if stream_to_close.CHANNELS == 1 and CHANNELS == 2:
                        import numpy as np
                        audio_data = np.frombuffer(data, dtype=np.int16)
                        stereo_data = np.repeat(audio_data, 2)
                        data = stereo_data.tobytes()

                if not data:
                    continue

                header = struct.pack("!Id", self.sequence, time.time())
                self.sock.sendto(header + data, (MULTICAST_GROUP, PORT))
                self.sequence += 1
        except Exception as e:
            if self.running:
                console.print(f"[red]Broadcasting error: {e}[/red]")
        finally:
            self.running = False

    def start(self):
        self.running = True
        
        if self.capture_mode == "system":
            self.system_capture = SystemAudioCapture()
            self.system_capture.start()
            
            console.print(f"[bold green]Master started.[/bold green] Broadcasting System Audio to {MULTICAST_GROUP}:{PORT}")
            
            # Start broadcasting in background thread
            t = threading.Thread(target=self._broadcast_loop, daemon=True)
            t.start()
            
            # RUN LOOP ON MAIN THREAD (Required by ScreenCaptureKit)
            from PyObjCTools import AppHelper
            try:
                AppHelper.runConsoleEventLoop()
            except KeyboardInterrupt:
                self.stop()
        else:
            input_channels = CHANNELS
            if self.device_index is not None:
                info = self.p.get_device_info_by_index(self.device_index)
                input_channels = info['maxInputChannels']

            stream = self.p.open(format=FORMAT, channels=input_channels, rate=RATE, 
                                 input=True, input_device_index=self.device_index,
                                 frames_per_buffer=CHUNK)
            stream.CHANNELS = input_channels # Attach for helper
            
            console.print(f"[bold green]Master started.[/bold green] Broadcasting to {MULTICAST_GROUP}:{PORT} (Group: {self.group_name})")
            device_name = self.p.get_device_info_by_index(self.device_index)['name'] if self.device_index is not None else 'Default'
            console.print(f"Using device: {device_name} ({input_channels} channels)")
            
            try:
                self._broadcast_loop(stream)
            except KeyboardInterrupt:
                self.stop()
            finally:
                stream.stop_stream()
                stream.close()

    def stop(self):
        self.running = False
        if self.system_capture:
            self.system_capture.stop()
        if self.p:
            self.p.terminate()
        # Kill the RunLoop
        from PyObjCTools import AppHelper
        AppHelper.stopEventLoop()

class AudioSlave:
    def __init__(self, multicast_group=MULTICAST_GROUP, port=PORT):
        self.multicast_group = multicast_group
        self.port = port
        self.p = pyaudio.PyAudio()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        
        mreq = struct.pack("4sl", socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        self.running = False
        self.last_sequence = -1

    def start(self):
        self.running = True
        stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                             output=True, frames_per_buffer=CHUNK)
        
        console.print(f"[bold blue]Slave started.[/bold blue] Listening for broadcast on {self.multicast_group}:{self.port}...")
        
        try:
            while self.running:
                data_packet, addr = self.sock.recvfrom(2048)
                header_size = struct.calcsize("!Id")
                header = data_packet[:header_size]
                audio_data = data_packet[header_size:]
                
                seq, timestamp = struct.unpack("!Id", header)
                
                # Simple Sync Logic: Drop out-of-order old packets
                if seq > self.last_sequence:
                    self.last_sequence = seq
                    stream.write(audio_data)
                else:
                    # Packet arrived too late or out of order
                    pass
        except KeyboardInterrupt:
            self.stop()
        finally:
            stream.stop_stream()
            stream.close()

    def stop(self):
        self.running = False
        self.p.terminate()
