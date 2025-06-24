import random
import time
import threading
from shapely.geometry import Polygon, Point
from xml.etree import ElementTree as ET

KML_PATH = 'kml_files/30ha.kml'

class RandomTargetGenerator:
    def __init__(self, kml_path=KML_PATH):
        self.kml_path = kml_path
        self.polygon = self._read_polygon()
        self.lock = threading.Lock()  # For thread safety

    def _read_polygon(self) -> Polygon:
        tree = ET.parse(self.kml_path)
        coord_text = tree.find('.//{*}coordinates').text.strip()
        coords = [tuple(map(float, p.split(',')[:2])) for p in coord_text.split()]
        if not coords:
            raise RuntimeError("KML contains no coordinates")
        return Polygon(coords)

    def _random_point_within(self) -> Point:
        minx, miny, maxx, maxy = self.polygon.bounds
        while True:
            rand_point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
            if self.polygon.contains(rand_point):
                return rand_point

    def get_random_target(self):
        with self.lock:
            delay = random.randint(1, 7)
            print(f"[Target Generator] Waiting {delay} seconds before providing next target...")
            time.sleep(delay)
            point = self._random_point_within()
            lat = point.y
            lon = point.x
            return lat, lon

# Only used if running directly for test/debug
if __name__ == '__main__':
    generator = RandomTargetGenerator()
    for i in range(5):
        lat, lon = generator.get_random_target()
        print(f"Random Target {i+1}: Latitude = {lat:.6f}, Longitude = {lon:.6f}")

