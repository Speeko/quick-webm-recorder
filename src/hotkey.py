from pynput import keyboard
from gi.repository import GLib


class HotkeyListener:
    def __init__(self, callback, hotkey_str='<cmd>+<shift>+c'):
        self.callback = callback
        self.hotkey_str = hotkey_str
        self.hotkey = keyboard.HotKey(
            keyboard.HotKey.parse(hotkey_str),
            self._on_trigger
        )
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        print(f"Hotkey registered: {hotkey_str}")

    def _on_trigger(self):
        # Thread-safe GTK call
        GLib.idle_add(self.callback)

    def _on_press(self, key):
        self.hotkey.press(self.listener.canonical(key))

    def _on_release(self, key):
        self.hotkey.release(self.listener.canonical(key))

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()
