from dronekit import connect, VehicleMode, Command
from pymavlink import mavutil
from shapely.ops import split
from shapely.geometry import Polygon, LineString
import time, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DroneCommon")

def arm_and_takeoff(vehicle, target_altitude):
    vehicle.mode = VehicleMode("GUIDED")
    time.sleep(2)
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(1)
    vehicle.simple_takeoff(target_altitude)
    while True:
        if vehicle.location.global_relative_frame.alt >= target_altitude * 0.95:
            break
        time.sleep(1)

def split_polygon_by_index(poly: Polygon, total_parts: int, index: int):
    minx, miny, maxx, maxy = poly.bounds
    step = (maxx - minx) / total_parts
    slice_line = LineString([
        (minx + index * step, miny),
        (minx + index * step, maxy)
    ])
    return split(poly, slice_line)

def upload_and_execute(vehicle, wps):
    cmds = vehicle.commands
    cmds.clear()
    lat0, lon0, alt0 = wps[0]
    cmds.add(Command(0,0,0,mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                     mavutil.mavlink.MAV_CMD_DO_SET_HOME, 0,0,1,0,0,0,
                     lat0, lon0, alt0))
    cmds.add(Command(0,0,0,mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                     mavutil.mavlink.MAV_CMD_NAV_VTOL_TAKEOFF, 0,0,0,0,0,0,
                     lat0, lon0, alt0))
    for lat, lon, alt in wps[1:]:
        cmds.add(Command(0,0,0,mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                         mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0,0,0,0,0,0,
                         lat, lon, alt))
    cmds.add(Command(0,0,0,mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                     mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0,0,0,0,0,0,
                     0,0,0))
    cmds.upload()
    vehicle.mode = VehicleMode("AUTO")

