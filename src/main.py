#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import subprocess

from config import Config
from hotkey import HotkeyListener
from recorder import Recorder
from overlay import SelectionManager


class App:
    IDLE = 0
    SELECTING = 1
    READY = 2
    RECORDING = 3

    def __init__(self):
        self.state = self.IDLE
        self.selection = None

        self.config = Config()
        self.recorder = Recorder(self.config)
        self.overlay = SelectionManager()
        self.hotkey = HotkeyListener(self.on_hotkey, self.config.hotkey)

        self.overlay.on_selection_complete = self.on_selection_complete
        self.overlay.on_cancel = self.on_cancel
        self.overlay.on_start_recording = self.start_recording
        self.overlay.on_stop_recording = self.stop_recording

        # Settings window (created on demand)
        self._settings_window = None

        # Tray icon
        self.tray = TrayIcon(self)

    def show_settings(self):
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self.config, self._on_settings_closed)
        self._settings_window.show_all()
        self._settings_window.present()

    def show_about(self):
        about = Gtk.AboutDialog()
        about.set_program_name("Quick WebM Recorder")
        about.set_version("1.0.0")
        about.set_comments("A lightweight screen region recorder for Linux.\nCaptures video with system audio to MP4.")
        about.set_website("https://github.com/Speeko/quick-webm-recorder")
        about.set_website_label("GitHub Repository")
        about.set_authors(["Brett"])
        about.set_license_type(Gtk.License.MIT_X11)
        about.set_logo_icon_name("camera-video")
        about.run()
        about.destroy()

    def _on_settings_closed(self, hotkey_changed):
        if hotkey_changed:
            # Restart hotkey listener with new hotkey
            self.hotkey.stop()
            self.hotkey = HotkeyListener(self.on_hotkey, self.config.hotkey)
            self.hotkey.start()
            print(f"Hotkey updated to: {self.config.hotkey}")

    def on_hotkey(self):
        if self.state == self.IDLE:
            self.start_selection()
        elif self.state == self.READY:
            self.start_recording()
        elif self.state == self.RECORDING:
            self.stop_recording()

    def start_selection(self):
        self.state = self.SELECTING
        self.overlay.show_for_selection()

    def on_selection_complete(self, rect):
        self.state = self.READY
        self.selection = rect
        print(f"Selection ready: {rect}")

    def on_cancel(self):
        self.state = self.IDLE
        self.selection = None
        print("Selection cancelled")

    def start_recording(self):
        self.state = self.RECORDING
        self.overlay.set_recording(True)  # Updates border color and button text
        x, y, w, h = self.selection
        self.recorder.start(x, y, w, h)
        print(f"Recording started: {w}x{h}")

    def stop_recording(self):
        output_path = self.recorder.stop()
        self.overlay.set_recording(False)  # Reset toolbar button text
        self.overlay.border_window.hide()
        self.overlay.toolbar.hide()
        self.state = self.IDLE
        self.selection = None

        # Copy path to clipboard
        try:
            subprocess.run(
                ['xclip', '-selection', 'clipboard'],
                input=output_path.encode(),
                check=True
            )
            print(f"Saved and copied to clipboard: {output_path}")
        except subprocess.CalledProcessError:
            print(f"Saved (clipboard failed): {output_path}")

    def run(self):
        print("Quick WebM Recorder started")
        print(f"Hotkey: {self.config.hotkey}")
        self.hotkey.start()
        try:
            Gtk.main()
        except KeyboardInterrupt:
            pass
        finally:
            self.hotkey.stop()
            if self.recorder.is_recording():
                self.recorder.stop()
            print("Exiting...")

    def quit(self):
        if self.recorder.is_recording():
            self.recorder.stop()
        Gtk.main_quit()


