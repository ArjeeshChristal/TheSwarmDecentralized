# test_workflow.py

import warnings
warnings.filterwarnings("ignore", message="Unable to import Axes3D")

import math
import os
import time
import logging
from dronekit import connect, VehicleMode, Command
from pymavlink import mavutil
from shapely.geometry import Polygon, LineString, MultiLineString
from xml.etree import ElementTree as ET
import matplotlib.pyplot as plt

from mapping_params import (
    calculate_mapping_params,
    meters_to_deg_lat,
    meters_to_deg_lon,
    haversine_distance
)

# --- CONFIGURATION ---
CONNECTION_STRING = 'udp:127.0.0.1:14551'
KML_PATH         = 'kml_files/30ha.kml'
ALTITUDE_M       = 50      # meters
OVERLAP_PCT      = 15
SIDELAP_PCT      = 15
# ----------------------

# ——— Performance parameters ———
STALL_SPEED       = 15.0    # m/s — minimum safe airspeed
CRUISE_SPEED      = 18.0    # m/s — planned nominal cruise
AIRCRAFT_WEIGHT_KG = 8.0    # kg
# ————————————————————————


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Survey")

class QuadplaneSurvey:
    def __init__(self):
        self.vehicle = None

    def connect_and_configure(self):
        logger.info(f"Connecting to vehicle on {CONNECTION_STRING}")
        self.vehicle = connect(CONNECTION_STRING, wait_ready=True, baud=115200)
        self.vehicle.wait_ready('last_heartbeat', timeout=15)
        logger.info("Vehicle heartbeat OK")

        # 1) Speed envelope
        params = {
            'AIRSPEED_MIN':    1700,  # 17 m/s
            'AIRSPEED_CRUISE': 1800,  # 18 m/s
            'AIRSPEED_MAX':    2000,  # 20 m/s
            'SCALING_SPEED':   1800,  # PID scale
            'WPNAV_SPEED':     1800,  # Navigator default cruise
            # 2) Bank & attitude limits
            'ROLL_LIMIT_DEG':  50,
            'PTCH_LIM_MAX_DEG': 25,
            'PTCH_LIM_MIN_DEG': -10,
            # 3) TECS tuning: bias speed hold
            'TECS_SPEEDWEIGHT': 2.0,  # >1 → stronger speed hold
        }

        for p, v in params.items():
            if p in self.vehicle.parameters:
                try:
                    self.vehicle.parameters[p] = v
                    logger.info(f"Set {p} = {v}")
                except:
                    logger.warning(f"Could not set {p}")
            else:
                logger.warning(f"{p} not supported – skipping")

        # Verify critical ones
        self.verify_params(params, critical={'AIRSPEED_CRUISE','WPNAV_SPEED','TECS_SPEEDWEIGHT'})



    def verify_params(self, desired: dict, critical: set):
        """
        For each param in `desired`, if it exists on the vehicle,
        check that its value matches. If a critical param is missing
        or mismatched, raise. Otherwise warn.
        """
        present = set(self.vehicle.parameters.keys())
        failed = False

        for p, want in desired.items():
            if p not in present:
                logger.warning(f"Param {p} not supported by this firmware—skipping verification")
                continue

            got = float(self.vehicle.parameters[p])
            if abs(got - float(want)) > 1e-3:
                msg = f"Param {p} = {got} (!= {want})"
                if p in critical:
                    logger.error(msg)
                    failed = True
                else:
                    logger.warning(msg)
            else:
                logger.info(f"Param {p} verified: {got}")

        if failed:
            raise RuntimeError("One or more *critical* parameters failed to apply")

    def read_polygon(self) -> Polygon:
        tree = ET.parse(KML_PATH)
        coord_text = tree.find('.//{*}coordinates').text.strip()
        coords = [tuple(map(float, p.split(',')[:2])) for p in coord_text.split()]
        if not coords:
            raise RuntimeError("KML contains no coordinates")
        return Polygon(coords)

    def generate_lawnmower(self, poly: Polygon):
        # derive mapping
        mp = calculate_mapping_params(ALTITUDE_M, OVERLAP_PCT, SIDELAP_PCT)
        swath_w = mp['ground_width_m']           # full swath width (m)
        lane_spacing_m = swath_w * (1 - SIDELAP_PCT/100.0)

        minx, miny, maxx, maxy = poly.bounds
        midlat = (miny + maxy) / 2

        # choose orientation by real‐world dimensions
        width_m  = haversine_distance(miny, minx, miny, maxx)
        height_m = haversine_distance(miny, minx, maxy, minx)
        horizontal = width_m >= height_m

        # compute degree spacing
        if horizontal:
            dlat = meters_to_deg_lat(lane_spacing_m)
        else:
            dlon = meters_to_deg_lon(lane_spacing_m, midlat)

        # build parallel lines
        lines = []
        if horizontal:
            y = miny
            while y <= maxy + dlat/2:
                lines.append(LineString([(minx, y), (maxx, y)]))
                y += dlat
        else:
            x = minx
            while x <= maxx + dlon/2:
                lines.append(LineString([(x, miny), (x, maxy)]))
                x += dlon

        # build waypoints: start at centroid
        pts = [(poly.centroid.y, poly.centroid.x, ALTITUDE_M)]
        flip = False
        for ln in lines:
            inter = poly.intersection(ln)
            segments = []
            if isinstance(inter, LineString):
                segments = [inter]
            elif isinstance(inter, MultiLineString):
                segments = list(inter.geoms)
            for seg in segments:
                coords = list(seg.coords)
                coords.sort(key=lambda c: c[0], reverse=flip)
                for lon, lat in coords:
                    pts.append((lat, lon, ALTITUDE_M))
                flip = not flip

        # total distance check
        dist = 0.0
        for i in range(1, len(pts)):
            dist += haversine_distance(*pts[i-1][:2], *pts[i][:2])
        logger.info(f"Waypoints: {len(pts)}  Total distance ≈ {dist:.1f}m")

        # save lawnmower png
        self._save_pattern(poly, lines)
        return pts, lines

    def _save_pattern(self, poly, lines):
        os.makedirs('outputs', exist_ok=True)
        fig, ax = plt.subplots(figsize=(6,6))
        x,y = poly.exterior.xy
        ax.plot(x,y,'k-',linewidth=2)
        for ln in lines:
            xs, ys = ln.xy
            ax.plot(xs, ys, 'b-', linewidth=1)
        ax.set_title('Lawnmower Pattern')
        ax.set_xlabel('Lon'); ax.set_ylabel('Lat')
        fig.savefig('outputs/lawnmower_pattern.png', dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info("Saved outputs/lawnmower_pattern.png")

    def upload_and_execute(self, wps):
        from pymavlink import mavutil

        cmds = self.vehicle.commands
        cmds.clear()

        # Build mission: HOME, TAKEOFF, WAYPOINTS, RTL
        lat0, lon0, alt0 = wps[0]
        cmds.add(Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                        mavutil.mavlink.MAV_CMD_DO_SET_HOME, 0,0,1,0,0,0,
                        lat0, lon0, alt0))
        cmds.add(Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                        mavutil.mavlink.MAV_CMD_NAV_VTOL_TAKEOFF, 0,0,0,0,0,0,
                        lat0, lon0, alt0))
        for lat, lon, alt in wps[1:]:
            cmds.add(Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0,0,0,0,0,0,
                            lat, lon, alt))
        cmds.add(Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0,0,0,0,0,0,
                        0,0,0))
        cmds.upload()
        logger.info("Mission uploaded")

        # GUIDED → ARM → AUTO
        logger.info("Switching to GUIDED for arming")
        self.vehicle.mode = VehicleMode("GUIDED")
        t0 = time.time()
        while self.vehicle.mode.name!="GUIDED" and time.time()-t0<10:
            time.sleep(0.2)
        if self.vehicle.mode.name!="GUIDED":
            raise RuntimeError("GUIDED failed")

        logger.info("Arming motors")
        self.vehicle.armed=True
        t0=time.time()
        while not self.vehicle.armed and time.time()-t0<10:
            time.sleep(0.2)
        if not self.vehicle.armed:
            raise RuntimeError("Arming failed")

        logger.info("Switching to AUTO – starting mission")
        self.vehicle.mode=VehicleMode("AUTO")
        t0=time.time()
        while self.vehicle.mode.name!="AUTO" and time.time()-t0<10:
            time.sleep(0.2)
        if self.vehicle.mode.name!="AUTO":
            raise RuntimeError("AUTO failed")

        # Single explicit cruise-speed command to kick off TECS
        msg=self.vehicle.message_factory.command_long_encode(
            0,0,
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED,
            0,
            0, 1800, -1,0,0,0,0
        )
        self.vehicle.send_mavlink(msg)
        logger.info("Sent initial DO_CHANGE_SPEED=18 m/s")

        # Monitor bank and wait for mission end
        total=self.vehicle.commands.count
        last_wp=-1
        while True:
            wp=self.vehicle.commands.next
            if wp!=last_wp:
                logger.info(f"WP {wp}/{total}")
                last_wp=wp

            # Bank angle warning
            roll_deg=abs(math.degrees(self.vehicle.attitude.roll or 0))
            if roll_deg>50.0:
                logger.warning(f"Bank {roll_deg:.1f}° >50°")

            if wp>=total:
                logger.info("All WPs done → RTL")
                self.vehicle.mode=VehicleMode("RTL")
                break
            time.sleep(1)

        # Wait landing & disarm
        logger.info("Waiting for landing/disarm")
        while True:
            alt=self.vehicle.location.global_relative_frame.alt or 0.0
            armed=self.vehicle.armed
            if alt<=1.0 and not armed:
                logger.info("Landed & disarmed")
                break
            time.sleep(1)

        self.vehicle.close()
        return

    def run(self):
        try:
            self.connect_and_configure()
            poly = self.read_polygon()
            wps, lines = self.generate_lawnmower(poly)
            self.upload_and_execute(wps)
        except Exception as e:
            logger.error(f"Mission aborted: {e}")
            if self.vehicle:
                # ensure safe‐stop
                logger.info("Triggering QRTL and waiting for landing")
                self.vehicle.mode = VehicleMode("QRTL")
                # wait for ground
                while True:
                    alt = self.vehicle.location.global_relative_frame.alt or 0
                    if alt <= 1.0:
                        logger.info("On ground—disarming")
                        self.vehicle.armed = False
                        break
                    time.sleep(1)
                self.vehicle.close()
            raise


if __name__ == '__main__':
    QuadplaneSurvey().run()
