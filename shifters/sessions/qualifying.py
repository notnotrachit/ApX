"""
F1 Qualifying System

Implements knockout-style qualifying with Q1, Q2, and Q3 sessions.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time


class QualifyingSession(Enum):
    """Qualifying session types."""
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    FINISHED = "finished"


@dataclass
class QualifyingResult:
    """Result for a single driver in qualifying."""
    driver_id: str
    driver_name: str
    team_name: str
    q1_time: Optional[float] = None
    q2_time: Optional[float] = None
    q3_time: Optional[float] = None
    best_time: Optional[float] = None
    grid_position: int = 0
    eliminated_in: Optional[str] = None
    laps_completed: int = 0


class QualifyingManager:
    """
    Manages F1-style knockout qualifying sessions.

    Q1: 18 minutes, eliminates bottom 5 (positions 16-20)
    Q2: 15 minutes, eliminates next 5 (positions 11-15)
    Q3: 12 minutes, top 10 fight for pole position
    """

    def __init__(self, drivers: List[Any]):
        """
        Initialize qualifying manager.

        Args:
            drivers: List of driver/vehicle objects
        """
        self.drivers = drivers
        self.current_session = QualifyingSession.Q1

        # Session durations in seconds
        self.session_durations = {
            QualifyingSession.Q1: 18 * 60,  # 18 minutes
            QualifyingSession.Q2: 15 * 60,  # 15 minutes
            QualifyingSession.Q3: 12 * 60,  # 12 minutes
        }

        # Session times
        self.session_start_time = 0.0
        self.session_elapsed_time = 0.0

        # Results tracking
        self.results: Dict[str, QualifyingResult] = {}
        for driver in drivers:
            self.results[driver.unique_id] = QualifyingResult(
                driver_id=driver.unique_id,
                driver_name=driver.name,
                team_name=getattr(driver, 'team_name', 'Unknown')
            )

        # Active drivers in current session
        self.active_drivers = set(d.unique_id for d in drivers)

        # Session flags
        self.session_started = False
        self.session_ended = False
        self.final_classification_complete = False

    def start_session(self) -> None:
        """Start the current qualifying session."""
        if not self.session_started:
            self.session_started = True
            self.session_start_time = time.time()
            self.session_elapsed_time = 0.0
            self.session_ended = False

    def update(self, delta_time: float) -> bool:
        """
        Update qualifying session.

        Args:
            delta_time: Time elapsed since last update

        Returns:
            True if session status changed
        """
        if not self.session_started or self.session_ended:
            return False

        old_session = self.current_session
        self.session_elapsed_time += delta_time

        # Check if session time has expired
        if self._is_session_expired():
            self._end_current_session()

        return self.current_session != old_session

    def _is_session_expired(self) -> bool:
        """Check if current session time has expired."""
        if self.current_session == QualifyingSession.FINISHED:
            return False

        duration = self.session_durations.get(self.current_session, 0)
        return self.session_elapsed_time >= duration

    def _end_current_session(self) -> None:
        """End the current session and progress to next."""
        self.session_ended = True

        if self.current_session == QualifyingSession.Q1:
            self._end_q1()
            self.current_session = QualifyingSession.Q2
        elif self.current_session == QualifyingSession.Q2:
            self._end_q2()
            self.current_session = QualifyingSession.Q3
        elif self.current_session == QualifyingSession.Q3:
            self._end_q3()
            self.current_session = QualifyingSession.FINISHED
            self._finalize_grid()

    def _end_q1(self) -> None:
        """End Q1 and eliminate bottom 5 drivers."""
        # Sort drivers by Q1 time
        sorted_drivers = self._get_sorted_results('q1_time')

        # Eliminate bottom 5 (positions 16-20)
        num_drivers = len(sorted_drivers)
        if num_drivers > 15:
            for i in range(num_drivers - 5, num_drivers):
                driver_id = sorted_drivers[i]['driver_id']
                self.results[driver_id].eliminated_in = "Q1"
                self.results[driver_id].grid_position = i + 1
                self.active_drivers.discard(driver_id)

    def _end_q2(self) -> None:
        """End Q2 and eliminate next 5 drivers."""
        # Sort drivers by Q2 time (or Q1 if no Q2 time)
        sorted_drivers = self._get_sorted_results('q2_time', fallback='q1_time')

        # Find drivers who participated in Q2
        q2_drivers = [d for d in sorted_drivers if d['driver_id'] in self.active_drivers]

        # Eliminate bottom 5 of Q2 participants (positions 11-15)
        if len(q2_drivers) > 10:
            for i in range(len(q2_drivers) - 5, len(q2_drivers)):
                driver_id = q2_drivers[i]['driver_id']
                self.results[driver_id].eliminated_in = "Q2"
                self.results[driver_id].grid_position = 11 + (i - (len(q2_drivers) - 5))
                self.active_drivers.discard(driver_id)

    def _end_q3(self) -> None:
        """End Q3 and set final positions for top 10."""
        # Sort top 10 by Q3 time
        sorted_drivers = self._get_sorted_results('q3_time', fallback='q2_time')

        # Set grid positions for top 10
        q3_drivers = [d for d in sorted_drivers if d['driver_id'] in self.active_drivers]

        for i, driver_data in enumerate(q3_drivers[:10]):
            driver_id = driver_data['driver_id']
            self.results[driver_id].grid_position = i + 1
            self.active_drivers.discard(driver_id)

    def _finalize_grid(self) -> None:
        """Finalize the grid with complete classification."""
        self.final_classification_complete = True

        # Set best times
        for result in self.results.values():
            times = [t for t in [result.q1_time, result.q2_time, result.q3_time] if t is not None]
            if times:
                result.best_time = min(times)

    def _get_sorted_results(self, primary_field: str, fallback: Optional[str] = None) -> List[Dict]:
        """
        Get results sorted by time.

        Args:
            primary_field: Primary field to sort by
            fallback: Fallback field if primary is None

        Returns:
            Sorted list of driver data dictionaries
        """
        driver_data = []

        for driver_id, result in self.results.items():
            time_value = getattr(result, primary_field, None)

            # Use fallback if primary is None
            if time_value is None and fallback:
                time_value = getattr(result, fallback, None)

            # If still no time, use a very large value
            if time_value is None:
                time_value = float('inf')

            driver_data.append({
                'driver_id': driver_id,
                'time': time_value,
                'result': result
            })

        # Sort by time (fastest first)
        driver_data.sort(key=lambda x: x['time'])

        return driver_data

    def record_lap_time(self, driver_id: str, lap_time: float) -> bool:
        """
        Record a lap time for a driver.

        Args:
            driver_id: Driver unique ID
            lap_time: Lap time in seconds

        Returns:
            True if this is a new personal best
        """
        if driver_id not in self.results:
            return False

        if driver_id not in self.active_drivers:
            return False  # Driver eliminated, don't record

        result = self.results[driver_id]
        result.laps_completed += 1

        is_personal_best = False

        # Record time in appropriate session
        if self.current_session == QualifyingSession.Q1:
            if result.q1_time is None or lap_time < result.q1_time:
                result.q1_time = lap_time
                is_personal_best = True
        elif self.current_session == QualifyingSession.Q2:
            if result.q2_time is None or lap_time < result.q2_time:
                result.q2_time = lap_time
                is_personal_best = True
        elif self.current_session == QualifyingSession.Q3:
            if result.q3_time is None or lap_time < result.q3_time:
                result.q3_time = lap_time
                is_personal_best = True

        return is_personal_best

    def get_session_remaining_time(self) -> float:
        """
        Get remaining time in current session.

        Returns:
            Remaining time in seconds
        """
        if self.current_session == QualifyingSession.FINISHED:
            return 0.0

        duration = self.session_durations.get(self.current_session, 0)
        remaining = duration - self.session_elapsed_time

        return max(0.0, remaining)

    def get_session_status(self) -> str:
        """
        Get current session status message.

        Returns:
            Status message
        """
        if not self.session_started:
            return f"{self.current_session.value} - NOT STARTED"

        if self.current_session == QualifyingSession.FINISHED:
            return "QUALIFYING COMPLETE"

        remaining = self.get_session_remaining_time()
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)

        return f"{self.current_session.value} - {minutes:02d}:{seconds:02d}"

    def get_live_classification(self) -> List[Dict[str, Any]]:
        """
        Get live classification during qualifying.

        Returns:
            List of driver standings
        """
        # Determine which time to use
        if self.current_session == QualifyingSession.Q1:
            time_field = 'q1_time'
        elif self.current_session == QualifyingSession.Q2:
            time_field = 'q2_time'
        else:
            time_field = 'q3_time'

        sorted_results = self._get_sorted_results(time_field)

        classification = []
        for pos, driver_data in enumerate(sorted_results, 1):
            result = driver_data['result']

            # Determine status
            if driver_data['driver_id'] not in self.active_drivers:
                status = result.eliminated_in or "OUT"
            elif result.laps_completed == 0:
                status = "IN PIT"
            else:
                status = "ON TRACK"

            classification.append({
                'position': pos,
                'driver_id': result.driver_id,
                'driver_name': result.driver_name,
                'team_name': result.team_name,
                'time': driver_data['time'] if driver_data['time'] != float('inf') else None,
                'gap': driver_data['time'] - sorted_results[0]['time'] if driver_data['time'] != float('inf') else None,
                'laps': result.laps_completed,
                'status': status,
                'in_danger_zone': self._is_in_danger_zone(pos)
            })

        return classification

    def _is_in_danger_zone(self, position: int) -> bool:
        """
        Check if a position is in the elimination zone.

        Args:
            position: Current position

        Returns:
            True if in danger of elimination
        """
        if self.current_session == QualifyingSession.Q1:
            return position >= 16
        elif self.current_session == QualifyingSession.Q2:
            return position >= 11 and position <= 15
        elif self.current_session == QualifyingSession.Q3:
            return False  # No elimination in Q3

        return False

    def get_final_grid(self) -> List[Dict[str, Any]]:
        """
        Get final starting grid.

        Returns:
            List of grid positions
        """
        if not self.final_classification_complete:
            return []

        # Sort by grid position
        sorted_results = sorted(
            self.results.values(),
            key=lambda r: r.grid_position if r.grid_position > 0 else 999
        )

        grid = []
        for result in sorted_results:
            grid.append({
                'position': result.grid_position,
                'driver_id': result.driver_id,
                'driver_name': result.driver_name,
                'team_name': result.team_name,
                'q1_time': result.q1_time,
                'q2_time': result.q2_time,
                'q3_time': result.q3_time,
                'best_time': result.best_time,
                'eliminated_in': result.eliminated_in
            })

        return grid

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert qualifying state to dictionary.

        Returns:
            Dictionary with qualifying data
        """
        return {
            'session': self.current_session.value,
            'session_status': self.get_session_status(),
            'remaining_time': round(self.get_session_remaining_time(), 1),
            'session_started': self.session_started,
            'session_ended': self.session_ended,
            'total_drivers': len(self.drivers),
            'active_drivers': len(self.active_drivers),
            'classification': self.get_live_classification() if not self.final_classification_complete else self.get_final_grid()
        }
