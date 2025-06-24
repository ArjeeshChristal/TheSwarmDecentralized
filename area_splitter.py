from shapely.geometry import Polygon, LineString
from shapely.ops import split
from xml.etree import ElementTree as ET

KML_PATH = 'kml_files/30ha.kml'

def read_polygon_from_kml(kml_path=KML_PATH) -> Polygon:
    """Parses the KML file and returns a Shapely Polygon."""
    tree = ET.parse(kml_path)
    coord_text = tree.find('.//{*}coordinates').text.strip()
    coords = [tuple(map(float, p.split(',')[:2])) for p in coord_text.split()]
    if not coords:
        raise RuntimeError("KML contains no coordinates")
    return Polygon(coords)

def split_polygon_vertically(polygon: Polygon):
    """Splits the polygon into two halves vertically and returns them."""
    minx, miny, maxx, maxy = polygon.bounds
    midx = (minx + maxx) / 2
    split_line = LineString([(midx, miny), (midx, maxy)])
    
    result = split(polygon, split_line)
    parts = [geom for geom in result.geoms if isinstance(geom, Polygon)]

    if len(parts) != 2:
        raise RuntimeError(f"Expected 2 parts after split, got {len(parts)}")

    return parts

def get_area_coordinates(area_number: int, kml_path=KML_PATH):
    """
    area_number: 1 or 2
    Returns: List of (lat, lon) coordinates for that area.
    """
    if area_number not in [1, 2]:
        raise ValueError("Area number must be 1 or 2")

    polygon = read_polygon_from_kml(kml_path)
    poly1, poly2 = split_polygon_vertically(polygon)

    # Choose polygon based on area_number
    selected = poly1 if area_number == 1 else poly2

    coords = list(selected.exterior.coords)
    # Convert (lon, lat) → (lat, lon) for consistency
    latlon_coords = [(lat, lon) for lon, lat in coords]
    return latlon_coords

# If run directly, test both areas
if __name__ == '__main__':
    area1 = get_area_coordinates(1)
    area2 = get_area_coordinates(2)

    print("Area 1 coordinates:")
    for lat, lon in area1:
        print(f"  {lat:.6f}, {lon:.6f}")

    print("\nArea 2 coordinates:")
    for lat, lon in area2:
        print(f"  {lat:.6f}, {lon:.6f}")

