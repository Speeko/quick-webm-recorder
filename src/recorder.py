import subprocess
import signal
import os
from datetime import datetime


class Recorder:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.output_path = None

    def start(self, x, y, w, h):
        output_dir = self.config.output_dir
        os.makedirs(output_dir, exist_ok=True)
        filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.mp4")
        self.output_path = os.path.join(output_dir, filename)

        framerate = self.config.framerate
        quality = self.config.video_quality

        # Note: dimensions should already be even (snapped during selection)
        # Small inset to ensure border anti-aliasing is never captured
        x += 1
        y += 1
        w -= 2
        h -= 2

        # Ensure dimensions stay even after inset
        w = max(w - (w % 2), 2)
        h = max(h - (h % 2), 2)

        # Build ffmpeg command - using H.264 for speed and compatibility
        cmd = [
            'ffmpeg', '-y',
            '-f', 'x11grab',
            '-framerate', str(framerate),
            '-video_size', f'{w}x{h}',
            '-i', f':0.0+{x},{y}',
        ]

        # Add audio capture if configured
        audio_source = self.config.get_resolved_audio_source()
        if audio_source:
            cmd.extend(['-f', 'pulse', '-i', audio_source])
            cmd.extend([
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', str(quality),
                '-c:a', 'aac', '-b:a', '128k',
                '-pix_fmt', 'yuv420p',  # Compatibility with all players
            ])
            print(f"Recording with audio from: {audio_source}")
        else:
            cmd.extend([
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', str(quality),
                '-pix_fmt', 'yuv420p',
            ])
            print("Recording video only (no audio)")

        cmd.append(self.output_path)
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        return self.output_path

    def is_recording(self):
        return self.process is not None
