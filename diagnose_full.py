import pyaudio

def detailed_diagnose():
    p = pyaudio.PyAudio()
    count = p.get_device_count()
    print(f"Total Devices: {count}")
    for i in range(count):
        info = p.get_device_info_by_index(i)
        print(f"[{i}] {info['name']}")
        print(f"    Input Channels: {info['maxInputChannels']}")
        print(f"    Output Channels: {info['maxOutputChannels']}")
        print(f"    Sample Rate: {info['defaultSampleRate']}")
    p.terminate()

if __name__ == "__main__":
    detailed_diagnose()
