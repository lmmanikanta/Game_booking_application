import sys
import os
# ======================================================================
# ADD THIS IMPORT FOR THE FIX
from PyQt5.QtWidgets import QSizePolicy
# ======================================================================
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QMessageBox, QStatusBar
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QIcon
from PyQt5.QtCore import Qt, QPoint, QRect, QThread, pyqtSignal, QObject

import cv2
from moviepy.editor import VideoFileClip

# ======================================================================
# HARDCODED FILE PATHS
# --- Change these to your desired input and output files ---
INPUT_VIDEO_PATH = "yt22.mp4"
OUTPUT_VIDEO_PATH = "output.mp4"
# ======================================================================


# --- Worker Thread for MoviePy Processing (No changes needed here) ---
class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_path, output_path, crop_rect):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.crop_rect = crop_rect

    def run(self):
        try:
            with VideoFileClip(self.input_path) as clip:
                x1, y1, x2, y2 = self.crop_rect
                cropped_clip = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
                cropped_clip.write_videofile(
                    self.output_path, codec="libx264", audio_codec="aac"
                )
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"An error occurred: {str(e)}")


# --- Custom QLabel for Drawing the Selection Rectangle (No changes needed here) ---
class SelectionLabel(QLabel):
    area_selected = pyqtSignal(QRect)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.begin, self.end = QPoint(), QPoint()
        self.is_selecting = False
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.begin = event.pos()
            self.end = self.begin
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_selecting:
            self.is_selecting = False
            self.area_selected.emit(QRect(self.begin, self.end).normalized())
            self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_selecting:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            painter.drawRect(QRect(self.begin, self.end).normalized())


# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Cropper")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon())

        self.crop_area = None
        self.thread = None
        self.worker = None
        self.original_pixmap = QPixmap()

        self.init_ui()
        self.load_initial_video() # Automatically load the video on start

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # UI is simplified - no more Open/Save buttons
        self.preview_label = SelectionLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        
        # ======================================================================
        # THE FIX: Change the Size Policy of the preview label.
        # This tells the layout to ignore the label's preferred (huge) size
        # and instead just give it all available space. This stops the window
        # from trying to resize beyond the screen limits.
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # ======================================================================

        self.preview_label.setScaledContents(False)
        self.preview_label.area_selected.connect(self.on_area_selected)
        main_layout.addWidget(self.preview_label, 1)

        self.start_btn = QPushButton("Start Cropping")
        self.start_btn.clicked.connect(self.start_cropping)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("font-size: 16px; padding: 10px;")
        main_layout.addWidget(self.start_btn)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

    def load_initial_video(self):
        """Loads the hardcoded video file when the app starts."""
        if not os.path.exists(INPUT_VIDEO_PATH):
            self.show_error(f"Input file not found: {INPUT_VIDEO_PATH}")
            self.preview_label.setText("Input file not found.")
            return

        self.status_bar.showMessage(f"Loaded: {os.path.basename(INPUT_VIDEO_PATH)}")
        self.load_and_display_first_frame()

    def load_and_display_first_frame(self):
        try:
            cap = cv2.VideoCapture(INPUT_VIDEO_PATH)
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                q_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self.original_pixmap = QPixmap.fromImage(q_image)
                self.update_preview_pixmap()
            else:
                self.show_error("Could not read the first frame of the video.")
        except Exception as e:
            self.show_error(f"Error loading video frame: {e}")

    def update_preview_pixmap(self):
        if self.original_pixmap.isNull():
            return
        scaled_pixmap = self.original_pixmap.scaled(
            self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview_pixmap()

    def on_area_selected(self, rect):
        pixmap = self.preview_label.pixmap()
        if not pixmap or pixmap.isNull(): return
            
        pw, ph = pixmap.width(), pixmap.height() 
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        scale_x, scale_y = ow / pw, oh / ph
        offset_x = (self.preview_label.width() - pw) / 2
        offset_y = (self.preview_label.height() - ph) / 2
        
        x1 = int((rect.x() - offset_x) * scale_x)
        y1 = int((rect.y() - offset_y) * scale_y)
        x2 = int((rect.right() - offset_x) * scale_x)
        y2 = int((rect.bottom() - offset_y) * scale_y)

        x1, x2 = sorted([max(0, x1), min(ow, x2)])
        y1, y2 = sorted([max(0, y1), min(oh, y2)])

        self.crop_area = (x1, y1, x2, y2)
        self.status_bar.showMessage(f"Area selected: ({x1}, {y1}) to ({x2}, {y2})")
        self.start_btn.setEnabled(True)

    def start_cropping(self):
        self.start_btn.setEnabled(False)
        self.status_bar.showMessage("Processing... this may take a while.")

        self.thread = QThread()
        self.worker = Worker(INPUT_VIDEO_PATH, OUTPUT_VIDEO_PATH, self.crop_area)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_cropping_finished)
        self.worker.error.connect(self.on_cropping_error)
        self.thread.start()

    def on_cropping_finished(self):
        msg = f"Cropping complete! File saved to {OUTPUT_VIDEO_PATH}"
        self.status_bar.showMessage(msg)
        QMessageBox.information(self, "Success", msg)
        self.cleanup_thread()

    def on_cropping_error(self, error_message):
        self.status_bar.showMessage("An error occurred during processing.")
        self.show_error(error_message)
        self.cleanup_thread()
    
    def cleanup_thread(self):
        self.thread.quit()
        self.thread.wait()
        self.thread, self.worker = None, None
        self.start_btn.setEnabled(True)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())