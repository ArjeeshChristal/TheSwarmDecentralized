import math
from math import cos, radians

# === Default Camera Parameters ===
CAMERA_SPECS = {
    'sensor_res_w': 4056,     # pixels
    'sensor_res_h': 3040,     # pixels
    'pixel_size': 0.00155,    # mm/pixel
    'focal_length': 8         # mm
}

def calculate_mapping_params(alt_m: float, overlap: float = 15.0, sidelap: float = 15.0) -> dict:
    """
    Calculate ground footprint and spacing for a given altitude and default camera settings.
    All dimensions are in meters (except GSD in cm/pixel).
    """
    alt_mm = alt_m * 1000.0
    w_mm = CAMERA_SPECS['sensor_res_w'] * CAMERA_SPECS['pixel_size']
    h_mm = CAMERA_SPECS['sensor_res_h'] * CAMERA_SPECS['pixel_size']

    ground_w = (w_mm * alt_mm) / CAMERA_SPECS['focal_length'] / 1000.0
    ground_h = (h_mm * alt_mm) / CAMERA_SPECS['focal_length'] / 1000.0

    line_spacing = ground_h * (1 - sidelap / 100.0)
    photo_spacing = ground_w * (1 - overlap / 100.0)

    gsd_cm = (CAMERA_SPECS['pixel_size'] * alt_mm * 100.0) / CAMERA_SPECS['focal_length']

    return {
        'ground_width_m': ground_w,
        'ground_height_m': ground_h,
        'gsd_cm': gsd_cm,
        'line_spacing_m': line_spacing,
        'photo_spacing_m': photo_spacing
    }

def meters_to_deg_lat(m: float) -> float:
    """Convert distance in meters to degrees latitude."""
    return m / 111320.0

def meters_to_deg_lon(m: float, lat_deg: float) -> float:
    """Convert distance in meters to degrees longitude, adjusted by latitude."""
    return m / (111320.0 * cos(radians(lat_deg)))

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance (Haversine) in meters between two lat/lon points."""
    R = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(radians(lat1)) * math.cos(radians(lat2)) * math.sin(dlon / 2)**2
    return R * 2 * math.asin(math.sqrt(a))


