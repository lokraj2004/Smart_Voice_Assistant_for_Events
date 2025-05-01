import sounddevice as sd
import numpy as np

def test_microphone(index):
    duration = 3
    print(f"🎤 Testing mic index {index} for {duration} seconds...")
    recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype='int16', device=index)
    sd.wait()
    volume = np.linalg.norm(recording)
    print(f"📈 Volume level: {volume}")
    return volume > 1000

for i, dev in enumerate(sd.query_devices()):
    if dev['max_input_channels'] > 0:
        print(f"\n[{i}] {dev['name']}")
        if test_microphone(i):
            print("✅ This mic is capturing audio.")
        else:
            print("❌ Mic seems silent.")
