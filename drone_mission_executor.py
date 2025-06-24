from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
import threading
from shapely.geometry import Polygon, Point
from area_splitter import get_area_coordinates
from random_target_generator import RandomTargetGenerator

import math

# === SETTINGS ===
DRONE_CONNECTION = 'udp:127.0.0.1:14550'
TARGET_ALTITUDE = 10
AREA_NUMBER = 1  # This drone is assigned to area 1

# === INIT ===
print("Connecting to drone...")
vehicle = connect(DRONE_CONNECTION, wait_ready=True)
print("Drone connected.")

# === Load assigned area as Polygon ===
area_coords = get_area_coordinates(AREA_NUMBER)
area_poly = Polygon([(lon, lat) for lat, lon in area_coords])  # lon, lat order for Shapely

# === Setup random target generator ===
generator = RandomTargetGenerator()

# === Coordinate Queue ===
target_queue = []
queue_lock = threading.Lock()

# === Arm and Takeoff ===
def arm_and_takeoff(alt):
    print("Arming motors...")
    vehicle.mode = VehicleMode("GUIDED")
    time.sleep(3)
    vehicle.armed = True
    while not vehicle.armed:
        print("Waiting for arming...")
        time.sleep(1)
    print("Taking off...")
    vehicle.simple_takeoff(alt)
    while True:
        current_alt = vehicle.location.global_relative_frame.alt
        print(f"Altitude: {current_alt:.2f}")
        if current_alt >= alt * 0.95:
            print("Reached target altitude.")
            break
        time.sleep(1)

# === Distance Calculator ===
def get_distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# === Background Thread to Fetch Random Targets ===
def fetch_targets():
    while True:
        lat, lon = generator.get_random_target()
        point = Point(lon, lat)
        if area_poly.contains(point):
            with queue_lock:
                print(f"[+] New target in area: {lat:.6f}, {lon:.6f}")
                target_queue.append((lat, lon))
        else:
            print(f"[-] Ignored target outside area: {lat:.6f}, {lon:.6f}")

# === Mission Execution ===
def fly_to_targets():
    while True:
        with queue_lock:
            if not target_queue:
                continue
            # Current location
            curr_lat = vehicle.location.global_relative_frame.lat
            curr_lon = vehicle.location.global_relative_frame.lon

            # Sort by nearest target
            target_queue.sort(key=lambda t: get_distance_meters(curr_lat, curr_lon, t[0], t[1]))
            lat, lon = target_queue.pop(0)

            remaining = len(target_queue)

        print(f"\n➡️  Flying to target: {lat:.6f}, {lon:.6f}")
        print(f"🧭 Remaining targets after this: {remaining}")
        vehicle.mode = VehicleMode("GUIDED")
        vehicle.simple_goto(LocationGlobalRelative(lat, lon, TARGET_ALTITUDE))
        
        # Wait to reach
        while True:
            current = vehicle.location.global_relative_frame
            dist = get_distance_meters(current.lat, current.lon, lat, lon)
            print(f"   ↪ Distance to target: {dist:.2f} m", end="\r")
            if dist < 2.0:
                print("\n✅ Reached target. Hovering...")
                break
            time.sleep(1)

        time.sleep(5)  # Hover at the location
        print("🕔 Hover complete. Moving to next...\n")

# === RUN ===
arm_and_takeoff(TARGET_ALTITUDE)

# Start target generator in the background
fetch_thread = threading.Thread(target=fetch_targets, daemon=True)
fetch_thread.start()

# Start drone navigation loop
fly_to_targets()

