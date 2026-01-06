import json
import os
import subprocess

CONFIG_DIR = os.path.expanduser("~/.config/quick-webm-recorder")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

# Quality profiles: name -> (CRF value, description)
QUALITY_PROFILES = {
    "lossless": (0, "Lossless - Very large files"),
    "high": (18, "High - Large files, excellent quality"),
    "medium": (23, "Medium - Balanced quality and size"),
    "low": (28, "Low - Smaller files, good quality"),
    "tiny": (35, "Tiny - Small files, reduced quality"),
}

DEFAULT_CONFIG = {
    "hotkey": "<cmd>+<shift>+c",
    "hotkey_gif": "<cmd>+<shift>+g",
    "output_dir": "~/Videos/Recordings",
    "framerate": 30,
    "gif_framerate": 15,  # Lower framerate for smaller GIFs
    "quality_profile": "medium",  # One of QUALITY_PROFILES keys
    "audio_source": "auto",  # "auto", "none", or specific source name
}


class Config:
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load config from file, or create default if doesn't exist."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    self._config.update(loaded)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config: {e}")
        else:
            self.save()  # Create default config file

    def save(self):
        """Save current config to file."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")

    @property
    def hotkey(self):
        return self._config["hotkey"]

    @hotkey.setter
    def hotkey(self, value):
        self._config["hotkey"] = value
        self.save()

    @property
    def hotkey_gif(self):
        return self._config.get("hotkey_gif", "<cmd>+<shift>+g")

    @hotkey_gif.setter
    def hotkey_gif(self, value):
        self._config["hotkey_gif"] = value
        self.save()

    @property
    def gif_framerate(self):
        return self._config.get("gif_framerate", 15)

    @gif_framerate.setter
    def gif_framerate(self, value):
        self._config["gif_framerate"] = int(value)
        self.save()

    @property
    def output_dir(self):
        return os.path.expanduser(self._config["output_dir"])

    @output_dir.setter
    def output_dir(self, value):
        self._config["output_dir"] = value
        self.save()

    @property
    def framerate(self):
        return self._config["framerate"]

    @framerate.setter
    def framerate(self, value):
        self._config["framerate"] = int(value)
        self.save()

    @property
    def quality_profile(self):
        return self._config.get("quality_profile", "medium")

    @quality_profile.setter
    def quality_profile(self, value):
        if value in QUALITY_PROFILES:
            self._config["quality_profile"] = value
            self.save()

    @property
    def video_quality(self):
        """Get CRF value from quality profile."""
        profile = self.quality_profile
        if profile in QUALITY_PROFILES:
            return QUALITY_PROFILES[profile][0]
        return 23  # Default to medium

    @property
    def audio_source(self):
        return self._config["audio_source"]

    @audio_source.setter
    def audio_source(self, value):
        self._config["audio_source"] = value
        self.save()

    def get_audio_sources(self):
        """Get list of available audio monitor sources."""
        sources = [("auto", "Auto-detect"), ("none", "No audio")]
        try:
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sources'],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.strip().split('\n'):
                if '.monitor' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        source_name = parts[1]
                        # Create a compact friendly name
                        friendly = source_name.replace('alsa_output.', '').replace('.monitor', '')
                        friendly = friendly.replace('_', ' ').replace('-', ' ')
                        # Capitalize first letter of each word
                        friendly = friendly.title()
                        sources.append((source_name, friendly))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return sources

    def get_resolved_audio_source(self):
        """Get the actual audio source to use (resolves 'auto')."""
        if self.audio_source == "none":
            return None
        elif self.audio_source == "auto":
            # Auto-detect default sink monitor
            try:
                result = subprocess.run(
                    ['pactl', 'get-default-sink'],
                    capture_output=True, text=True, check=True
                )
                default_sink = result.stdout.strip()
                return f"{default_sink}.monitor"
            except (subprocess.CalledProcessError, FileNotFoundError):
                return None
        else:
            return self.audio_source
