import pyaudio
import sys

def test_pyaudio():
    try:
        p = pyaudio.PyAudio()
        print(f"PyAudio version: {pyaudio.__version__}")
        device_count = p.get_device_count()
        print(f"Device count: {device_count}")
        
        if device_count == 0:
            print("\n[!] No audio devices found by PortAudio.")
        else:
            for i in range(device_count):
                info = p.get_device_info_by_index(i)
                print(f"Index {i}: {info['name']} (Inputs: {info['maxInputChannels']})")
        
        p.terminate()
    except Exception as e:
        print(f"\n[X] Error initializing PyAudio: {e}")

if __name__ == "__main__":
    test_pyaudio()
