import speech_recognition as sr
import pyttsx3
from llm_processor import handle_query_with_llm
from llm_processor import sync_google_sheet
from history_logger import HistoryLogger

import pvporcupine
import pyaudio

import struct
import time

# === Configuration ===
ACCESS_KEY = "x6aoh4VVU27BVZ1mHQMGa2EMqE0aee1wy63qK5M4lpyWudjY/ucrjQ==" # picovoice API Key
WAKE_WORD = "jarvis" #Wake word
CONVERSATION_TIMEOUT = 30  # seconds of idle time before returning to wake-word mode
DEVICE_INDEX =2  # Your preferred microphone
LONG_QUERY_THRESHOLD = 20  # Words

engine = pyttsx3.init()
engine.setProperty('rate', 175)   # Adjust speed: 150-200 is natural
engine.setProperty('volume', 1.0) # Full volume

logger = HistoryLogger("user_history.docx")

def speak(text):
    print("Assistant:", text)
    engine.say(text)
    engine.runAndWait()

# === Confirm Only Long/Unclear Queries ===
def needs_confirmation(query):
    return len(query.split()) >= LONG_QUERY_THRESHOLD

def confirm_with_user(query): # used for confirmation of long words
    speak(f"Did you mean: {query}? Please say yes or no.")
    confirmation = listen_for_query(timeout=4, phrase_time_limit=3, pause_threshold=0.8)
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

# === Syncing commands ===
def is_sync_command(query):
    sync_phrases = [
        "sync the sheet", "sync the sheets",
        "update sheet", "update google sheet",
        "sync google sheet"
    ]
    return any(phrase in query.lower() for phrase in sync_phrases)

# === Logging commands ===
def is_logging_command(query):
    lowered = query.lower()
    if "start logging" in lowered or "enable logging" in lowered:
        return "start"
    elif "stop logging" in lowered or "disable logging" in lowered:
        return "stop"
    return None

# === Speech recognition after wake word ===
def listen_for_query(timeout=5, phrase_time_limit=10, pause_threshold=1.5):
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = pause_threshold

    with sr.Microphone(device_index=DEVICE_INDEX, sample_rate=16000) as source:
        print("🎤 Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        speak("Listening")

        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

    try:
        preferred_language = 'en-IN'  # Indian English accent
        query = recognizer.recognize_google(audio, language=preferred_language)
        print("🧍 You said:", query)
        return query
    except sr.WaitTimeoutError:
        print("⏰ No speech detected within timeout.")
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
    except Exception as e:
        print("⚠️ Error:", e)
    return None


# === Voice Cutoff Commands ===
def is_exit_command(query):
    exit_phrases = [
        "simba stop", "simba quit", "simba bye",
        "stop listening simba", "goodbye simba", "exit simba"
    ]
    return any(phrase in query.lower() for phrase in exit_phrases)


# === Voice Cutoff Commands ===
def is_exit_command(query):
    exit_phrases = [
        "simba stop", "simba quit", "simba bye",
        "stop listening simba", "goodbye simba", "exit simba"
    ]
    return any(phrase in query.lower() for phrase in exit_phrases)



# === Wake word detection loop ===
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

                # Start conversational loop
                last_active = time.time()
                while True:
                    query = listen_for_query(timeout=5)  # You can tweak this
                    if query:
                        last_active = time.time()

                        # exit Command
                        if is_exit_command(query):
                            speak("Goodbye! Simba is signing off.")
                            exit(0)

                        # Sync Command
                        if is_sync_command(query):
                            speak("Syncing your Google Sheets now.")
                            success = sync_google_sheet()
                            if success:
                                speak("Sheets synced successfully.")
                            else:
                                speak("There was a problem syncing the sheets.")
                            continue

                        # Logging Command
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

                        # Log interaction
                        logger.log(query, response)

                    elif time.time() - last_active > CONVERSATION_TIMEOUT:
                        print("⌛ Conversation timed out. Returning to wake word mode...")
                        speak("Let me know if you need anything else.")
                        break

                print("👂 Listening for wake word again...")
    except KeyboardInterrupt:
        print("👋 Exiting...")
        logger.stop_logging()  # Ensure logs are saved on exit
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == "__main__":
    detect_wake_word()
