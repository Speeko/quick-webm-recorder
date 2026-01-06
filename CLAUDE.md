# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quick WebM Recorder - A minimal ShareX-style screen region recorder for Linux (X11). Captures a selected screen region to WebM with system audio, copies result to clipboard.

**Design Philosophy:** Lightweight and functional. No transparency effects, no config UI, no toolbar buttons.

## Tech Stack

- **Language:** Python 3
- **GUI:** GTK 3 / PyGObject
- **Recording:** ffmpeg (x11grab + PulseAudio)
- **Global Hotkeys:** pynput
- **Clipboard:** xclip
- **Target Platform:** Linux (X11, PulseAudio/PipeWire)

## User Flow

```
IDLE → [Super+Shift+R] → SELECTING (fullscreen window, crosshair cursor)
     → [drag mouse]    → selection rectangle drawn (white border)
     → [release mouse] → READY (border remains visible)
     → [Super+Shift+R] → RECORDING (border turns red)
     → [Super+Shift+R] → save webm, copy path to clipboard, return to IDLE
     → [Escape]        → cancel anytime, return to IDLE
```

## Commands

```bash
# Setup virtual environment (first time)
cd ~/Documents/GitHub/quick-webm-recorder
python3 -m venv venv
source venv/bin/activate
pip install pynput

# Install system dependencies (if needed)
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 ffmpeg xclip

# Run the application
source venv/bin/activate
python src/main.py
```

## Project Structure

```
quick-webm-recorder/
├── src/
│   ├── main.py       # Entry point + App state machine
│   ├── hotkey.py     # Global hotkey listener (pynput)
│   ├── overlay.py    # Selection window + border drawing
│   └── recorder.py   # ffmpeg subprocess wrapper
├── venv/             # Python virtual environment
├── config/
│   └── settings.json # (unused - hardcoded defaults)
├── CLAUDE.md
└── requirements.txt
```

## Key Files

### `src/main.py` - App Controller
- State machine: IDLE → SELECTING → READY → RECORDING
- Coordinates hotkey, overlay, and recorder
- Handles clipboard copy via xclip subprocess

### `src/hotkey.py` - Global Hotkey
- Uses pynput for Super+Shift+R detection
- Bridges to GTK main thread via GLib.idle_add()

### `src/overlay.py` - Selection UI
- `SelectionWindow`: Nearly-invisible fullscreen window for mouse capture
- `BorderWindow`: Popup window drawing just the selection border
- White border when ready, red border when recording

### `src/recorder.py` - ffmpeg Wrapper
- Spawns ffmpeg with x11grab + pulse audio
- SIGINT for graceful stop
- Outputs to ~/Videos/Recordings/

## Recording Command

```bash
ffmpeg -y \
  -f x11grab -framerate 30 -video_size WxH -i :0.0+X,Y \
  -f pulse -i default \
  -c:v libvpx-vp9 -crf 30 -b:v 0 \
  -c:a libopus \
  ~/Videos/Recordings/recording_YYYYMMDD_HHMMSS.webm
```

## Dependencies

**System packages:**
- python3-gi, python3-gi-cairo, gir1.2-gtk-3.0
- ffmpeg (with x11grab, libvpx-vp9, libopus, pulseaudio)
- xclip

**Python (in venv):**
- pynput