class SettingsWindow(Gtk.Window):
    def __init__(self, config, on_close_callback):
        super().__init__(title="Quick WebM Recorder - Settings")
        self.config = config
        self.on_close_callback = on_close_callback
        self.original_hotkey = config.hotkey

        # Hotkey capture state
        self._listening = False
        self._hotkey_listener = None
        self._captured_keys = set()

        self.set_default_size(450, 320)
        self.set_border_width(12)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect('delete-event', self._on_delete)

        # Main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(vbox)

        # Hotkey setting with Listen button
        hotkey_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hotkey_label = Gtk.Label(label="Hotkey:")
        hotkey_label.set_xalign(0)
        hotkey_label.set_size_request(100, -1)
        self.hotkey_entry = Gtk.Entry()
        self.hotkey_entry.set_text(config.hotkey)
        self.hotkey_entry.set_editable(False)
        self.listen_btn = Gtk.Button(label="Listen...")
        self.listen_btn.connect('clicked', self._on_listen_clicked)
        self.listen_btn.set_tooltip_text("Click then press your desired hotkey combination")
        hotkey_box.pack_start(hotkey_label, False, False, 0)
        hotkey_box.pack_start(self.hotkey_entry, True, True, 0)
        hotkey_box.pack_start(self.listen_btn, False, False, 0)
        vbox.pack_start(hotkey_box, False, False, 0)

        # Output directory
        output_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        output_label = Gtk.Label(label="Output folder:")
        output_label.set_xalign(0)
        output_label.set_size_request(100, -1)
        self.output_entry = Gtk.Entry()
        self.output_entry.set_text(config._config["output_dir"])
        output_browse = Gtk.Button(label="Browse...")
        output_browse.connect('clicked', self._on_browse_output)
        output_box.pack_start(output_label, False, False, 0)
        output_box.pack_start(self.output_entry, True, True, 0)
        output_box.pack_start(output_browse, False, False, 0)
        vbox.pack_start(output_box, False, False, 0)

        # Framerate
        fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fps_label = Gtk.Label(label="Framerate:")
        fps_label.set_xalign(0)
        fps_label.set_size_request(100, -1)
        self.fps_spin = Gtk.SpinButton.new_with_range(10, 60, 5)
        self.fps_spin.set_value(config.framerate)
        fps_box.pack_start(fps_label, False, False, 0)
        fps_box.pack_start(self.fps_spin, False, False, 0)
        vbox.pack_start(fps_box, False, False, 0)

        # Video quality (profile-based)
        from config import QUALITY_PROFILES
        quality_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        quality_label = Gtk.Label(label="Quality:")
        quality_label.set_xalign(0)
        quality_label.set_size_request(100, -1)
        self.quality_combo = Gtk.ComboBoxText()
        current_profile = config.quality_profile
        active_index = 0
        for i, (profile_id, (crf, description)) in enumerate(QUALITY_PROFILES.items()):
            self.quality_combo.append(profile_id, description)
            if profile_id == current_profile:
                active_index = i
        self.quality_combo.set_active(active_index)
        quality_box.pack_start(quality_label, False, False, 0)
        quality_box.pack_start(self.quality_combo, True, True, 0)
        vbox.pack_start(quality_box, False, False, 0)

        # Audio source
        audio_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        audio_label = Gtk.Label(label="Audio source:")
        audio_label.set_xalign(0)
        audio_label.set_size_request(100, -1)
        self.audio_combo = Gtk.ComboBoxText()
        audio_sources = config.get_audio_sources()
        current_source = config.audio_source
        active_index = 0
        for i, (source_id, source_name) in enumerate(audio_sources):
            self.audio_combo.append(source_id, source_name)
            if source_id == current_source:
                active_index = i
        self.audio_combo.set_active(active_index)
        audio_box.pack_start(audio_label, False, False, 0)
        audio_box.pack_start(self.audio_combo, True, True, 0)
        vbox.pack_start(audio_box, False, False, 0)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        save_btn = Gtk.Button(label="Save")
        save_btn.connect('clicked', self._on_save)
        save_btn.get_style_context().add_class('suggested-action')
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect('clicked', self._on_cancel)
        button_box.pack_start(cancel_btn, False, False, 0)
        button_box.pack_start(save_btn, False, False, 0)
        vbox.pack_end(button_box, False, False, 0)

    def _on_listen_clicked(self, button):
        if self._listening:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self):
        from pynput import keyboard
        from gi.repository import GLib
        self._listening = True
        self._captured_keys = set()
        self.listen_btn.set_label("Press keys...")
        self.hotkey_entry.set_text("Press hotkey combination...")

        def on_press(key):
            self._captured_keys.add(key)

        def on_release(key):
            if self._listening and self._captured_keys:
                # Build hotkey string from captured keys
                GLib.idle_add(self._finish_capture)

        self._hotkey_listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self._hotkey_listener.start()

    def _stop_listening(self):
        self._listening = False
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        self.listen_btn.set_label("Listen...")

    def _finish_capture(self):
        from pynput import keyboard
        if not self._captured_keys:
            self._stop_listening()
            return

        # Convert captured keys to pynput hotkey format
        parts = []
        main_key = None

        for key in self._captured_keys:
            if key == keyboard.Key.cmd or key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                parts.append("<cmd>")
            elif key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                parts.append("<ctrl>")
            elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                parts.append("<alt>")
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                parts.append("<shift>")
            elif hasattr(key, 'char') and key.char:
                main_key = key.char.lower()
            elif hasattr(key, 'name'):
                main_key = key.name

        if main_key:
            parts.append(main_key)

        if parts:
            hotkey_str = "+".join(parts)
            self.hotkey_entry.set_text(hotkey_str)

        self._stop_listening()

    def _on_browse_output(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Output Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                          Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_current_folder(self.config.output_dir)

        if dialog.run() == Gtk.ResponseType.OK:
            self.output_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _on_save(self, button):
        self._stop_listening()  # Stop listening if active
        self.config.hotkey = self.hotkey_entry.get_text()
        self.config.output_dir = self.output_entry.get_text()
        self.config.framerate = int(self.fps_spin.get_value())
        self.config.quality_profile = self.quality_combo.get_active_id()
        self.config.audio_source = self.audio_combo.get_active_id()

        hotkey_changed = (self.config.hotkey != self.original_hotkey)
        self.hide()
        if self.on_close_callback:
            self.on_close_callback(hotkey_changed)

    def _on_cancel(self, button):
        self._stop_listening()
        self.hide()

    def _on_delete(self, widget, event):
        self._stop_listening()
        self.hide()
        return True  # Prevent destruction


class TrayIcon:
    def __init__(self, app):
        self.app = app

        # Create status icon
        self.icon = Gtk.StatusIcon()
        self.icon.set_from_icon_name("camera-video")
        self.icon.set_tooltip_text("Quick WebM Recorder")
        self.icon.connect('popup-menu', self._on_popup_menu)
        self.icon.connect('activate', self._on_activate)
        self.icon.set_visible(True)

    def _on_activate(self, icon):
        # Left click - start recording
        if self.app.state == self.app.IDLE:
            self.app.start_selection()

    def _on_popup_menu(self, icon, button, time):
        menu = Gtk.Menu()

        # Record item
        record_item = Gtk.MenuItem(label="Record")
        record_item.connect('activate', lambda x: self.app.start_selection())
        record_item.set_sensitive(self.app.state == self.app.IDLE)
        menu.append(record_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Settings item
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.connect('activate', lambda x: self.app.show_settings())
        menu.append(settings_item)

        # About item
        about_item = Gtk.MenuItem(label="About")
        about_item.connect('activate', lambda x: self.app.show_about())
        menu.append(about_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Quit item
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect('activate', lambda x: self.app.quit())
        menu.append(quit_item)

        menu.show_all()
        menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)


def main():
    app = App()
    app.run()


if __name__ == '__main__':
    main()
