import sys
import subprocess
import os
import glob
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QFileDialog, QMessageBox, QComboBox, QTextEdit, QSlider, QHBoxLayout
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import QUrl, Qt


class ImageMorphGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G'MIC + FFmpeg Image Morph GUI with Frame Control")
        self.resize(950, 800)

        self.image1_path = ''
        self.image2_path = ''
        self.output_path = 'output.mp4'
        self.frames_dir = os.path.join(os.getcwd(), 'frames')
        os.makedirs(self.frames_dir, exist_ok=True)

        # GUI elements
        self.label1 = QLabel("Image 1: Not selected")
        self.label2 = QLabel("Image 2: Not selected")

        self.btn1 = QPushButton("Select Image 1")
        self.btn2 = QPushButton("Select Image 2")
        self.btn1.clicked.connect(self.select_image1)
        self.btn2.clicked.connect(self.select_image2)

        self.frames_label = QLabel("Number of intermediate frames:")
        self.frames_input = QLineEdit('30')

        self.output_label = QLabel("Output filename:")
        self.output_input = QLineEdit(self.output_path)

        self.format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "gif"])

        self.run_button = QPushButton("Run Morph + FFmpeg")
        self.run_button.clicked.connect(self.run_morph)

        self.preview_button = QPushButton("Preview Frames")
        self.preview_button.clicked.connect(self.preview_frames)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # Video/GIF preview
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

        # Layouts
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.scrubber)

        layout = QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.btn1)
        layout.addWidget(self.label2)
        layout.addWidget(self.btn2)
        layout.addWidget(self.frames_label)
        layout.addWidget(self.frames_input)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_input)
        layout.addWidget(self.format_label)
        layout.addWidget(self.format_combo)
        layout.addWidget(self.run_button)
        layout.addWidget(self.preview_button)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_output)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.video_widget)
        layout.addWidget(self.gif_label)
        layout.addLayout(control_layout)
        layout.addWidget(self.play_button)

        self.setLayout(layout)

    # ========== Image Selection ==========
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

    # ========== Main Morph Process ==========
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
        os.makedirs(self.frames_dir, exist_ok=True)

        frame_pattern = os.path.join(self.frames_dir, 'frame_%04d.png')

        # Clean old frames
        for f in glob.glob(os.path.join(self.frames_dir, "*.png")):
            os.remove(f)

        # Run G'MIC
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

        all_frames = sorted(glob.glob(os.path.join(self.frames_dir, "*.png")))
        if not all_frames:
            self.log("❌ No frames generated! FFmpeg will not run.")
            return

        # FFmpeg command using glob pattern
        if fmt == 'mp4':
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-framerate', '30', '-pattern_type', 'glob',
                '-i', os.path.join(self.frames_dir, '*.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output
            ]
        else:
            subprocess.run([
                'ffmpeg', '-y', '-framerate', '15', '-pattern_type', 'glob',
                '-i', os.path.join(self.frames_dir, '*.png'),
                '-vf', 'palettegen', 'palette.png'
            ], check=True)
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-framerate', '15', '-pattern_type', 'glob',
                '-i', os.path.join(self.frames_dir, '*.png'),
                '-i', 'palette.png', '-lavfi', 'paletteuse', output
            ]

        self.log(f"Running: {' '.join(ffmpeg_cmd)}")

        try:
            subprocess.run(ffmpeg_cmd, check=True)
            self.log(f"🎉 Output saved to {output}")
        except subprocess.CalledProcessError as e:
            self.log(f"❌ FFmpeg error: {e}")
            return

        QMessageBox.information(self, "Success", f"Morph completed! Output saved as {output}")
        self.output_path = output
        self.output_input.setText(output)

    # ========== Frame Preview ==========
    def preview_frames(self):
        all_frames = sorted(glob.glob(os.path.join(self.frames_dir, "*.png")))
        if not all_frames:
            QMessageBox.warning(self, "No Frames", "No frames found to preview. Please run morph first.")
            return

        preview_window = FramePreviewWindow(all_frames)
        preview_window.exec_()

    # ========== Video Controls ==========
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
        elif output.endswith('.gif'):
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


# ========== Frame Preview Window ==========
from PyQt5.QtWidgets import QDialog

class FramePreviewWindow(QDialog):
    def __init__(self, frames):
        super().__init__()
        self.frames = frames
        self.index = 0
        self.setWindowTitle("Frame Preview")
        self.resize(600, 700)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        self.prev_btn = QPushButton("⟨ Previous")
        self.next_btn = QPushButton("Next ⟩")
        self.prev_btn.clicked.connect(self.show_prev)
        self.next_btn.clicked.connect(self.show_next)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addLayout(nav_layout)
        self.setLayout(layout)

        self.show_frame()

    def show_frame(self):
        if 0 <= self.index < len(self.frames):
            pixmap = QPixmap(self.frames[self.index])
            self.image_label.setPixmap(pixmap.scaled(
                500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.setWindowTitle(f"Frame Preview ({self.index+1}/{len(self.frames)})")

    def show_prev(self):
        if self.index > 0:
            self.index -= 1
            self.show_frame()

    def show_next(self):
        if self.index < len(self.frames) - 1:
            self.index += 1
            self.show_frame()


# ========== Run App ==========
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageMorphGUI()
    window.show()
    sys.exit(app.exec_())
