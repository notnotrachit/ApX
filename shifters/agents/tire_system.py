"""
F1 Tire Management System

Realistic tire compound and degradation simulation for Formula 1 racing.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class TireCompound(Enum):
    """F1 tire compound types."""
    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"
    INTERMEDIATE = "intermediate"
    WET = "wet"


@dataclass
class TireCharacteristics:
    """Characteristics of a tire compound."""
    name: str
    compound: TireCompound
    base_grip: float  # Base grip level (0.0 - 1.0)
    degradation_rate: float  # How fast the tire degrades per km
    optimal_temperature: float  # Optimal operating temperature in Celsius
    performance_dropoff: float  # How much performance drops when worn


# Tire compound characteristics based on F1 specifications
TIRE_SPECS = {
    TireCompound.SOFT: TireCharacteristics(
        name="Soft",
        compound=TireCompound.SOFT,
        base_grip=1.0,  # Highest grip
        degradation_rate=0.015,  # Degrades fastest
        optimal_temperature=100.0,
        performance_dropoff=0.4  # Performance drops significantly when worn
    ),
    TireCompound.MEDIUM: TireCharacteristics(
        name="Medium",
        compound=TireCompound.MEDIUM,
        base_grip=0.85,  # Moderate grip
        degradation_rate=0.008,  # Moderate degradation
        optimal_temperature=95.0,
        performance_dropoff=0.25
    ),
    TireCompound.HARD: TireCharacteristics(
        name="Hard",
        compound=TireCompound.HARD,
        base_grip=0.75,  # Lower grip
        degradation_rate=0.004,  # Slowest degradation
        optimal_temperature=90.0,
        performance_dropoff=0.15  # More consistent when worn
    ),
    TireCompound.INTERMEDIATE: TireCharacteristics(
        name="Intermediate",
        compound=TireCompound.INTERMEDIATE,
        base_grip=0.7,  # For damp conditions
        degradation_rate=0.012,
        optimal_temperature=80.0,
        performance_dropoff=0.3
    ),
    TireCompound.WET: TireCharacteristics(
        name="Wet",
        compound=TireCompound.WET,
        base_grip=0.6,  # For wet conditions
        degradation_rate=0.010,
        optimal_temperature=70.0,
        performance_dropoff=0.35
    ),
}


class TireSet:
    """
    Represents a set of tires with wear and performance characteristics.
    """

    def __init__(self, compound: TireCompound = TireCompound.MEDIUM):
        """
        Initialize a tire set.

        Args:
            compound: Tire compound type
        """
        self.compound = compound
        self.specs = TIRE_SPECS[compound]

        # Tire state
        self.wear_percentage = 0.0  # 0-100%
        self.temperature = 25.0  # Current temperature in Celsius
        self.distance_traveled = 0.0  # Distance on this tire set in meters
        self.is_mounted = True  # Whether tires are currently on the car

        # Performance tracking
        self.laps_completed = 0
        self.age_laps = 0  # Total laps including previous stints

    def update_wear(self, distance_delta: float, speed: float,
                    track_temperature: float = 25.0) -> None:
        """
        Update tire wear based on distance traveled.

        Args:
            distance_delta: Distance traveled in meters since last update
            speed: Current speed (affects temperature)
            track_temperature: Ambient track temperature
        """
        # Convert distance to kilometers for degradation calculation
        distance_km = distance_delta / 1000.0
        self.distance_traveled += distance_delta

        # Base wear from degradation rate
        base_wear = distance_km * self.specs.degradation_rate * 100

        # Temperature effect on wear
        temp_factor = self._get_temperature_factor()
        wear_multiplier = 1.0 + (1.0 - temp_factor) * 0.5  # Higher wear when not at optimal temp

        # Speed effect (higher speeds = more wear)
        speed_factor = 1.0 + (speed / 350.0) * 0.3  # Max 30% increase at 350 km/h

        # Apply wear
        total_wear = base_wear * wear_multiplier * speed_factor
        self.wear_percentage = min(100.0, self.wear_percentage + total_wear)

        # Update temperature based on speed and ambient
        self._update_temperature(speed, track_temperature)

    def _update_temperature(self, speed: float, track_temperature: float) -> None:
        """
        Update tire temperature based on speed and track conditions.

        Args:
            speed: Current speed in km/h
            track_temperature: Ambient track temperature
        """
        # Target temperature based on speed
        speed_heat = (speed / 350.0) * 50  # Up to 50°C from speed
        target_temp = track_temperature + speed_heat + 20  # Base operating temp

        # Smooth temperature change (tire heats/cools gradually)
        temp_diff = target_temp - self.temperature
        self.temperature += temp_diff * 0.1  # 10% per update towards target

    def _get_temperature_factor(self) -> float:
        """
        Calculate performance factor based on temperature.

        Returns:
            Factor between 0.0 and 1.0 (1.0 = optimal temperature)
        """
        optimal = self.specs.optimal_temperature
        temp_diff = abs(self.temperature - optimal)

        # Performance drops as temperature deviates from optimal
        if temp_diff < 10:
            return 1.0
        elif temp_diff < 20:
            return 0.9
        elif temp_diff < 30:
            return 0.75
        else:
            return 0.6

    def get_current_grip(self) -> float:
        """
        Calculate current grip level based on wear and temperature.

        Returns:
            Current grip multiplier (0.0 - 1.0)
        """
        # Base grip from compound
        base = self.specs.base_grip

        # Wear effect
        wear_factor = 1.0 - (self.wear_percentage / 100.0) * self.specs.performance_dropoff

        # Temperature effect
        temp_factor = self._get_temperature_factor()

        # Combined grip
        current_grip = base * wear_factor * temp_factor

        return max(0.1, min(1.0, current_grip))  # Clamp between 0.1 and 1.0

    def get_max_speed_multiplier(self) -> float:
        """
        Get the speed multiplier based on tire condition.

        Returns:
            Multiplier for maximum speed (0.0 - 1.0)
        """
        return self.get_current_grip()

    def is_worn_out(self, threshold: float = 85.0) -> bool:
        """
        Check if tires are critically worn.

        Args:
            threshold: Wear percentage threshold

        Returns:
            True if wear exceeds threshold
        """
        return self.wear_percentage >= threshold

    def needs_change(self, strategy_threshold: float = 70.0) -> bool:
        """
        Check if tires should be changed based on strategy.

        Args:
            strategy_threshold: Strategic wear threshold

        Returns:
            True if tire change is recommended
        """
        return self.wear_percentage >= strategy_threshold

    def get_remaining_life(self) -> float:
        """
        Get estimated remaining tire life.

        Returns:
            Percentage of life remaining (0-100)
        """
        return max(0.0, 100.0 - self.wear_percentage)

    def complete_lap(self) -> None:
        """Mark a lap as completed on this tire set."""
        self.laps_completed += 1
        self.age_laps += 1

    def to_dict(self) -> dict:
        """
        Convert tire state to dictionary.

        Returns:
            Dictionary containing tire information
        """
        return {
            "compound": self.compound.value,
            "compound_name": self.specs.name,
            "wear_percentage": round(self.wear_percentage, 1),
            "temperature": round(self.temperature, 1),
            "current_grip": round(self.get_current_grip(), 3),
            "distance_traveled_km": round(self.distance_traveled / 1000.0, 2),
            "laps_completed": self.laps_completed,
            "age_laps": self.age_laps,
            "is_worn_out": self.is_worn_out(),
            "needs_change": self.needs_change(),
            "remaining_life": round(self.get_remaining_life(), 1),
        }


class TireStrategy:
    """
    Manages tire strategy for a race including pit stops and compound choices.
    """

    def __init__(self):
        """Initialize tire strategy manager."""
        self.tire_history = []  # History of tire sets used
        self.planned_pit_laps = []  # Planned pit stop laps
        self.compounds_used = set()  # Track which compounds have been used

    def record_tire_change(self, old_tires: Optional[TireSet], new_tires: TireSet,
                          lap: int) -> None:
        """
        Record a tire change.

        Args:
            old_tires: Previous tire set (None if start of race)
            new_tires: New tire set
            lap: Lap number when change occurred
        """
        if old_tires:
            self.tire_history.append({
                "lap": lap,
                "old_compound": old_tires.compound.value,
                "new_compound": new_tires.compound.value,
                "old_wear": old_tires.wear_percentage,
                "laps_on_old": old_tires.laps_completed
            })

        self.compounds_used.add(new_tires.compound)

    def meets_compound_requirement(self) -> bool:
        """
        Check if minimum compound requirement is met.
        In F1, drivers must use at least 2 different compounds in dry races.

        Returns:
            True if requirement is met
        """
        dry_compounds_used = self.compounds_used - {
            TireCompound.INTERMEDIATE,
            TireCompound.WET
        }
        return len(dry_compounds_used) >= 2

    def suggest_compound(self, current_lap: int, total_laps: int,
                        current_compound: TireCompound,
                        track_condition: str = "dry") -> TireCompound:
        """
        Suggest optimal tire compound for next stint.

        Args:
            current_lap: Current lap number
            total_laps: Total race laps
            current_compound: Current tire compound
            track_condition: Track condition (dry/damp/wet)

        Returns:
            Recommended tire compound
        """
        # Weather-based suggestions
        if track_condition == "wet":
            return TireCompound.WET
        elif track_condition == "damp":
            return TireCompound.INTERMEDIATE

        # Dry race strategy
        laps_remaining = total_laps - current_lap
        race_progress = current_lap / total_laps if total_laps > 0 else 0

        # Early race: Use softer compounds
        if race_progress < 0.3:
            if TireCompound.SOFT not in self.compounds_used:
                return TireCompound.SOFT
            return TireCompound.MEDIUM

        # Mid race: Balance performance and durability
        elif race_progress < 0.7:
            if TireCompound.MEDIUM not in self.compounds_used:
                return TireCompound.MEDIUM
            return TireCompound.HARD

        # Late race: Prioritize durability
        else:
            # If we need to meet compound requirement
            if not self.meets_compound_requirement():
                # Use whichever compound we haven't used yet
                for compound in [TireCompound.HARD, TireCompound.MEDIUM, TireCompound.SOFT]:
                    if compound not in self.compounds_used:
                        return compound

            return TireCompound.HARD

    def to_dict(self) -> dict:
        """
        Convert strategy to dictionary.

        Returns:
            Dictionary containing strategy information
        """
        return {
            "tire_history": self.tire_history,
            "compounds_used": [c.value for c in self.compounds_used],
            "meets_compound_requirement": self.meets_compound_requirement(),
            "planned_pit_laps": self.planned_pit_laps
        }
