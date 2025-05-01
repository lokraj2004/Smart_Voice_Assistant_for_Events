import pyttsx3
import struct
import time
import queue
import json
import pvporcupine
import pyaudio
import noisereduce as nr
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from llm_processor import handle_query_with_llm, sync_google_sheet
from history_logger import HistoryLogger

# === Configuration ===
ACCESS_KEY = "x6aoh4VVU27BVZ1mHQMGa2EMqE0aee1wy63qK5M4lpyWudjY/ucrjQ=="  # picovoice API Key
WAKE_WORD = "jarvis"
CONVERSATION_TIMEOUT = 30  # seconds
DEVICE_INDEX = 2
LONG_QUERY_THRESHOLD = 20  # Words
WHISPER_MODEL_SIZE = "medium"  # "tiny", "base", "small", "medium", "large"
PAUSE_THRESHOLD = 1.0  # seconds of silence to consider end of speech
NOISE_SUPPRESSION_LEVEL = 0.7  # adjust (0 to 1), higher = more suppression

# === Initialize Components ===
engine = pyttsx3.init()
engine.setProperty('rate', 175)
engine.setProperty('volume', 1.0)
logger = HistoryLogger("Chat_history.txt")
audio_queue = queue.Queue()
model = WhisperModel(WHISPER_MODEL_SIZE, compute_type="int8")

# === Utilities ===
def speak(text):
    print("Assistant:", text)
    engine.say(text)
    engine.runAndWait()

def needs_confirmation(query):
    return len(query.split()) >= LONG_QUERY_THRESHOLD

def is_sync_command(query):
    sync_phrases = [
        "sync the sheet", "sync the sheets",
        "update sheet", "update google sheet",
        "sync google sheet"
    ]
    return any(phrase in query.lower() for phrase in sync_phrases)

def is_logging_command(query):
    lowered = query.lower()
    if "start log" in lowered or "enable log" in lowered:
        return "start"
    elif "stop log" in lowered or "disable log" in lowered:
        return "stop"
    return None

def is_exit_command(query):
    exit_phrases = [
        "simba stop", "simba quit", "simba bye",
        "stop listening simba", "goodbye simba", "exit simba"
    ]
    return any(phrase in query.lower() for phrase in exit_phrases)

def audio_callback(indata, frames, time_info, status):
    if status:
        print("[Status]", status)
    audio_queue.put(indata.copy())

def listen_for_query():
    print("🎤 Listening with Faster-Whisper...")
    speak("Listening...")

    recording = []
    silence_threshold = 5000
    max_silence_duration = 2.0
    max_total_duration = 10.0
    silence_start = None

    with sd.InputStream(samplerate=16000, blocksize=1600, dtype='int16',
                        channels=1, callback=audio_callback, device=DEVICE_INDEX):
        start_time = time.time()

        while True:
            try:
                data = audio_queue.get(timeout=1.0)
            except queue.Empty:
                print("⌛ No input for a while, ending...")
                break

            audio_array = data.flatten()
            volume = np.linalg.norm(audio_array)

            if volume < silence_threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > max_silence_duration:
                    print("🛑 Silence detected. Stopping listening.")
                    break
            else:
                silence_start = None

            recording.append(audio_array)

            if time.time() - start_time > max_total_duration:
                print("⌛ Max recording duration reached.")
                break

    if not recording:
        print("⚠️ No audio captured.")
        return None

    audio_np = np.concatenate(recording)
    audio_float32 = audio_np.astype(np.float32) / 32768.0

    try:
        segments, info = model.transcribe(audio_float32, beam_size=5, language="en")
    except Exception as e:
        print("❌ Transcription failed:", e)
        return None

    full_text = " ".join(segment.text.strip() for segment in segments)
    query = full_text.strip()
    if query:
        print("🧍 You said:", query)
        return query
    else:
        print("🤷 No text recognized.")
        return None

def confirm_with_user(query):
    speak(f"Did you mean: {query}? Please say yes or no.")
    confirmation = listen_for_query()
    if not confirmation:
        speak("I didn't catch that.")
        return False

    confirmation = confirmation.lower()
    print("🔁 Confirmation heard:", confirmation)
    if confirmation in ["yes", "yeah", "correct", "yup", "sure"]:
        return True
    elif confirmation in ["no", "nope", "nah"]:
        return False
    else:
        speak("I'm not sure I understood. Let's try again.")
        return False

def handle_conversation():
    last_active = time.time()

    while True:
        query = listen_for_query()
        if query:
            last_active = time.time()

            if is_exit_command(query):
                speak("Goodbye! Simba is signing off.")
                logger.stop_logging()
                exit(0)

            if is_sync_command(query):
                speak("Syncing your Google Sheets now.")
                success = sync_google_sheet()
                speak("Sheets synced successfully." if success else "There was a problem syncing the sheets.")
                continue

            log_cmd = is_logging_command(query)
            if log_cmd == "start":
                logger.start_logging()
                speak("History logging started.")
                continue
            elif log_cmd == "stop":
                logger.stop_logging()
                speak("History logging stopped.")
                continue

            if needs_confirmation(query):
                if not confirm_with_user(query):
                    speak("Okay, let's try again.")
                    continue

            response = handle_query_with_llm(query)
            speak(response)
            logger.log(query, response)

        elif time.time() - last_active > CONVERSATION_TIMEOUT:
            print("⌛ Conversation timed out. Returning to wake word mode...")
            speak("Let me know if you need anything else.")
            break

def detect_wake_word():
    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keywords=[WAKE_WORD]
    )

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        input_device_index=DEVICE_INDEX,
        frames_per_buffer=porcupine.frame_length
    )

    speak("Hello! I’m Simba")

    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                print("✅ Wake word detected!")
                speak("Yes, how can I help?")

                # Stop Porcupine listening
                stream.stop_stream()
                stream.close()
                pa.terminate()
                porcupine.delete()

                # === Handle conversation ===
                handle_conversation()

                # === Restart wake word detection ===
                porcupine = pvporcupine.create(
                    access_key=ACCESS_KEY,
                    keywords=[WAKE_WORD]
                )

                pa = pyaudio.PyAudio()
                stream = pa.open(
                    rate=porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    input_device_index=DEVICE_INDEX,
                    frames_per_buffer=porcupine.frame_length
                )
                print("👂 Returning to wake word listening...")

    except KeyboardInterrupt:
        print("👋 Exiting...")
        logger.stop_logging()
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == "__main__":
    detect_wake_word()
