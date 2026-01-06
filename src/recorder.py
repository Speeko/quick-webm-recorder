import subprocess
import signal
import os
from datetime import datetime


class Recorder:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.output_path = None
        self._temp_video = None  # For GIF conversion
        self._is_gif = False

    def start(self, x, y, w, h, gif_mode=False):
        self._is_gif = gif_mode
        output_dir = self.config.output_dir
        os.makedirs(output_dir, exist_ok=True)

        if gif_mode:
            # For GIF, we record to a temp MP4 then convert
            filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S")
            self._temp_video = os.path.join(output_dir, f"{filename}_temp.mp4")
            self.output_path = os.path.join(output_dir, f"{filename}.gif")
            framerate = self.config.gif_framerate
        else:
            filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.mp4")
            self.output_path = os.path.join(output_dir, filename)
            self._temp_video = None
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
            # Video input with x11grab
            '-f', 'x11grab',
            '-thread_queue_size', '1024',  # Larger buffer to prevent frame drops
            '-probesize', '10M',
            '-framerate', str(framerate),
            '-draw_mouse', '1',
            '-video_size', f'{w}x{h}',
            '-i', f':0.0+{x},{y}',
        ]

        # Add audio capture if configured
        audio_source = self.config.get_resolved_audio_source()
        if audio_source:
            cmd.extend([
                '-f', 'pulse',
                '-thread_queue_size', '512',
                '-i', audio_source,
            ])

        # Video encoding options
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', str(quality),
            '-pix_fmt', 'yuv420p',
            '-vsync', 'cfr',  # Constant frame rate to prevent timing glitches
        ])

        # Audio encoding if we have audio (not for GIF)
        if audio_source and not gif_mode:
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
            print(f"Recording with audio from: {audio_source}")
        else:
            if gif_mode:
                print(f"Recording for GIF (no audio, {framerate} fps)")
            else:
                print("Recording video only (no audio)")

        # Output to temp file for GIF, or final file for MP4
        cmd.append(self._temp_video if gif_mode else self.output_path)
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

        # Convert to GIF if needed
        if self._is_gif and self._temp_video and os.path.exists(self._temp_video):
            self._convert_to_gif()

        return self.output_path

    def _convert_to_gif(self):
        """Convert temp video to GIF using ffmpeg with palette for quality."""
        print("Converting to GIF...")

        # Generate palette for better GIF quality
        palette_path = self._temp_video + ".palette.png"

        # Pass 1: Generate palette
        palette_cmd = [
            'ffmpeg', '-y',
            '-i', self._temp_video,
            '-vf', 'palettegen=stats_mode=diff',
            palette_path
        ]
        subprocess.run(palette_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Pass 2: Create GIF with palette
        gif_cmd = [
            'ffmpeg', '-y',
            '-i', self._temp_video,
            '-i', palette_path,
            '-lavfi', 'paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
            self.output_path
        ]
        subprocess.run(gif_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Clean up temp files
        try:
            os.remove(self._temp_video)
            os.remove(palette_path)
        except OSError:
            pass

        print(f"GIF saved: {self.output_path}")

    def is_recording(self):
        return self.process is not None
