import os
import json
import random
from typing import Dict, Optional

class SessionRotator:
    def __init__(self, sessions_directory: str = "sessions"):
        self.sessions_dir = sessions_directory
        self.active_sessions: Dict[str, dict] = {}
        self._load_sessions()

    def _load_sessions(self):
        """Loads all JSON cookie files from the designated folder."""
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
            return

        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.sessions_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        self.active_sessions[filename] = json.load(f)
                except Exception as e:
                    print(f"Error loading session {filename}: {e}")

    def get_random_session(self) -> Optional[dict]:
        """Retrieves a random set of session cookies."""
        if not self.active_sessions:
            return None
        session_name = random.choice(list(self.active_sessions.keys()))
        return self.active_sessions[session_name]

    def remove_invalid_session(self, filename: str):
        """Discards an identity if the session has expired or been revoked."""
        if filename in self.active_sessions:
            del self.active_sessions[filename]
            # Optionally remove or rename the file locally
            target_path = os.path.join(self.sessions_dir, filename)
            if os.path.exists(target_path):
                os.rename(target_path, target_path + ".invalid")
