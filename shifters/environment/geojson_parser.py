"""
GeoJSON Track Parser for F1 Simulator

This module provides functionality to parse GeoJSON files containing F1 track layouts
and convert them into usable track data for the simulator.
"""

import json
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import math
import geojson
from shapely.geometry import LineString, Point
from pyproj import Transformer


@dataclass
class TrackPoint:
    """Represents a point on the track with 2D coordinates."""
    x: float  # Normalized x coordinate (0-1000)
    y: float  # Normalized y coordinate (0-1000)
    distance: float  # Distance from start in meters
    lat: Optional[float] = None  # Original latitude
    lon: Optional[float] = None  # Original longitude
    sector: Optional[int] = None  # Sector number (1, 2, or 3)
    corner_type: Optional[str] = None  # 'slow', 'medium', 'fast', 'straight'


@dataclass
class TrackZone:
    """Represents a special zone on the track (DRS, pit lane, etc.)."""
    zone_type: str  # 'drs_detection', 'drs_activation', 'pit_entry', 'pit_exit'
    start_distance: float  # Start position in meters
    end_distance: float  # End position in meters
    metadata: Dict[str, Any]  # Additional zone-specific data


class GeoJSONTrackParser:
    """Parser for F1 track GeoJSON files."""

    def __init__(self, geojson_data: Dict[str, Any]):
        """
        Initialize the parser with GeoJSON data.

        Args:
            geojson_data: Dictionary containing GeoJSON track data
        """
        self.geojson_data = geojson_data
        self.track_points: List[TrackPoint] = []
        self.zones: List[TrackZone] = []
        self.track_name: str = ""
        self.total_length: float = 0.0

    @classmethod
    def from_file(cls, filepath: str) -> 'GeoJSONTrackParser':
        """
        Create a parser from a GeoJSON file.

        Args:
            filepath: Path to the GeoJSON file

        Returns:
            GeoJSONTrackParser instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(data)

    @classmethod
    def from_string(cls, geojson_string: str) -> 'GeoJSONTrackParser':
        """
        Create a parser from a GeoJSON string.

        Args:
            geojson_string: JSON string containing GeoJSON data

        Returns:
            GeoJSONTrackParser instance
        """
        data = json.loads(geojson_string)
        return cls(data)

    def parse(self) -> None:
        """Parse the GeoJSON data and extract track information."""
        # Extract track name from properties
        if 'properties' in self.geojson_data:
            self.track_name = self.geojson_data['properties'].get('name', 'Unknown Track')

        # Handle FeatureCollection or single Feature
        features = []
        if self.geojson_data.get('type') == 'FeatureCollection':
            features = self.geojson_data.get('features', [])
        elif self.geojson_data.get('type') == 'Feature':
            features = [self.geojson_data]

        # Parse features
        for feature in features:
            feature_type = feature.get('properties', {}).get('type', 'track')

            if feature_type in ['track', 'racing_line', 'circuit']:
                self._parse_track_geometry(feature)
            elif feature_type in ['drs_detection', 'drs_activation', 'pit_entry', 'pit_exit']:
                self._parse_zone(feature)

        # If no track points were parsed from features, try the main geometry
        if not self.track_points and 'geometry' in self.geojson_data:
            self._parse_track_geometry(self.geojson_data)

        # Calculate sector boundaries (divide track into 3 equal sectors)
        self._assign_sectors()

    def _parse_track_geometry(self, feature: Dict[str, Any]) -> None:
        """Parse track geometry from a GeoJSON feature."""
        geometry = feature.get('geometry', {})
        geometry_type = geometry.get('type', '')
        coordinates = geometry.get('coordinates', [])

        if not coordinates:
            return

        # Extract coordinate pairs based on geometry type
        coord_pairs = []
        if geometry_type == 'LineString':
            coord_pairs = coordinates
        elif geometry_type == 'MultiLineString':
            # Flatten multi-line into single line
            for line in coordinates:
                coord_pairs.extend(line)
        elif geometry_type == 'Polygon':
            # Use outer ring
            coord_pairs = coordinates[0] if coordinates else []

        if not coord_pairs:
            return

        # Convert coordinates to TrackPoints
        self._convert_coordinates_to_points(coord_pairs)

    def _convert_coordinates_to_points(self, coordinates: List[List[float]]) -> None:
        """
        Convert GeoJSON coordinates to TrackPoint objects.

        Args:
            coordinates: List of [lon, lat] or [lon, lat, elevation] pairs
        """
        if len(coordinates) < 2:
            return

        # Create shapely LineString for distance calculations
        # Handle coordinates that may be [lon, lat] or [lon, lat, elevation]
        points = []
        for coord in coordinates:
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                lon, lat = coord[0], coord[1]
                points.append((lon, lat))
            else:
                # Skip invalid coordinates
                continue

        if len(points) < 2:
            return

        # Calculate bounding box for normalization
        lons = [p[0] for p in points]
        lats = [p[1] for p in points]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        # Calculate center for distance calculations
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Convert to meters using Haversine formula
        cumulative_distance = 0.0
        self.track_points = []

        for i, (lon, lat) in enumerate(points):
            # Normalize coordinates to 0-1000 range for visualization
            x = ((lon - min_lon) / (max_lon - min_lon) * 900 + 50) if max_lon != min_lon else 500
            y = ((lat - min_lat) / (max_lat - min_lat) * 900 + 50) if max_lat != min_lat else 500

            # Calculate distance from previous point
            if i > 0:
                prev_lon, prev_lat = points[i - 1]
                segment_distance = self._haversine_distance(
                    prev_lat, prev_lon, lat, lon
                )
                cumulative_distance += segment_distance

            track_point = TrackPoint(
                x=x,
                y=y,
                distance=cumulative_distance,
                lat=lat,
                lon=lon
            )
            self.track_points.append(track_point)

        # Close the circuit if needed (connect last point to first)
        if len(self.track_points) > 2:
            first = self.track_points[0]
            last = self.track_points[-1]
            final_segment = self._haversine_distance(
                last.lat, last.lon, first.lat, first.lon
            )
            cumulative_distance += final_segment

        self.total_length = cumulative_distance

    def _haversine_distance(self, lat1: float, lon1: float,
                           lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _assign_sectors(self) -> None:
        """Assign sector numbers to track points (3 sectors)."""
        if not self.track_points or self.total_length == 0:
            return

        sector_length = self.total_length / 3

        for point in self.track_points:
            if point.distance < sector_length:
                point.sector = 1
            elif point.distance < 2 * sector_length:
                point.sector = 2
            else:
                point.sector = 3

    def _parse_zone(self, feature: Dict[str, Any]) -> None:
        """Parse a track zone (DRS, pit lane, etc.) from a GeoJSON feature."""
        properties = feature.get('properties', {})
        zone_type = properties.get('type', 'unknown')
        geometry = feature.get('geometry', {})
        coordinates = geometry.get('coordinates', [])

        if not coordinates:
            return

        # For zones, we expect LineString with start and end points
        if geometry.get('type') == 'LineString' and len(coordinates) >= 2:
            start_coord = coordinates[0]
            end_coord = coordinates[-1]

            # Find closest track points to zone boundaries
            start_distance = self._find_closest_distance(start_coord)
            end_distance = self._find_closest_distance(end_coord)

            zone = TrackZone(
                zone_type=zone_type,
                start_distance=start_distance,
                end_distance=end_distance,
                metadata=properties
            )
            self.zones.append(zone)

    def _find_closest_distance(self, coordinate: List[float]) -> float:
        """
        Find the distance along track closest to a given coordinate.

        Args:
            coordinate: [lon, lat] pair

        Returns:
            Distance in meters
        """
        if not self.track_points:
            return 0.0

        lon, lat = coordinate[0], coordinate[1]
        min_dist = float('inf')
        closest_distance = 0.0

        for point in self.track_points:
            dist = self._haversine_distance(lat, lon, point.lat, point.lon)
            if dist < min_dist:
                min_dist = dist
                closest_distance = point.distance

        return closest_distance

    def get_point_at_distance(self, distance: float) -> Optional[TrackPoint]:
        """
        Get the track point at a specific distance along the track.

        Args:
            distance: Distance in meters from start

        Returns:
            TrackPoint at that distance (interpolated if necessary)
        """
        if not self.track_points:
            return None

        # Normalize distance to track length (handle laps)
        normalized_distance = distance % self.total_length if self.total_length > 0 else distance

        # Find the two points to interpolate between
        for i in range(len(self.track_points) - 1):
            p1 = self.track_points[i]
            p2 = self.track_points[i + 1]

            if p1.distance <= normalized_distance <= p2.distance:
                # Linear interpolation
                if p2.distance == p1.distance:
                    return p1

                t = (normalized_distance - p1.distance) / (p2.distance - p1.distance)

                return TrackPoint(
                    x=p1.x + t * (p2.x - p1.x),
                    y=p1.y + t * (p2.y - p1.y),
                    distance=normalized_distance,
                    lat=p1.lat + t * (p2.lat - p1.lat) if p1.lat and p2.lat else None,
                    lon=p1.lon + t * (p2.lon - p1.lon) if p1.lon and p2.lon else None,
                    sector=p1.sector
                )

        # If we're past the end, return the last point
        return self.track_points[-1] if self.track_points else None

    def get_sector_at_distance(self, distance: float) -> int:
        """
        Get the sector number at a specific distance.

        Args:
            distance: Distance in meters from start

        Returns:
            Sector number (1, 2, or 3)
        """
        normalized_distance = distance % self.total_length if self.total_length > 0 else distance
        sector_length = self.total_length / 3

        if normalized_distance < sector_length:
            return 1
        elif normalized_distance < 2 * sector_length:
            return 2
        else:
            return 3

    def is_in_zone(self, distance: float, zone_type: str) -> bool:
        """
        Check if a position is within a specific zone type.

        Args:
            distance: Distance in meters from start
            zone_type: Type of zone to check

        Returns:
            True if position is in the zone
        """
        normalized_distance = distance % self.total_length if self.total_length > 0 else distance

        for zone in self.zones:
            if zone.zone_type == zone_type:
                if zone.start_distance <= normalized_distance <= zone.end_distance:
                    return True

        return False

    def get_track_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get the bounding box of the track.

        Returns:
            (min_x, min_y, max_x, max_y)
        """
        if not self.track_points:
            return (0, 0, 1000, 1000)

        xs = [p.x for p in self.track_points]
        ys = [p.y for p in self.track_points]

        return (min(xs), min(ys), max(xs), max(ys))

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert track data to a dictionary for serialization.

        Returns:
            Dictionary containing track data
        """
        return {
            'name': self.track_name,
            'length': self.total_length,
            'points': [
                {
                    'x': p.x,
                    'y': p.y,
                    'distance': p.distance,
                    'sector': p.sector
                }
                for p in self.track_points
            ],
            'zones': [
                {
                    'type': z.zone_type,
                    'start': z.start_distance,
                    'end': z.end_distance,
                    'metadata': z.metadata
                }
                for z in self.zones
            ],
            'bounds': self.get_track_bounds()
        }
