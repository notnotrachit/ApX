"""
Safety Car System for F1 Simulator

Implements Virtual Safety Car (VSC) and Full Safety Car (SC) periods.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import random


class SafetyCarStatus(Enum):
    """Safety car status types."""
    NONE = "none"
    VSC = "virtual_safety_car"
    SC = "safety_car"
    SC_ENDING = "safety_car_ending"


@dataclass
class SafetyCarPeriod:
    """Record of a safety car period."""
    start_time: float
    end_time: Optional[float]
    status: SafetyCarStatus
    reason: str
    lap: int


class SafetyCarSystem:
    """
    Manages safety car deployments and virtual safety car periods.
    """

    def __init__(self):
        """Initialize safety car system."""
        self.status = SafetyCarStatus.NONE
        self.active_period: Optional[SafetyCarPeriod] = None
        self.periods: List[SafetyCarPeriod] = []

        # Configuration
        self.vsc_speed_limit = 0.60  # 60% of normal speed
        self.sc_speed_limit = 0.50  # 50% of normal speed (80 km/h typical)
        self.sc_ending_laps = 1  # Laps with "SC Ending" message

        # Timing
        self.session_time = 0.0
        self.sc_deployed_lap = 0
        self.sc_ending_lap = 0

        # Incident tracking
        self.incident_probability = 0.0002  # Per step probability of incident
        self.weather_incident_multiplier = 1.0

    def update(self, delta_time: float, current_lap: int, weather_conditions: Optional[Dict] = None) -> bool:
        """
        Update safety car status.

        Args:
            delta_time: Time since last update
            current_lap: Current race lap
            weather_conditions: Optional weather data

        Returns:
            True if safety car status changed
        """
        self.session_time += delta_time
        old_status = self.status

        # Update weather incident multiplier
        if weather_conditions:
            self._update_incident_probability(weather_conditions)

        # Check if SC should end
        if self.status == SafetyCarStatus.SC_ENDING:
            if current_lap > self.sc_ending_lap:
                self._end_safety_car()
        elif self.status in [SafetyCarStatus.VSC, SafetyCarStatus.SC]:
            # Random duration or manual control
            if self.active_period:
                duration = self.session_time - self.active_period.start_time

                # VSC typically 2-4 minutes
                if self.status == SafetyCarStatus.VSC and duration > random.uniform(120, 240):
                    self._end_safety_car()

                # SC typically 3-6 minutes, then SC ending
                elif self.status == SafetyCarStatus.SC and duration > random.uniform(180, 360):
                    self._prepare_sc_ending(current_lap)
        else:
            # Check for random incident requiring safety car
            if self._should_deploy_safety_car():
                reason = self._generate_incident_reason()
                self._deploy_safety_car(current_lap, reason)

        return self.status != old_status

    def _update_incident_probability(self, weather_conditions: Dict) -> None:
        """Update incident probability based on weather."""
        track_condition = weather_conditions.get('track_condition', 'dry')

        # Wet conditions increase incident probability
        if track_condition == 'soaking':
            self.weather_incident_multiplier = 4.0
        elif track_condition == 'wet':
            self.weather_incident_multiplier = 2.5
        elif track_condition == 'damp':
            self.weather_incident_multiplier = 1.5
        else:
            self.weather_incident_multiplier = 1.0

    def _should_deploy_safety_car(self) -> bool:
        """Check if safety car should be deployed due to incident."""
        adjusted_probability = self.incident_probability * self.weather_incident_multiplier
        return random.random() < adjusted_probability

    def _generate_incident_reason(self) -> str:
        """Generate a reason for safety car deployment."""
        incidents = [
            "Collision between cars",
            "Car crashed into barrier",
            "Debris on track",
            "Spin at Turn {turn}",
            "Car stopped on track",
            "Barrier damage at Turn {turn}",
            "Multiple car incident",
            "Car off track in gravel",
        ]

        reason = random.choice(incidents)
        if "{turn}" in reason:
            reason = reason.format(turn=random.randint(1, 20))

        return reason

    def deploy_vsc(self, lap: int, reason: str = "Track incident") -> None:
        """
        Deploy Virtual Safety Car.

        Args:
            lap: Current lap number
            reason: Reason for deployment
        """
        if self.status != SafetyCarStatus.NONE:
            return

        self.status = SafetyCarStatus.VSC
        self.active_period = SafetyCarPeriod(
            start_time=self.session_time,
            end_time=None,
            status=SafetyCarStatus.VSC,
            reason=reason,
            lap=lap
        )

    def deploy_safety_car(self, lap: int, reason: str = "Incident on track") -> None:
        """
        Deploy Full Safety Car.

        Args:
            lap: Current lap number
            reason: Reason for deployment
        """
        if self.status not in [SafetyCarStatus.NONE, SafetyCarStatus.VSC]:
            return

        # If upgrading from VSC, end VSC period first
        if self.status == SafetyCarStatus.VSC:
            self._end_safety_car()

        self.status = SafetyCarStatus.SC
        self.sc_deployed_lap = lap
        self.active_period = SafetyCarPeriod(
            start_time=self.session_time,
            end_time=None,
            status=SafetyCarStatus.SC,
            reason=reason,
            lap=lap
        )

    def _deploy_safety_car(self, lap: int, reason: str) -> None:
        """Internal method to randomly deploy safety car."""
        # 70% chance of VSC, 30% chance of full SC
        if random.random() < 0.7:
            self.deploy_vsc(lap, reason)
        else:
            self.deploy_safety_car(lap, reason)

    def _prepare_sc_ending(self, current_lap: int) -> None:
        """Prepare for safety car to end."""
        if self.status == SafetyCarStatus.SC:
            self.status = SafetyCarStatus.SC_ENDING
            self.sc_ending_lap = current_lap + self.sc_ending_laps

    def _end_safety_car(self) -> None:
        """End the current safety car period."""
        if self.active_period:
            self.active_period.end_time = self.session_time
            self.periods.append(self.active_period)
            self.active_period = None

        self.status = SafetyCarStatus.NONE
        self.sc_deployed_lap = 0
        self.sc_ending_lap = 0

    def end_safety_car_now(self) -> None:
        """Immediately end safety car (manual control)."""
        if self.status == SafetyCarStatus.SC:
            self.status = SafetyCarStatus.SC_ENDING
            # End on current lap
            self.sc_ending_lap = self.sc_deployed_lap
        elif self.status == SafetyCarStatus.VSC:
            self._end_safety_car()

    def get_speed_limit_multiplier(self) -> float:
        """
        Get speed limit multiplier for current safety car status.

        Returns:
            Speed multiplier (1.0 = normal, <1.0 = limited)
        """
        if self.status == SafetyCarStatus.VSC:
            return self.vsc_speed_limit
        elif self.status in [SafetyCarStatus.SC, SafetyCarStatus.SC_ENDING]:
            return self.sc_speed_limit
        else:
            return 1.0

    def is_active(self) -> bool:
        """
        Check if any safety car is currently active.

        Returns:
            True if VSC or SC is active
        """
        return self.status != SafetyCarStatus.NONE

    def can_pit(self) -> bool:
        """
        Check if pit stops are allowed during current safety car.

        Returns:
            True if pit stops are allowed
        """
        # Pit lane typically closed briefly when SC first deployed
        # For simplicity, always allow pitting during SC periods
        return True

    def can_overtake(self) -> bool:
        """
        Check if overtaking is allowed.

        Returns:
            True if overtaking is allowed
        """
        # No overtaking under any safety car
        return self.status == SafetyCarStatus.NONE

    def get_status_message(self) -> str:
        """
        Get current status message.

        Returns:
            Status message string
        """
        if self.status == SafetyCarStatus.VSC:
            return "🟡 VIRTUAL SAFETY CAR"
        elif self.status == SafetyCarStatus.SC:
            return "🚗 SAFETY CAR DEPLOYED"
        elif self.status == SafetyCarStatus.SC_ENDING:
            return "🟢 SAFETY CAR IN THIS LAP"
        else:
            return ""

    def get_info_message(self) -> Optional[str]:
        """
        Get detailed information message.

        Returns:
            Info message if safety car is active
        """
        if self.active_period and self.status != SafetyCarStatus.NONE:
            duration = self.session_time - self.active_period.start_time
            return f"{self.active_period.reason} (Lap {self.active_period.lap}, {duration:.0f}s ago)"
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert safety car state to dictionary.

        Returns:
            Dictionary with safety car data
        """
        return {
            "status": self.status.value,
            "is_active": self.is_active(),
            "speed_limit": self.get_speed_limit_multiplier(),
            "can_overtake": self.can_overtake(),
            "can_pit": self.can_pit(),
            "message": self.get_status_message(),
            "info": self.get_info_message(),
            "total_periods": len(self.periods),
            "current_period": {
                "lap": self.active_period.lap,
                "reason": self.active_period.reason,
                "duration": round(self.session_time - self.active_period.start_time, 1)
            } if self.active_period else None
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about safety car usage.

        Returns:
            Statistics dictionary
        """
        total_vsc = sum(1 for p in self.periods if p.status == SafetyCarStatus.VSC)
        total_sc = sum(1 for p in self.periods if p.status == SafetyCarStatus.SC)

        total_vsc_time = sum(
            (p.end_time or self.session_time) - p.start_time
            for p in self.periods if p.status == SafetyCarStatus.VSC
        )

        total_sc_time = sum(
            (p.end_time or self.session_time) - p.start_time
            for p in self.periods if p.status == SafetyCarStatus.SC
        )

        return {
            "total_vsc_periods": total_vsc,
            "total_sc_periods": total_sc,
            "total_vsc_time": round(total_vsc_time, 1),
            "total_sc_time": round(total_sc_time, 1),
            "all_periods": [
                {
                    "type": p.status.value,
                    "lap": p.lap,
                    "reason": p.reason,
                    "duration": round((p.end_time or self.session_time) - p.start_time, 1)
                }
                for p in self.periods
            ]
        }
