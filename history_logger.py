import threading
from datetime import datetime

class HistoryLogger:
    def __init__(self, file_path="Chat_history.txt"):
        self.file_path = file_path
        self.lock = threading.Lock()
        self.logging_active = False

    def start_logging(self):
        with self.lock:
            if not self.logging_active:
                self.logging_active = True
                self._log_message("🔴 Logging started")

    def stop_logging(self):
        with self.lock:
            if self.logging_active:
                self._log_message("🟢 Logging stopped")
                self.logging_active = False
                self.save()

    def log(self, user_input, response=None):
        if not self.logging_active:
            return
        with self.lock:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.file_path, "a", encoding="utf-8") as file:
                file.write(f"[{timestamp}] 🧍 You: {user_input}\n")
                if response:
                    file.write(f"[{timestamp}] 🤖 Assistant: {response}\n")

    def save(self):
        # In this version, 'save' isn't strictly necessary since we're directly appending to the file.
        pass

    def _log_message(self, msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {msg}\n")

