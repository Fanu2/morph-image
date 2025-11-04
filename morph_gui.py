import sys
import subprocess
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QFileDialog, QMessageBox, QComboBox, QTextEdit, QSlider, QHBoxLayout, QCheckBox
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QUrl, Qt


class ImageMorphGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G'MIC + FFmpeg Image Morph GUI (Loop Version)")
        self.resize(900, 780)

        self.image1_path = ''
        self.image2_path = ''
        self.output_path = 'output.mp4'
        self.loop_enabled = True

        # GUI Elements
        self.label1 = QLabel("Image 1: Not selected")
        self.label2 = QLabel("Image 2: Not selected")

        self.btn1 = QPushButton("Select Image 1")
        self.btn2 = QPushButton("Select Image 2")
        self.btn1.clicked.connect(self.select_image1)
        self.btn2.clicked.connect(self.select_image2)

        self.duration_label = QLabel("Morph Duration (seconds):")
        self.duration_input = QLineEdit('3')

        self.frames_label = QLabel("Number of intermediate frames:")
        self.frames_input = QLineEdit('30')

        self.output_label = QLabel("Output filename:")
        self.output_input = QLineEdit(self.output_path)

        self.format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "gif"])

        self.loop_checkbox = QCheckBox("Loop Playback")
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.stateChanged.connect(self.toggle_loop)

        self.run_button = QPushButton("Run G'MIC Morph + FFmpeg")
        self.run_button.clicked.connect(self.run_morph)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # Video/GIF preview
        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

        self.gif_label = QLabel()
        self.gif_label.setVisible(False)
        self.gif_movie = None

        # Playback controls
        self.scrubber = QSlider(Qt.Horizontal)
        self.scrubber.setRange(0, 100)
        self.scrubber.sliderMoved.connect(self.scrub_video)

        self.media_player.positionChanged.connect(self.update_slider)
        self.media_player.durationChanged.connect(self.set_slider_range)

        self.play_button = QPushButton("Play Preview")
        self.play_button.clicked.connect(self.play_preview)

        self.step_back_button = QPushButton("◀ Frame -1")
        self.step_forward_button = QPushButton("Frame +1 ▶")
        self.step_back_button.clicked.connect(self.step_back)
        self.step_forward_button.clicked.connect(self.step_forward)

        # Layout setup
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.step_back_button)
        control_layout.addWidget(self.scrubber)
        control_layout.addWidget(self.step_forward_button)

        layout = QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.btn1)
        layout.addWidget(self.label2)
        layout.addWidget(self.btn2)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.duration_input)
        layout.addWidget(self.frames_label)
        layout.addWidget(self.frames_input)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_input)
        layout.addWidget(self.format_label)
        layout.addWidget(self.format_combo)
        layout.addWidget(self.loop_checkbox)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_output)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.video_widget)
        layout.addWidget(self.gif_label)
        layout.addLayout(control_layout)
        layout.addWidget(self.play_button)

        self.setLayout(layout)

    # ---------- Utility Functions ----------
    def select_image1(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select First Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file:
            self.image1_path = file
            self.label1.setText(f"Image 1: {file}")

    def select_image2(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Second Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file:
            self.image2_path = file
            self.label2.setText(f"Image 2: {file}")

    def log(self, text):
        self.log_output.append(text)
        QApplication.processEvents()

    # ---------- Core Process ----------
    def run_morph(self):
        if not self.image1_path or not self.image2_path:
            QMessageBox.warning(self, "Error", "Please select both images.")
            return

        frames = self.frames_input.text()
        output = self.output_input.text()
        fmt = self.format_combo.currentText()

        if not output.endswith(fmt):
            output = f"{os.path.splitext(output)[0]}.{fmt}"
            self.output_input.setText(output)

        self.log_output.clear()

        # Frame directory
        frames_dir = os.path.join(os.getcwd(), 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        frame_pattern = os.path.join(frames_dir, 'frame_%04d.png')

        # Cleanup old frames
        for f in os.listdir(frames_dir):
            if f.startswith("frame_") and f.endswith(".png"):
                os.remove(os.path.join(frames_dir, f))

        # G'MIC morph
        gmic_cmd = [
            'gmic', self.image1_path, self.image2_path,
            '-morph', str(frames),
            '-o', frame_pattern
        ]

        self.log(f"Running: {' '.join(gmic_cmd)}")
        try:
            subprocess.run(gmic_cmd, check=True)
            self.log("✅ G'MIC morph completed.")
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Error running G'MIC: {e}")
            return

        # Check frames
        files = [f for f in os.listdir(frames_dir) if f.startswith("frame_")]
        if not files:
            self.log("❌ No frames found! Check G'MIC output.")
            return
        self.log(f"🖼️ {len(files)} frames found in {frames_dir}")

        # FPS from duration
        try:
            frames_count = int(frames)
            duration_sec = float(self.duration_input.text())
            fps = max(1, round(frames_count / duration_sec))
        except ValueError:
            fps = 30

        self.log(f"🎞️ Target playback: {fps} fps for {duration_sec}s total")

        # FFmpeg command
        if fmt == 'mp4':
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-framerate', str(fps),
                '-pattern_type', 'glob', '-i', os.path.join(frames_dir, 'frame_*.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output
            ]
        else:
            # Palette generation for GIF
            subprocess.run([
                'ffmpeg', '-y', '-framerate', str(fps),
                '-pattern_type', 'glob', '-i', os.path.join(frames_dir, 'frame_*.png'),
                '-vf', 'palettegen', 'palette.png'
            ], check=True)
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-framerate', str(fps),
                '-pattern_type', 'glob', '-i', os.path.join(frames_dir, 'frame_*.png'),
                '-i', 'palette.png', '-lavfi', 'paletteuse', output
            ]

        self.log(f"Running: {' '.join(ffmpeg_cmd)}")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            self.log(f"✅ Output saved to {output}")
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Error running ffmpeg: {e}")
            return

        QMessageBox.information(self, "Success", f"Morph completed! Output saved as {output}")
        self.output_path = output
        self.output_input.setText(output)

        # 🔁 Auto-preview with loop
        self.play_preview()

    # ---------- Playback ----------
    def play_preview(self):
        output = self.output_input.text()
        if not os.path.exists(output):
            QMessageBox.warning(self, "Error", "No output file found to preview.")
            return

        if output.endswith('.mp4'):
            self.gif_label.setVisible(False)
            self.video_widget.setVisible(True)
            url = QUrl.fromLocalFile(os.path.abspath(output))
            self.media_player.setMedia(QMediaContent(url))
            self.media_player.play()
            self.log("🎬 Auto-playing MP4 preview...")
        elif output.endswith('.gif'):
            self.video_widget.setVisible(False)
            self.gif_label.setVisible(True)
            self.gif_movie = QMovie(output)
            if self.loop_enabled:
                self.gif_movie.setCacheMode(QMovie.CacheAll)
                self.gif_movie.setSpeed(100)
                self.gif_movie.setLoopCount(0)  # Infinite loop
            else:
                self.gif_movie.setLoopCount(1)
            self.gif_label.setMovie(self.gif_movie)
            self.gif_movie.start()
            self.log("🎞️ Auto-playing GIF preview...")

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia and self.loop_enabled:
            self.media_player.setPosition(0)
            self.media_player.play()

    def toggle_loop(self, state):
        self.loop_enabled = bool(state)
        self.log(f"🔁 Loop Playback {'enabled' if self.loop_enabled else 'disabled'}")

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

    def step_back(self):
        pos = self.media_player.position() - 100
        self.media_player.setPosition(max(0, pos))

    def step_forward(self):
        pos = self.media_player.position() + 100
        self.media_player.setPosition(min(pos, self.media_player.duration()))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageMorphGUI()
    window.show()
    sys.exit(app.exec_())
