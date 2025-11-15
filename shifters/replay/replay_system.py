"""
Replay System for F1 Simulator

Save and replay race sessions with full telemetry data.
"""

import json
import gzip
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import time


@dataclass
class ReplayFrame:
    """Single frame of replay data."""
    timestamp: float
    simulation_step: int
    agents_state: List[Dict[str, Any]]
    weather_state: Optional[Dict[str, Any]] = None
    safety_car_state: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = None


class ReplayRecorder:
    """
    Records race sessions for later playback.
    """

    def __init__(self, session_name: str = "race"):
        """
        Initialize replay recorder.

        Args:
            session_name: Name for this session
        """
        self.session_name = session_name
        self.frames: List[ReplayFrame] = []
        self.metadata: Dict[str, Any] = {}

        self.recording = False
        self.start_time = 0.0
        self.current_step = 0

        # Recording settings
        self.record_interval = 1  # Record every N steps
        self.compress_data = True

    def start_recording(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Start recording.

        Args:
            metadata: Optional session metadata
        """
        self.recording = True
        self.start_time = time.time()
        self.frames = []
        self.current_step = 0

        self.metadata = metadata or {}
        self.metadata['session_name'] = self.session_name
        self.metadata['start_time'] = self.start_time
        self.metadata['record_interval'] = self.record_interval

    def stop_recording(self) -> None:
        """Stop recording."""
        self.recording = False
        self.metadata['end_time'] = time.time()
        self.metadata['duration'] = self.metadata['end_time'] - self.start_time
        self.metadata['total_frames'] = len(self.frames)

    def record_frame(
        self,
        step: int,
        agents_state: List[Dict[str, Any]],
        weather_state: Optional[Dict[str, Any]] = None,
        safety_car_state: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Record a single frame.

        Args:
            step: Simulation step number
            agents_state: List of agent states
            weather_state: Weather data
            safety_car_state: Safety car data
            events: List of events that occurred
        """
        if not self.recording:
            return

        # Only record every N steps
        if step % self.record_interval != 0:
            return

        timestamp = time.time() - self.start_time

        frame = ReplayFrame(
            timestamp=timestamp,
            simulation_step=step,
            agents_state=agents_state,
            weather_state=weather_state,
            safety_car_state=safety_car_state,
            events=events or []
        )

        self.frames.append(frame)
        self.current_step = step

    def save_replay(self, filepath: str) -> bool:
        """
        Save replay to file.

        Args:
            filepath: Path to save file

        Returns:
            True if saved successfully
        """
        try:
            replay_data = {
                'metadata': self.metadata,
                'frames': [asdict(frame) for frame in self.frames]
            }

            # Convert to JSON
            json_data = json.dumps(replay_data, indent=2)

            # Save (optionally compressed)
            if self.compress_data:
                # Save as gzip
                with gzip.open(f"{filepath}.gz", 'wt', encoding='utf-8') as f:
                    f.write(json_data)
            else:
                # Save as plain JSON
                with open(filepath, 'w') as f:
                    f.write(json_data)

            return True

        except Exception as e:
            print(f"Error saving replay: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get recording statistics.

        Returns:
            Statistics dictionary
        """
        if not self.frames:
            return {'frames': 0, 'duration': 0}

        return {
            'session_name': self.session_name,
            'total_frames': len(self.frames),
            'duration': self.metadata.get('duration', 0),
            'start_time': self.metadata.get('start_time', 0),
            'end_time': self.metadata.get('end_time', 0),
            'record_interval': self.record_interval,
            'compressed': self.compress_data
        }


class ReplayPlayer:
    """
    Plays back recorded race sessions.
    """

    def __init__(self):
        """Initialize replay player."""
        self.metadata: Dict[str, Any] = {}
        self.frames: List[ReplayFrame] = []

        self.playing = False
        self.current_frame_index = 0
        self.playback_speed = 1.0  # 1.0 = normal speed
        self.loop = False

    def load_replay(self, filepath: str) -> bool:
        """
        Load replay from file.

        Args:
            filepath: Path to replay file

        Returns:
            True if loaded successfully
        """
        try:
            # Check if compressed
            if filepath.endswith('.gz') or Path(f"{filepath}.gz").exists():
                if not filepath.endswith('.gz'):
                    filepath = f"{filepath}.gz"

                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    replay_data = json.load(f)
            else:
                with open(filepath, 'r') as f:
                    replay_data = json.load(f)

            self.metadata = replay_data.get('metadata', {})

            # Convert frame dictionaries back to ReplayFrame objects
            self.frames = []
            for frame_dict in replay_data.get('frames', []):
                frame = ReplayFrame(**frame_dict)
                self.frames.append(frame)

            self.current_frame_index = 0

            return True

        except Exception as e:
            print(f"Error loading replay: {e}")
            return False

    def start_playback(self, speed: float = 1.0, loop: bool = False) -> None:
        """
        Start replay playback.

        Args:
            speed: Playback speed multiplier
            loop: Whether to loop playback
        """
        self.playing = True
        self.playback_speed = speed
        self.loop = loop
        self.current_frame_index = 0

    def stop_playback(self) -> None:
        """Stop playback."""
        self.playing = False

    def pause_playback(self) -> None:
        """Pause playback."""
        self.playing = False

    def resume_playback(self) -> None:
        """Resume playback."""
        self.playing = True

    def get_current_frame(self) -> Optional[ReplayFrame]:
        """
        Get current frame.

        Returns:
            Current replay frame or None
        """
        if not self.frames or self.current_frame_index >= len(self.frames):
            return None

        return self.frames[self.current_frame_index]

    def advance_frame(self) -> Optional[ReplayFrame]:
        """
        Advance to next frame.

        Returns:
            Next frame or None if end reached
        """
        if not self.playing:
            return self.get_current_frame()

        self.current_frame_index += 1

        if self.current_frame_index >= len(self.frames):
            if self.loop:
                self.current_frame_index = 0
            else:
                self.playing = False
                return None

        return self.get_current_frame()

    def seek_to_frame(self, frame_index: int) -> Optional[ReplayFrame]:
        """
        Seek to specific frame.

        Args:
            frame_index: Frame index to seek to

        Returns:
            Frame at index or None
        """
        if 0 <= frame_index < len(self.frames):
            self.current_frame_index = frame_index
            return self.frames[frame_index]

        return None

    def seek_to_time(self, timestamp: float) -> Optional[ReplayFrame]:
        """
        Seek to specific timestamp.

        Args:
            timestamp: Time in seconds

        Returns:
            Closest frame to timestamp
        """
        # Find closest frame
        closest_index = 0
        min_diff = float('inf')

        for i, frame in enumerate(self.frames):
            diff = abs(frame.timestamp - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_index = i

        return self.seek_to_frame(closest_index)

    def get_playback_info(self) -> Dict[str, Any]:
        """
        Get playback information.

        Returns:
            Playback info dictionary
        """
        current_frame = self.get_current_frame()

        return {
            'playing': self.playing,
            'total_frames': len(self.frames),
            'current_frame': self.current_frame_index,
            'current_time': current_frame.timestamp if current_frame else 0,
            'total_time': self.frames[-1].timestamp if self.frames else 0,
            'playback_speed': self.playback_speed,
            'loop': self.loop,
            'progress_percentage': (self.current_frame_index / len(self.frames) * 100) if self.frames else 0
        }

    def export_highlights(
        self,
        start_time: float,
        end_time: float,
        output_path: str
    ) -> bool:
        """
        Export a highlight clip.

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Path to save highlight

        Returns:
            True if exported successfully
        """
        try:
            # Find frames in time range
            highlight_frames = [
                frame for frame in self.frames
                if start_time <= frame.timestamp <= end_time
            ]

            if not highlight_frames:
                return False

            # Create highlight replay
            highlight_data = {
                'metadata': {
                    **self.metadata,
                    'is_highlight': True,
                    'original_start_time': start_time,
                    'original_end_time': end_time,
                    'frames': len(highlight_frames)
                },
                'frames': [asdict(frame) for frame in highlight_frames]
            }

            # Save
            with open(output_path, 'w') as f:
                json.dump(highlight_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Error exporting highlight: {e}")
            return False

    def get_driver_data(self, driver_id: str) -> List[Dict[str, Any]]:
        """
        Extract all data for a specific driver.

        Args:
            driver_id: Driver unique ID

        Returns:
            List of driver states across all frames
        """
        driver_data = []

        for frame in self.frames:
            for agent_state in frame.agents_state:
                if agent_state.get('id') == driver_id:
                    driver_data.append({
                        'timestamp': frame.timestamp,
                        'step': frame.simulation_step,
                        **agent_state
                    })
                    break

        return driver_data

    def analyze_race(self) -> Dict[str, Any]:
        """
        Analyze replay for key statistics.

        Returns:
            Race analysis data
        """
        if not self.frames:
            return {}

        first_frame = self.frames[0]
        last_frame = self.frames[-1]

        # Count safety car periods
        sc_periods = 0
        in_sc = False

        for frame in self.frames:
            if frame.safety_car_state:
                is_active = frame.safety_car_state.get('is_active', False)
                if is_active and not in_sc:
                    sc_periods += 1
                    in_sc = True
                elif not is_active:
                    in_sc = False

        # Count events
        total_events = sum(len(frame.events) for frame in self.frames if frame.events)

        return {
            'duration': last_frame.timestamp,
            'total_steps': last_frame.simulation_step,
            'total_frames': len(self.frames),
            'drivers': len(first_frame.agents_state),
            'safety_car_periods': sc_periods,
            'total_events': total_events,
            'metadata': self.metadata
        }
