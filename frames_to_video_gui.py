import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QFileDialog, QMessageBox, QComboBox, QTextEdit, QSlider, QHBoxLayout
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QUrl, Qt


class FramesToVideoGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frames to Video (FFmpeg GUI)")
        self.resize(800, 700)

        self.frames_dir = "/home/jasvir/Pictures/frames"
        self.output_path = "/home/jasvir/Pictures/output.mp4"

        # Widgets
        self.frames_label = QLabel(f"Frames directory: {self.frames_dir}")
        self.output_label = QLabel("Output filename:")
        self.output_input = QLineEdit(self.output_path)

        self.framerate_label = QLabel("Frame rate (fps):")
        self.framerate_input = QLineEdit("30")

        self.format_label = QLabel("Output format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "gif"])

        self.run_button = QPushButton("Combine Frames with FFmpeg")
        self.run_button.clicked.connect(self.run_ffmpeg)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # Preview section
        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)

        self.gif_label = QLabel()
        self.gif_label.setVisible(False)

        # Playback controls
        self.scrubber = QSlider(Qt.Horizontal)
        self.scrubber.setRange(0, 100)
        self.scrubber.sliderMoved.connect(self.scrub_video)
        self.media_player.positionChanged.connect(self.update_slider)
        self.media_player.durationChanged.connect(self.set_slider_range)

        self.play_button = QPushButton("Play Preview")
        self.play_button.clicked.connect(self.play_preview)

        # Layout
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.scrubber)

        layout = QVBoxLayout()
        layout.addWidget(self.frames_label)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_input)
        layout.addWidget(self.framerate_label)
        layout.addWidget(self.framerate_input)
        layout.addWidget(self.format_label)
        layout.addWidget(self.format_combo)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_output)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.video_widget)
        layout.addWidget(self.gif_label)
        layout.addLayout(control_layout)
        layout.addWidget(self.play_button)

        self.setLayout(layout)

    def log(self, text):
        self.log_output.append(text)
        QApplication.processEvents()

    def run_ffmpeg(self):
        frames_dir = self.frames_dir
        frame_pattern = os.path.join(frames_dir, "frame_%04d.png")

        if not os.path.exists(frames_dir):
            QMessageBox.warning(self, "Error", f"Frames directory not found:\n{frames_dir}")
            return

        files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
        if not files:
            QMessageBox.warning(self, "Error", f"No .png frames found in {frames_dir}")
            return

        first_frame = os.path.join(frames_dir, files[0])
        self.log(f"✅ Found {len(files)} frames.")
        self.log(f"First frame: {first_frame}")

        framerate = self.framerate_input.text().strip()
        fmt = self.format_combo.currentText()
        output = self.output_input.text().strip()

        if not output.endswith(fmt):
            output = f"{os.path.splitext(output)[0]}.{fmt}"
            self.output_input.setText(output)

        self.log_output.clear()

        if fmt == "mp4":
            cmd = [
                "ffmpeg", "-y", "-framerate", framerate,
                "-start_number", "0",
                "-i", frame_pattern,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", output
            ]
        else:
            # Create GIF with palette for quality
            subprocess.run([
                "ffmpeg", "-y", "-framerate", framerate,
                "-i", frame_pattern, "-vf", "palettegen", "palette.png"
            ], check=True)
            cmd = [
                "ffmpeg", "-y", "-framerate", framerate,
                "-i", frame_pattern, "-i", "palette.png",
                "-lavfi", "paletteuse", output
            ]

        self.log(f"Running FFmpeg:\n{' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            self.log(f"✅ Video saved: {output}")
            QMessageBox.information(self, "Success", f"Output created:\n{output}")
            self.output_path = output
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Error running FFmpeg: {e}")

    def play_preview(self):
        output = self.output_input.text()
        if not os.path.exists(output):
            QMessageBox.warning(self, "Error", "No output file found to preview.")
            return

        if output.endswith(".mp4"):
            self.gif_label.setVisible(False)
            self.video_widget.setVisible(True)
            url = QUrl.fromLocalFile(os.path.abspath(output))
            self.media_player.setMedia(QMediaContent(url))
            self.media_player.play()
        elif output.endswith(".gif"):
            self.video_widget.setVisible(False)
            self.gif_label.setVisible(True)
            movie = QMovie(output)
            self.gif_label.setMovie(movie)
            movie.start()

    def scrub_video(self, position):
        if self.media_player.duration() > 0:
            new_pos = int((position / 100) * self.media_player.duration())
            self.media_player.setPosition(new_pos)

    def update_slider(self, position):
        if self.media_player.duration() > 0:
            value = int((position / self.media_player.duration()) * 100)
            self.scrubber.blockSignals(True)
            self.scrubber.setValue(value)
            self.scrubber.blockSignals(False)

    def set_slider_range(self, duration):
        self.scrubber.setEnabled(duration > 0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FramesToVideoGUI()
    window.show()
    sys.exit(app.exec_())

