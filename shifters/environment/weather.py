"""
Weather System for F1 Simulator

Realistic weather simulation with dynamic conditions affecting tire choice,
grip levels, and race strategy.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import random
import math


class WeatherCondition(Enum):
    """Weather condition types."""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"


class TrackCondition(Enum):
    """Track surface condition."""
    DRY = "dry"
    DAMP = "damp"
    WET = "wet"
    SOAKING = "soaking"


@dataclass
class WeatherState:
    """Current weather state."""
    condition: WeatherCondition
    track_condition: TrackCondition
    temperature: float  # Air temperature in Celsius
    track_temperature: float  # Track surface temperature
    humidity: float  # Humidity percentage (0-100)
    wind_speed: float  # Wind speed in km/h
    wind_direction: float  # Wind direction in degrees (0-360)
    rain_intensity: float  # Rain intensity (0.0 - 1.0)
    visibility: float  # Visibility in meters (100-1000+)


class WeatherSystem:
    """
    Manages dynamic weather conditions during a race session.
    """

    def __init__(
        self,
        initial_condition: WeatherCondition = WeatherCondition.SUNNY,
        initial_temperature: float = 25.0,
        enable_dynamic_weather: bool = True,
        weather_change_probability: float = 0.02,
    ):
        """
        Initialize weather system.

        Args:
            initial_condition: Starting weather condition
            initial_temperature: Starting air temperature
            enable_dynamic_weather: Whether weather can change during session
            weather_change_probability: Probability of weather change per step
        """
        self.enable_dynamic_weather = enable_dynamic_weather
        self.weather_change_probability = weather_change_probability

        # Initialize weather state
        self.state = self._create_initial_state(initial_condition, initial_temperature)

        # Weather history
        self.history: List[Dict[str, Any]] = []
        self.session_time = 0.0

        # Track drying rate
        self.track_drying_rate = 0.005  # Rate at which track dries per second

    def _create_initial_state(
        self, condition: WeatherCondition, temperature: float
    ) -> WeatherState:
        """Create initial weather state based on condition."""
        track_temp = temperature + 10.0  # Track usually warmer than air

        # Set parameters based on weather condition
        if condition == WeatherCondition.SUNNY:
            return WeatherState(
                condition=condition,
                track_condition=TrackCondition.DRY,
                temperature=temperature,
                track_temperature=track_temp,
                humidity=40.0,
                wind_speed=10.0,
                wind_direction=random.uniform(0, 360),
                rain_intensity=0.0,
                visibility=10000.0,
            )
        elif condition == WeatherCondition.CLOUDY:
            return WeatherState(
                condition=condition,
                track_condition=TrackCondition.DRY,
                temperature=temperature - 2.0,
                track_temperature=track_temp - 3.0,
                humidity=60.0,
                wind_speed=15.0,
                wind_direction=random.uniform(0, 360),
                rain_intensity=0.0,
                visibility=8000.0,
            )
        elif condition == WeatherCondition.LIGHT_RAIN:
            return WeatherState(
                condition=condition,
                track_condition=TrackCondition.DAMP,
                temperature=temperature - 3.0,
                track_temperature=track_temp - 5.0,
                humidity=80.0,
                wind_speed=20.0,
                wind_direction=random.uniform(0, 360),
                rain_intensity=0.3,
                visibility=5000.0,
            )
        elif condition == WeatherCondition.RAIN:
            return WeatherState(
                condition=condition,
                track_condition=TrackCondition.WET,
                temperature=temperature - 4.0,
                track_temperature=track_temp - 7.0,
                humidity=90.0,
                wind_speed=25.0,
                wind_direction=random.uniform(0, 360),
                rain_intensity=0.6,
                visibility=3000.0,
            )
        elif condition == WeatherCondition.HEAVY_RAIN:
            return WeatherState(
                condition=condition,
                track_condition=TrackCondition.SOAKING,
                temperature=temperature - 5.0,
                track_temperature=track_temp - 8.0,
                humidity=95.0,
                wind_speed=35.0,
                wind_direction=random.uniform(0, 360),
                rain_intensity=0.9,
                visibility=1500.0,
            )
        else:  # STORM
            return WeatherState(
                condition=condition,
                track_condition=TrackCondition.SOAKING,
                temperature=temperature - 6.0,
                track_temperature=track_temp - 10.0,
                humidity=98.0,
                wind_speed=50.0,
                wind_direction=random.uniform(0, 360),
                rain_intensity=1.0,
                visibility=500.0,
            )

    def update(self, delta_time: float) -> Optional[WeatherCondition]:
        """
        Update weather state.

        Args:
            delta_time: Time elapsed since last update in seconds

        Returns:
            New weather condition if changed, None otherwise
        """
        self.session_time += delta_time
        old_condition = self.state.condition

        # Check for weather change
        if self.enable_dynamic_weather and random.random() < self.weather_change_probability:
            new_condition = self._get_next_weather_condition()
            if new_condition != old_condition:
                self._transition_to_weather(new_condition)

        # Update track condition based on current weather
        self._update_track_condition(delta_time)

        # Update temperature (track cools/heats slowly)
        self._update_temperature(delta_time)

        # Update wind
        self._update_wind(delta_time)

        # Record history
        self._record_state()

        return new_condition if self.state.condition != old_condition else None

    def _get_next_weather_condition(self) -> WeatherCondition:
        """Determine next weather condition based on current state."""
        current = self.state.condition

        # Weather transition probabilities
        transitions = {
            WeatherCondition.SUNNY: {
                WeatherCondition.SUNNY: 0.7,
                WeatherCondition.CLOUDY: 0.25,
                WeatherCondition.LIGHT_RAIN: 0.05,
            },
            WeatherCondition.CLOUDY: {
                WeatherCondition.SUNNY: 0.3,
                WeatherCondition.CLOUDY: 0.4,
                WeatherCondition.LIGHT_RAIN: 0.25,
                WeatherCondition.RAIN: 0.05,
            },
            WeatherCondition.LIGHT_RAIN: {
                WeatherCondition.CLOUDY: 0.3,
                WeatherCondition.LIGHT_RAIN: 0.4,
                WeatherCondition.RAIN: 0.25,
                WeatherCondition.HEAVY_RAIN: 0.05,
            },
            WeatherCondition.RAIN: {
                WeatherCondition.LIGHT_RAIN: 0.3,
                WeatherCondition.RAIN: 0.4,
                WeatherCondition.HEAVY_RAIN: 0.25,
                WeatherCondition.STORM: 0.05,
            },
            WeatherCondition.HEAVY_RAIN: {
                WeatherCondition.RAIN: 0.4,
                WeatherCondition.HEAVY_RAIN: 0.4,
                WeatherCondition.STORM: 0.2,
            },
            WeatherCondition.STORM: {
                WeatherCondition.HEAVY_RAIN: 0.5,
                WeatherCondition.STORM: 0.4,
                WeatherCondition.RAIN: 0.1,
            },
        }

        # Choose next condition based on probabilities
        conditions = list(transitions[current].keys())
        probabilities = list(transitions[current].values())

        return random.choices(conditions, weights=probabilities)[0]

    def _transition_to_weather(self, new_condition: WeatherCondition) -> None:
        """Transition to new weather condition."""
        # Gradually adjust parameters
        target_state = self._create_initial_state(
            new_condition, self.state.temperature
        )

        # Update condition
        self.state.condition = new_condition

        # Smoothly transition other parameters
        self.state.humidity = (self.state.humidity + target_state.humidity) / 2
        self.state.rain_intensity = target_state.rain_intensity
        self.state.visibility = target_state.visibility
        self.state.wind_speed = (self.state.wind_speed + target_state.wind_speed) / 2

    def _update_track_condition(self, delta_time: float) -> None:
        """Update track surface condition based on weather."""
        rain = self.state.rain_intensity

        if rain > 0.8:
            # Heavy rain -> soaking track
            self.state.track_condition = TrackCondition.SOAKING
        elif rain > 0.5:
            # Rain -> wet track
            self.state.track_condition = TrackCondition.WET
        elif rain > 0.2:
            # Light rain -> damp track
            self.state.track_condition = TrackCondition.DAMP
        else:
            # No rain -> track drying
            if self.state.track_condition == TrackCondition.SOAKING:
                # Soaking slowly becomes wet
                if random.random() < self.track_drying_rate * delta_time:
                    self.state.track_condition = TrackCondition.WET
            elif self.state.track_condition == TrackCondition.WET:
                # Wet becomes damp
                if random.random() < self.track_drying_rate * delta_time:
                    self.state.track_condition = TrackCondition.DAMP
            elif self.state.track_condition == TrackCondition.DAMP:
                # Damp becomes dry
                if random.random() < self.track_drying_rate * delta_time:
                    self.state.track_condition = TrackCondition.DRY

    def _update_temperature(self, delta_time: float) -> None:
        """Update temperatures based on weather and time."""
        # Temperature changes slowly
        target_temp = self.state.temperature

        if self.state.condition in [WeatherCondition.SUNNY]:
            target_temp += 0.01 * delta_time  # Slow warming
        elif self.state.condition in [WeatherCondition.RAIN, WeatherCondition.HEAVY_RAIN]:
            target_temp -= 0.01 * delta_time  # Slow cooling

        self.state.temperature = target_temp

        # Track temperature follows air temperature with offset
        track_offset = 10.0 - self.state.rain_intensity * 15.0
        self.state.track_temperature = self.state.temperature + track_offset

    def _update_wind(self, delta_time: float) -> None:
        """Update wind conditions."""
        # Wind direction changes slowly
        direction_change = random.uniform(-2, 2)
        self.state.wind_direction = (self.state.wind_direction + direction_change) % 360

        # Wind speed fluctuates slightly
        speed_change = random.uniform(-1, 1)
        self.state.wind_speed = max(0, self.state.wind_speed + speed_change)

    def _record_state(self) -> None:
        """Record current state to history."""
        self.history.append(
            {
                "time": self.session_time,
                "condition": self.state.condition.value,
                "track_condition": self.state.track_condition.value,
                "temperature": round(self.state.temperature, 1),
                "track_temperature": round(self.state.track_temperature, 1),
                "rain_intensity": round(self.state.rain_intensity, 2),
            }
        )

        # Keep only recent history (last 1000 entries)
        if len(self.history) > 1000:
            self.history.pop(0)

    def get_grip_multiplier(self) -> float:
        """
        Get grip multiplier based on track condition.

        Returns:
            Grip multiplier (0.0 - 1.0)
        """
        condition = self.state.track_condition

        if condition == TrackCondition.DRY:
            return 1.0
        elif condition == TrackCondition.DAMP:
            return 0.85
        elif condition == TrackCondition.WET:
            return 0.65
        else:  # SOAKING
            return 0.45

    def get_visibility_factor(self) -> float:
        """
        Get visibility factor affecting driver performance.

        Returns:
            Visibility factor (0.0 - 1.0)
        """
        visibility = self.state.visibility

        if visibility >= 5000:
            return 1.0
        elif visibility >= 2000:
            return 0.9
        elif visibility >= 1000:
            return 0.75
        else:
            return 0.5

    def should_red_flag(self) -> bool:
        """
        Check if conditions warrant a red flag.

        Returns:
            True if race should be red flagged
        """
        # Red flag in extreme conditions
        if self.state.condition == WeatherCondition.STORM:
            if self.state.visibility < 300 or self.state.wind_speed > 60:
                return True

        return False

    def should_safety_car(self) -> bool:
        """
        Check if weather conditions require safety car.

        Returns:
            True if safety car should be deployed
        """
        # Safety car in heavy rain with poor visibility
        if self.state.condition in [WeatherCondition.HEAVY_RAIN, WeatherCondition.STORM]:
            if self.state.visibility < 1000:
                return True

        return False

    def get_recommended_tire_compound(self) -> str:
        """
        Get recommended tire compound for current conditions.

        Returns:
            Tire compound name
        """
        condition = self.state.track_condition

        if condition == TrackCondition.DRY:
            return "slick"  # Soft/Medium/Hard
        elif condition == TrackCondition.DAMP:
            return "intermediate"
        else:  # WET or SOAKING
            return "wet"

    def force_weather(self, condition: WeatherCondition) -> None:
        """
        Force a specific weather condition.

        Args:
            condition: Weather condition to set
        """
        self._transition_to_weather(condition)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert weather state to dictionary.

        Returns:
            Dictionary with weather data
        """
        return {
            "condition": self.state.condition.value,
            "track_condition": self.state.track_condition.value,
            "temperature": round(self.state.temperature, 1),
            "track_temperature": round(self.state.track_temperature, 1),
            "humidity": round(self.state.humidity, 1),
            "wind_speed": round(self.state.wind_speed, 1),
            "wind_direction": round(self.state.wind_direction, 1),
            "rain_intensity": round(self.state.rain_intensity, 2),
            "visibility": round(self.state.visibility, 0),
            "grip_multiplier": round(self.get_grip_multiplier(), 2),
            "recommended_tire": self.get_recommended_tire_compound(),
            "safety_car_required": self.should_safety_car(),
            "red_flag_required": self.should_red_flag(),
        }

    def get_weather_description(self) -> str:
        """
        Get human-readable weather description.

        Returns:
            Weather description string
        """
        condition = self.state.condition
        descriptions = {
            WeatherCondition.SUNNY: "☀️ Sunny and clear",
            WeatherCondition.CLOUDY: "☁️ Cloudy with good visibility",
            WeatherCondition.LIGHT_RAIN: "🌦️ Light rain, track damp",
            WeatherCondition.RAIN: "🌧️ Rain, wet track",
            WeatherCondition.HEAVY_RAIN: "⛈️ Heavy rain, challenging conditions",
            WeatherCondition.STORM: "⚡ Storm, dangerous conditions",
        }

        return descriptions.get(condition, "Unknown conditions")
