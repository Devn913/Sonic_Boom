import objc
import threading
import time
import numpy as np
from Foundation import NSObject
from ScreenCaptureKit import (
    SCStream, SCShareableContent, SCStreamConfiguration, 
    SCContentFilter, SCStreamOutputTypeAudio
)
import CoreMedia
from rich.console import Console

console = Console()

class AudioCaptureDelegate(NSObject):
    def initWithCallback_andRate_(self, callback, target_rate):
        self = objc.super(AudioCaptureDelegate, self).init()
        if self:
            self.callback = callback
            self.target_rate = target_rate
        return self

    def stream_didOutputSampleBuffer_ofType_(self, stream, sampleBuffer, outputType):
        if outputType == SCStreamOutputTypeAudio:
            blockBuffer = CoreMedia.CMSampleBufferGetDataBuffer(sampleBuffer)
            if not blockBuffer: return
            
            length = CoreMedia.CMBlockBufferGetDataLength(blockBuffer)
            if length == 0: return
            
            status, data = CoreMedia.CMBlockBufferCopyDataBytes(blockBuffer, 0, length, None)
            
            if status == 0 and data:
                try:
                    # SCK usually outputs 48000 or 44100 Float32
                    audio_float = np.frombuffer(data, dtype=np.float32).copy()
                    
                    # Party Gain (Optimized)
                    gain = 12.0
                    audio_float = np.clip(audio_float * gain, -1.0, 1.0)
                    
                    # Resample if needed (very simple decimation for WiFi stability)
                    # We assume SCK is 44100 and target is 22050
                    if self.target_rate == 22050:
                        # Take every 2nd sample (L, R, L, R) -> (L, R)
                        # audio_float is [L, R, L, R, ...]
                        resampled = audio_float[::2] 
                        # Wait, slicing [::2] on interleaved stereo is WRONG.
                        # It takes L1, L2, L3... 
                        # Correct way:
                        reshaped = audio_float.reshape(-1, 2)
                        downsampled = reshaped[::2].reshape(-1)
                        audio_float = downsampled

                    # Convert to Int16
                    self.callback((audio_float * 32767).astype(np.int16).tobytes())
                except Exception as e:
                    pass

class SystemAudioCapture:
    def __init__(self, callback, rate=22050):
        self.callback = callback
        self.rate = rate
        self.stream = None
        self.running = False
        self.delegate = None

    def start(self):
        self.running = True
        self._setup_capture()

    def _setup_capture(self):
        def completion_handler(content, error):
            if error or not content.displays(): return

            display = content.displays()[0]
            filter = SCContentFilter.alloc().initWithDisplay_excludingApplications_exceptingWindows_(display, [], [])
            config = SCStreamConfiguration.alloc().init()
            config.setCapturesAudio_(True)
            config.setExcludesCurrentProcessAudio_(True)
            config.setWidth_(1280)
            config.setHeight_(720)
            
            # Request 44100 from SCK, we downsample to 22050 for the network
            config.setSampleRate_(44100)
            config.setChannelCount_(2)
            
            self.delegate = AudioCaptureDelegate.alloc().initWithCallback_andRate_(self.callback, self.rate)
            self.stream = SCStream.alloc().initWithFilter_configuration_delegate_(filter, config, self.delegate)
            self.stream.addStreamOutput_type_sampleHandlerQueue_error_(self.delegate, SCStreamOutputTypeAudio, None, objc.NULL)
            
            time.sleep(0.2)
            self.stream.startCaptureWithCompletionHandler_(lambda err: None)

        SCShareableContent.getShareableContentWithCompletionHandler_(completion_handler)

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stopCaptureWithCompletionHandler_(lambda err: None)
