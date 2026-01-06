# Quick WebM Recorder

A lightweight ShareX-style screen region recorder for Linux (X11). Select a region, record video with system audio, and get the file path copied to your clipboard.

## Features

- **Global hotkey** - Trigger recording from anywhere (default: Super+Shift+C)
- **Region selection** - Click and drag to select any screen region
- **System audio capture** - Records what you hear through PulseAudio/PipeWire
- **H.264/MP4 output** - Compatible with all devices and platforms
- **Quality presets** - Choose from Lossless, High, Medium, Low, or Tiny
- **Clipboard integration** - File path copied automatically after recording
- **System tray** - Runs quietly in your system tray

## Installation

### Dependencies

```bash
# System packages
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 ffmpeg xclip

# Python virtual environment
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install pynput
```

### Running

```bash
source venv/bin/activate
python src/main.py
```

## Usage

1. Press the hotkey (Super+Shift+C) to start selection
2. Click and drag to select the recording region
3. Click "Start Recording" or press the hotkey again
4. Click "Finish and Save" or press the hotkey to stop
5. The MP4 file path is copied to your clipboard

Press Escape at any time to cancel.

## Configuration

Right-click the tray icon and select "Settings" to configure:

- **Hotkey** - Click "Listen..." and press your preferred key combination
- **Output folder** - Where recordings are saved
- **Framerate** - 10-60 fps
- **Quality** - Lossless, High, Medium, Low, or Tiny presets
- **Audio source** - Auto-detect, specific device, or no audio

Settings are saved to `~/.config/quick-webm-recorder/settings.json`

## Known Issues

### Flickering/flashing in recordings

When recording GPU-accelerated windows (browsers, video players, games), you may see occasional frame flashes where parts of the window briefly disappear. This is a limitation of x11grab screen capture on composited desktops.

**Workarounds:**
- Disable hardware acceleration in the app you're recording (e.g., Chrome: Settings → System → disable "Use hardware acceleration")
- Temporarily disable compositor effects (Mint: System Settings → Effects)
- Use a lower framerate (24 fps tends to be more stable)

This affects most x11grab-based recorders. A future version may implement PipeWire portal capture for flicker-free recording.

## License

MIT License
