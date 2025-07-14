import sys
import json
import threading
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer

import folium
import os
from PyQt5.QtWidgets import QPushButton, QHBoxLayout

DATA_FILE = "drone_status.json"
HOME_LOCATION = [12.34, 56.78]

class DroneMapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Swarm Map Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.web_view = QWebEngineView()
        self.last_bounds = None
        self.last_center = HOME_LOCATION
        self.last_zoom = 15
        # Buttons
        self.btn_home = QPushButton("Zoom to Home")
        self.btn_fit = QPushButton("Fit All Drones")
        self.btn_home.clicked.connect(self.zoom_home)
        self.btn_fit.clicked.connect(self.zoom_fit)
        # Layout
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_home)
        btn_layout.addWidget(self.btn_fit)
        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self.web_view)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_map)
        self.timer.start(2000)  # Update every 2 seconds
        self.update_map()

    def update_map(self):
        # Load drone data
        if not os.path.exists(DATA_FILE):
            drones = {}
        else:
            with open(DATA_FILE, "r") as f:
                try:
                    drones = json.load(f)
                except Exception:
                    drones = {}
        # Use last center/zoom unless user pressed a button
        center = self.last_center
        zoom = self.last_zoom
        m = folium.Map(location=center, zoom_start=zoom)
        bounds = []
        for drone_id, status in drones.items():
            latlon = [status["gps"]["lat"], status["gps"]["lon"]]
            folium.Marker(
                latlon,
                popup=f"Drone {drone_id}<br>Baro: {status['baro']}<br>Vel: {status['velocity']}"
            ).add_to(m)
            bounds.append(latlon)
        # Save bounds for fit
        self.last_bounds = bounds
        m.save("map.html")
        self.web_view.load(QUrl.fromLocalFile(os.path.abspath("map.html")))

    def zoom_home(self):
        self.last_center = HOME_LOCATION
        self.last_zoom = 15
        self.update_map()

    def zoom_fit(self):
        # Fit all drones
        if self.last_bounds and len(self.last_bounds) > 0:
            lats = [lat for lat, lon in self.last_bounds]
            lons = [lon for lat, lon in self.last_bounds]
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
            self.last_center = center
            # Estimate zoom: crude, but works for small areas
            self.last_zoom = 12 if max_lat - min_lat > 0.01 or max_lon - min_lon > 0.01 else 15
            self.update_map()

if __name__ == "__main__":
    from PyQt5.QtCore import QUrl
    app = QApplication(sys.argv)
    window = DroneMapWindow()
    window.show()
    sys.exit(app.exec_())
