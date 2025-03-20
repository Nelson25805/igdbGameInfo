import sys
import random
import requests
from datetime import datetime, timezone
import qdarkstyle

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QTextEdit, QPushButton,
    QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy
)
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal

import api  # All API logic is centralized in api.py

#########################################
# Worker Class Using QThread Mechanism  #
#########################################

class FetchWorker(QObject):
    finished = pyqtSignal(dict, object, QPixmap)  # Emits: game_data, game_url, pixmap
    error = pyqtSignal(str)

    def __init__(self, desired_width, desired_height, parent=None):
        super().__init__(parent)
        self.desired_width = desired_width
        self.desired_height = desired_height

    def run(self):
        try:
            # Get total games count using the helper in api.py.
            total_games = api.get_games_count()
            if total_games == 0:
                raise Exception("No games found in the database.")
            random_offset = random.randint(0, total_games - 1)
            query = (
                "fields name, summary, release_dates.date, genres.name, "
                "platforms.name, cover.id, cover.image_id, slug; "
                f"offset {random_offset}; limit 1;"
            )
            game_data_list = api.get_game_data(query)
            if not game_data_list:
                raise Exception("API call for game data returned no results.")
            game_data = game_data_list[0]
            # Build game URL from slug
            game_slug = game_data.get('slug')
            game_url = f"https://www.igdb.com/games/{game_slug}" if game_slug else None

            # Process cover image using our api helper.
            # Pass the numeric cover ID instead of the entire cover dictionary.
            cover = game_data.get('cover')
            if cover:
                image_url = api.fetch_cover_image(cover.get("id"))
            else:
                image_url = ""

            if image_url and image_url.startswith("http"):
                image_response = requests.get(image_url, timeout=10)
                if image_response.status_code == 200:
                    image = QImage()
                    image.loadFromData(image_response.content)
                    pixmap = QPixmap.fromImage(image).scaled(
                        self.desired_width, self.desired_height,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                else:
                    pixmap = self.display_no_image()
            else:
                pixmap = self.display_no_image()
        except Exception as e:
            self.error.emit(str(e))
            game_data = {}
            game_url = None
            pixmap = self.display_no_image()
        self.finished.emit(game_data, game_url, pixmap)

    def display_no_image(self):
        # Create a placeholder QPixmap with fixed dimensions.
        image = QImage(self.desired_width, self.desired_height, QImage.Format_RGB32)
        image.fill(Qt.gray)
        painter = QPainter(image)
        painter.setPen(QPen(Qt.white))
        font = QFont("Arial", 16)
        painter.setFont(font)
        painter.drawText(image.rect(), Qt.AlignCenter, "No Image Available")
        painter.end()
        return QPixmap.fromImage(image)

############################################
# Main Window: Random Game Search Interface#
############################################

class RandomGameSearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Random Game Search")
        self.resize(800, 400)
        
        # Set up central widget and main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title Label
        title_label = QLabel("Random Game Section", self)
        title_label.setObjectName("title_label")
        main_layout.addWidget(title_label)
        
        # Horizontal layout: left (game details) and right (image/link)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # LEFT: Grid layout for labels and read-only text areas
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        labels = [
            "Game Name:",
            "Summary:",
            "Platforms:",
            "Genres:",
            "Release Dates:"
        ]
        self.text_areas = []
        for i, label_text in enumerate(labels):
            label = QLabel(label_text, self)
            label.setFont(QFont("Arial", 12))
            grid_layout.addWidget(label, i, 0)
            
            text_area = QTextEdit(self)
            text_area.setReadOnly(True)
            text_area.setFixedHeight(60)
            text_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid_layout.addWidget(text_area, i, 1)
            self.text_areas.append(text_area)
        left_widget = QWidget(self)
        left_widget.setLayout(grid_layout)
        content_layout.addWidget(left_widget, 3)
        
        # RIGHT: Vertical layout for image and game link
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        self.game_image_label = QLabel(self)
        self.game_image_label.setFixedSize(300, 300)
        self.game_image_label.setStyleSheet("border: 1px solid black;")
        self.game_image_label.setAlignment(Qt.AlignCenter)
        self.game_image_label.setPixmap(QPixmap())
        right_layout.addWidget(self.game_image_label)
        
        self.game_link_label = QLabel("Game Link: Not Available", self)
        self.game_link_label.setFont(QFont("Arial", 12))
        self.game_link_label.setAlignment(Qt.AlignCenter)
        self.game_link_label.setOpenExternalLinks(True)
        right_layout.addWidget(self.game_link_label)
        
        right_widget = QWidget(self)
        right_widget.setLayout(right_layout)
        content_layout.addWidget(right_widget, 2)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.fetch_button = QPushButton("Fetch Random Game", self)
        self.fetch_button.setFont(QFont("Arial", 12))
        self.fetch_button.clicked.connect(self.fetch_random_game)
        button_layout.addWidget(self.fetch_button)
        
        self.back_button = QPushButton("Back to Main Page", self)
        self.back_button.setFont(QFont("Arial", 12))
        self.back_button.clicked.connect(self.back_to_main)
        button_layout.addWidget(self.back_button)
        
        main_layout.addLayout(button_layout)
    
    def fetch_random_game(self):
        # Disable buttons while fetching
        self.fetch_button.setEnabled(False)
        self.back_button.setEnabled(False)
        
        # Use fixed image box dimensions for scaling
        desired_width = self.game_image_label.width()
        desired_height = self.game_image_label.height()
        
        # Set up QThread and worker
        self.thread = QThread()
        self.worker = FetchWorker(desired_width, desired_height)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
    
    def on_fetch_finished(self, game_data, game_url, pixmap):
        if game_data:
            self.populate_game_details(game_data)
            self.game_image_label.setPixmap(pixmap)
            if game_url:
                self.game_link_label.setText(f'<a href="{game_url}">View Game on IGDB</a>')
            else:
                self.game_link_label.setText("No link available")
        self.fetch_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def on_fetch_error(self, error_message):
        print("Error during fetch:", error_message)
        self.fetch_button.setEnabled(True)
        self.back_button.setEnabled(True)
    
    def populate_game_details(self, game_data):
        self.text_areas[0].setPlainText(game_data.get("name", "No Information"))
        self.text_areas[1].setPlainText(game_data.get("summary", "No Information"))
        
        platforms = game_data.get("platforms", [])
        platforms_str = ", ".join(platform.get("name", "") for platform in platforms) if platforms else "No Information"
        self.text_areas[2].setPlainText(platforms_str)
        
        genres = game_data.get("genres", [])
        genres_str = ", ".join(genre.get("name", "") for genre in genres) if genres else "No Information"
        self.text_areas[3].setPlainText(genres_str)
        
        release_dates = game_data.get("release_dates", [])
        if release_dates:
            dates_formatted = []
            for date_entry in release_dates:
                if "date" in date_entry:
                    dt = datetime.fromtimestamp(date_entry["date"], tz=timezone.utc)
                    dates_formatted.append(dt.strftime("%d-%m-%Y"))
            release_dates_str = ", ".join(dates_formatted) if dates_formatted else "No Information"
        else:
            release_dates_str = "No Information"
        self.text_areas[4].setPlainText(release_dates_str)
    
    def back_to_main(self):
        from main import MainWindow
        global main_window
        main_window = MainWindow()
        main_window.show()
        self.close()
    
    def closeEvent(self, event):
        # Ensure any running thread is properly stopped before closing.
        try:
            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()
        except Exception as e:
            print("Error during thread shutdown:", e)
        event.accept()
        
def load_stylesheet(file_path):
    with open(file_path, "r") as f:
        return f.read()

def main():
    app = QApplication(sys.argv)
    # Load the dark theme first.
    dark_style = qdarkstyle.load_stylesheet_pyqt5()
    # Then load your size styling overrides.
    size_style = load_stylesheet("style.qss")
    
    # Combine them (size_style overrides where applicable)
    app.setStyleSheet(dark_style + "\n" + size_style)
    window = RandomGameSearchWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
