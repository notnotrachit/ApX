"""Track and environment representation for mobility simulation."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .geojson_parser import GeoJSONTrackParser, TrackZone


@dataclass
class Checkpoint:
    """Represents a checkpoint on the track."""

    id: str
    position: float  # Position on track (distance from start)
    name: Optional[str] = None


@dataclass
class SectorTime:
    """Represents sector timing information."""

    sector_number: int  # 1, 2, or 3
    time: float  # Time in seconds
    is_personal_best: bool = False
    is_overall_best: bool = False


class Track:
    """
    Represents a racing track or path for agents to follow.

    Can be linear, circular, or have custom topology.
    Supports both simple 1D tracks and complex GeoJSON-based 2D tracks.
    """

    def __init__(
        self,
        length: float,
        num_laps: int = 3,
        track_type: str = "circuit",  # "circuit" or "linear"
        name: str = "Default Track",
        geojson_data: Optional[Dict[str, Any]] = None,
        geojson_file: Optional[str] = None,
    ):
        """
        Initialize a track.

        Args:
            length: Total length of the track (in distance units)
            num_laps: Number of laps to complete
            track_type: Type of track - "circuit" (loop) or "linear" (point-to-point)
            name: Name of the track
            geojson_data: Optional GeoJSON dictionary for 2D track layout
            geojson_file: Optional path to GeoJSON file
        """
        self.length = length
        self.num_laps = num_laps
        self.track_type = track_type
        self.name = name
        self.checkpoints: List[Checkpoint] = []

        # GeoJSON support
        self.geojson_parser: Optional[GeoJSONTrackParser] = None
        self.has_geojson = False

        # Sector boundaries (distances in meters)
        self.sector_boundaries = [0.0, length / 3, 2 * length / 3, length]

        # DRS zones
        self.drs_zones: List[TrackZone] = []

        # Initialize GeoJSON if provided
        if geojson_file:
            self.load_geojson_from_file(geojson_file)
        elif geojson_data:
            self.load_geojson(geojson_data)
        else:
            # Create default start/finish checkpoint for simple tracks
            self.add_checkpoint("start_finish", 0.0, "Start/Finish")

    def load_geojson(self, geojson_data: Dict[str, Any]) -> None:
        """
        Load track layout from GeoJSON data.

        Args:
            geojson_data: Dictionary containing GeoJSON track data
        """
        self.geojson_parser = GeoJSONTrackParser(geojson_data)
        self.geojson_parser.parse()

        # Update track properties from GeoJSON
        if self.geojson_parser.track_name:
            self.name = self.geojson_parser.track_name
        if self.geojson_parser.total_length > 0:
            self.length = self.geojson_parser.total_length

        # Update sector boundaries
        self.sector_boundaries = [
            0.0,
            self.length / 3,
            2 * self.length / 3,
            self.length
        ]

        # Load DRS zones from GeoJSON
        self.drs_zones = [
            zone for zone in self.geojson_parser.zones
            if zone.zone_type in ['drs_detection', 'drs_activation']
        ]

        # Create sector checkpoints
        self.add_checkpoint("start_finish", 0.0, "Start/Finish")
        self.add_checkpoint("sector_1_end", self.length / 3, "Sector 1 End")
        self.add_checkpoint("sector_2_end", 2 * self.length / 3, "Sector 2 End")

        self.has_geojson = True

    def load_geojson_from_file(self, filepath: str) -> None:
        """
        Load track layout from a GeoJSON file.

        Args:
            filepath: Path to the GeoJSON file
        """
        parser = GeoJSONTrackParser.from_file(filepath)
        self.geojson_parser = parser
        self.load_geojson(parser.geojson_data)

    def add_checkpoint(
        self, checkpoint_id: str, position: float, name: Optional[str] = None
    ):
        """
        Add a checkpoint to the track.

        Args:
            checkpoint_id: Unique identifier for the checkpoint
            position: Position on track (0 to track length)
            name: Display name for the checkpoint
        """
        if position < 0 or position > self.length:
            raise ValueError(f"Checkpoint position must be between 0 and {self.length}")

        checkpoint = Checkpoint(id=checkpoint_id, position=position, name=name)
        self.checkpoints.append(checkpoint)
        # Sort checkpoints by position
        self.checkpoints.sort(key=lambda c: c.position)

    def get_next_checkpoint(self, current_position: float) -> Optional[Checkpoint]:
        """
        Get the next checkpoint from the current position.

        Args:
            current_position: Current position on track

        Returns:
            The next checkpoint, or None if no more checkpoints
        """
        for checkpoint in self.checkpoints:
            if checkpoint.position > current_position:
                return checkpoint
        return None

    def is_lap_complete(self, position: float) -> bool:
        """
        Check if a lap is complete based on position.

        Args:
            position: Current position on track

        Returns:
            True if position exceeds track length (for circuit tracks)
        """
        if self.track_type == "circuit":
            return position >= self.length
        return False

    def normalize_position(self, position: float) -> float:
        """
        Normalize position for circuit tracks (wrap around).

        Args:
            position: Current position

        Returns:
            Normalized position (0 to track length)
        """
        if self.track_type == "circuit" and position >= self.length:
            return position % self.length
        return position

    def get_progress_percentage(self, position: float, lap: int) -> float:
        """
        Calculate overall progress percentage.

        Args:
            position: Current position on track
            lap: Current lap number

        Returns:
            Progress as percentage (0-100)
        """
        total_distance = self.length * self.num_laps
        current_distance = (lap * self.length) + position
        return min(100.0, (current_distance / total_distance) * 100)

    def is_race_complete(self, lap: int) -> bool:
        """
        Check if race is complete.

        Args:
            lap: Current lap number

        Returns:
            True if all laps are complete
        """
        return lap >= self.num_laps

    def get_sector(self, position: float) -> int:
        """
        Get the current sector number based on position.

        Args:
            position: Current position on track

        Returns:
            Sector number (1, 2, or 3)
        """
        if self.has_geojson and self.geojson_parser:
            return self.geojson_parser.get_sector_at_distance(position)

        # Fallback to simple sector calculation
        normalized_pos = position % self.length if self.length > 0 else 0

        if normalized_pos < self.sector_boundaries[1]:
            return 1
        elif normalized_pos < self.sector_boundaries[2]:
            return 2
        else:
            return 3

    def get_2d_position(self, distance: float) -> Optional[Tuple[float, float]]:
        """
        Get 2D (x, y) coordinates for a given distance along the track.

        Args:
            distance: Distance from start in meters

        Returns:
            (x, y) tuple or None if track has no GeoJSON data
        """
        if not self.has_geojson or not self.geojson_parser:
            return None

        point = self.geojson_parser.get_point_at_distance(distance)
        if point:
            return (point.x, point.y)
        return None

    def is_in_drs_zone(self, distance: float, zone_type: str = 'drs_activation') -> bool:
        """
        Check if position is within a DRS zone.

        Args:
            distance: Distance from start in meters
            zone_type: Type of DRS zone ('drs_detection' or 'drs_activation')

        Returns:
            True if position is in the specified DRS zone
        """
        if self.has_geojson and self.geojson_parser:
            return self.geojson_parser.is_in_zone(distance, zone_type)

        # Check manually defined DRS zones
        normalized_distance = distance % self.length if self.length > 0 else distance

        for zone in self.drs_zones:
            if zone.zone_type == zone_type:
                if zone.start_distance <= normalized_distance <= zone.end_distance:
                    return True

        return False

    def add_drs_zone(self, zone_type: str, start_distance: float,
                     end_distance: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Manually add a DRS zone to the track.

        Args:
            zone_type: Type of zone ('drs_detection' or 'drs_activation')
            start_distance: Start position in meters
            end_distance: End position in meters
            metadata: Optional additional data about the zone
        """
        zone = TrackZone(
            zone_type=zone_type,
            start_distance=start_distance,
            end_distance=end_distance,
            metadata=metadata or {}
        )
        self.drs_zones.append(zone)

    def get_track_data_for_ui(self) -> Dict[str, Any]:
        """
        Get track data formatted for UI visualization.

        Returns:
            Dictionary containing track visualization data
        """
        data = {
            "name": self.name,
            "length": self.length,
            "num_laps": self.num_laps,
            "track_type": self.track_type,
            "has_geojson": self.has_geojson,
            "sector_boundaries": self.sector_boundaries,
            "drs_zones": [
                {
                    "type": zone.zone_type,
                    "start": zone.start_distance,
                    "end": zone.end_distance
                }
                for zone in self.drs_zones
            ]
        }

        if self.has_geojson and self.geojson_parser:
            data["geojson"] = self.geojson_parser.to_dict()

        return data

    def get_info(self) -> Dict[str, Any]:
        """Get track information."""
        info = {
            "name": self.name,
            "length": self.length,
            "num_laps": self.num_laps,
            "track_type": self.track_type,
            "total_distance": self.length * self.num_laps,
            "checkpoints": len(self.checkpoints),
            "has_geojson": self.has_geojson,
            "sectors": 3,
            "drs_zones": len(self.drs_zones),
        }

        return info


class Environment:
    """
    Environment manager that handles track and conditions.
    """

    def __init__(self, track: Track):
        """
        Initialize environment.

        Args:
            track: The track to use for this environment
        """
        self.track = track
        self.current_time = 0.0
        self.weather = "clear"  # Weather conditions
        self.temperature = 25.0  # Temperature in Celsius

    def update(self, delta_time: float):
        """
        Update environment state.

        Args:
            delta_time: Time elapsed since last update
        """
        self.current_time += delta_time

    def get_state(self) -> Dict[str, Any]:
        """Get current environment state."""
        return {
            "time": round(self.current_time, 2),
            "weather": self.weather,
            "temperature": self.temperature,
            "track": self.track.get_info(),
        }
