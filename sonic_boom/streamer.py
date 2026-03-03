import pyaudio
import socket
import struct
import time
import threading
import queue
import numpy as np
from rich.console import Console

console = Console()

# Optimized Audio Configuration for WiFi
FORMAT = pyaudio.paInt16
CHANNELS = 2 
# Lower rate reduces bandwidth by 50%, dramatically improving stability on WiFi
RATE = 22050 
CHUNK = 512 # Balanced for latency/overhead
BROADCAST_ADDR = '255.255.255.255'
PORT = 10000

from .system_audio import SystemAudioCapture

class AudioMaster:
    def __init__(self, group_name="DefaultGroup", device_index=None, capture_mode="pyaudio"):
        self.group_name = group_name
        self.p = pyaudio.PyAudio()
        self.device_index = device_index
        self.capture_mode = capture_mode 
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
        self.running = False
        self.sequence = 0
        self.system_capture = None

    def _on_audio_data(self, data):
        """Pushes data from capture callback to network."""
        if not self.running: return
        # Packet: Seq(I) + Timestamp(d) + Data
        header = struct.pack("!Id", self.sequence, time.time())
        try:
            self.sock.sendto(header + data, (BROADCAST_ADDR, PORT))
            self.sequence += 1
        except: pass

    def start(self):
        self.running = True
        
        if self.capture_mode == "system":
            self.system_capture = SystemAudioCapture(callback=self._on_audio_data, rate=RATE)
            self.system_capture.start()
            console.print(f"[bold green]Master started (System).[/bold green] Broadcasting @ {RATE}Hz")
            
            from PyObjCTools import AppHelper
            try: AppHelper.runConsoleEventLoop()
            except KeyboardInterrupt: self.stop()
        else:
            input_channels = CHANNELS
            if self.device_index is not None:
                info = self.p.get_device_info_by_index(self.device_index)
                input_channels = info['maxInputChannels']

            def mic_callback(in_data, frame_count, time_info, status):
                # Standardize to stereo if needed
                if input_channels == 1:
                    audio = np.frombuffer(in_data, dtype=np.int16)
                    stereo = np.repeat(audio, 2)
                    in_data = stereo.tobytes()
                self._on_audio_data(in_data)
                return (None, pyaudio.paContinue)

            stream = self.p.open(format=FORMAT, channels=input_channels, rate=RATE, 
                                 input=True, input_device_index=self.device_index,
                                 frames_per_buffer=CHUNK, stream_callback=mic_callback)
            
            console.print(f"[bold green]Master started (Mic).[/bold green] Broadcasting @ {RATE}Hz")
            stream.start_stream()
            while self.running: time.sleep(0.5)
            stream.stop_stream()
            stream.close()

    def stop(self):
        self.running = False
        if self.system_capture: self.system_capture.stop()
        if self.p: self.p.terminate()
        from PyObjCTools import AppHelper
        try: AppHelper.stopEventLoop()
        except: pass

class AudioSlave:
    def __init__(self, port=PORT):
        self.port = port
        self.p = pyaudio.PyAudio()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
        self.sock.bind(('', self.port))
        self.running = False
        self.last_seq = -1
        # Priority queue for jitter handling
        self.audio_buffer = queue.PriorityQueue(maxsize=500)
        self.latency_ms = 400 # Initial buffering for seamlessness

    def start(self):
        self.running = True
        
        def playback_callback(in_data, frame_count, time_info, status):
            try:
                # Blocks slightly to self-pace, or returns immediately if data is ready
                # We aim for ~400ms delay to absorb WiFi jitter
                seq, audio_data = self.audio_buffer.get(timeout=0.05)
                if seq <= self.last_seq: # Drop late packet
                    return (b'\x00' * (frame_count * CHANNELS * 2), pyaudio.paContinue)
                self.last_seq = seq
                return (audio_data, pyaudio.paContinue)
            except:
                # Under-run - return silence
                return (b'\x00' * (frame_count * CHANNELS * 2), pyaudio.paContinue)

        stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                             output=True, frames_per_buffer=CHUNK,
                             stream_callback=playback_callback)
        
        console.print(f"[bold blue]Slave started.[/bold blue] Syncing with Master...")
        
        def receiver():
            while self.running:
                try:
                    data_packet, addr = self.sock.recvfrom(4096)
                    header_size = struct.calcsize("!Id")
                    if len(data_packet) < header_size: continue
                    header = data_packet[:header_size]
                    audio_data = data_packet[header_size:]
                    seq, ts = struct.unpack("!Id", header)
                    
                    try:
                        self.audio_buffer.put((seq, audio_data), block=False)
                    except queue.Full:
                        self.audio_buffer.get_nowait()
                        self.audio_buffer.put((seq, audio_data), block=False)
                except: continue

        threading.Thread(target=receiver, daemon=True).start()
        
        # Buffer up before starting playback
        time.sleep(self.latency_ms / 1000.0)
        
        stream.start_stream()
        while self.running: time.sleep(0.5)
        stream.stop_stream()
        stream.close()

    def stop(self):
        self.running = False
        self.p.terminate()
