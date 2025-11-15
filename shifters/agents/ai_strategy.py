"""
AI Strategy Engine for F1 Simulator

Intelligent decision-making for pit stops, tire choice, fuel management, and race strategy.
"""

from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import random


class StrategyType(Enum):
    """Race strategy types."""
    ONE_STOP = "one_stop"
    TWO_STOP = "two_stop"
    THREE_STOP = "three_stop"
    ADAPTIVE = "adaptive"  # Changes based on conditions


class RiskProfile(Enum):
    """AI risk-taking personality."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class AIStrategyEngine:
    """
    Intelligent strategy engine for F1 racing decisions.

    Makes decisions about:
    - When to pit
    - Which tire compound to use
    - Fuel management
    - ERS deployment
    - Overtaking attempts
    - Response to safety cars
    """

    def __init__(
        self,
        driver_id: str,
        risk_profile: RiskProfile = RiskProfile.BALANCED,
        strategy_type: StrategyType = StrategyType.ADAPTIVE
    ):
        """
        Initialize AI strategy engine.

        Args:
            driver_id: Driver unique ID
            risk_profile: Risk-taking personality
            strategy_type: Preferred strategy type
        """
        self.driver_id = driver_id
        self.risk_profile = risk_profile
        self.strategy_type = strategy_type

        # Planned pit stops
        self.planned_pit_laps: List[int] = []
        self.completed_pit_stops = 0

        # Decision thresholds
        self.tire_wear_pit_threshold = self._get_tire_threshold()
        self.fuel_reserve = 5.0  # Always keep 5kg reserve

        # Track state
        self.current_lap = 0
        self.total_laps = 0
        self.position = 0

        # Decision history
        self.decisions: List[Dict[str, Any]] = []

    def _get_tire_threshold(self) -> float:
        """Get tire wear threshold based on risk profile."""
        thresholds = {
            RiskProfile.CONSERVATIVE: 65.0,  # Pit earlier
            RiskProfile.BALANCED: 75.0,
            RiskProfile.AGGRESSIVE: 85.0,  # Push tires harder
        }
        return thresholds.get(self.risk_profile, 75.0)

    def initialize_strategy(self, total_laps: int, track_info: Dict[str, Any]) -> None:
        """
        Initialize race strategy.

        Args:
            total_laps: Total race laps
            track_info: Track characteristics
        """
        self.total_laps = total_laps

        # Determine base strategy
        if self.strategy_type == StrategyType.ONE_STOP:
            self._plan_one_stop()
        elif self.strategy_type == StrategyType.TWO_STOP:
            self._plan_two_stop()
        elif self.strategy_type == StrategyType.THREE_STOP:
            self._plan_three_stop()
        else:  # ADAPTIVE
            # Choose based on track characteristics and total laps
            if total_laps < 20:
                self._plan_one_stop()
            elif total_laps < 40:
                self._plan_two_stop()
            else:
                self._plan_two_stop()  # Default to two-stop for long races

    def _plan_one_stop(self) -> None:
        """Plan a one-stop strategy."""
        # Pit around 50-60% of race
        pit_lap = int(self.total_laps * random.uniform(0.50, 0.60))
        self.planned_pit_laps = [pit_lap]

    def _plan_two_stop(self) -> None:
        """Plan a two-stop strategy."""
        # First stop around 30-35%, second around 65-70%
        first_stop = int(self.total_laps * random.uniform(0.30, 0.35))
        second_stop = int(self.total_laps * random.uniform(0.65, 0.70))
        self.planned_pit_laps = [first_stop, second_stop]

    def _plan_three_stop(self) -> None:
        """Plan a three-stop strategy."""
        # Stops at 25%, 50%, 75%
        stops = [
            int(self.total_laps * 0.25),
            int(self.total_laps * 0.50),
            int(self.total_laps * 0.75)
        ]
        self.planned_pit_laps = stops

    def should_pit(
        self,
        current_lap: int,
        tire_state: Dict[str, Any],
        fuel_kg: float,
        damage_state: Dict[str, Any],
        weather_state: Dict[str, Any],
        safety_car_active: bool,
        position: int,
        gap_ahead: float,
        gap_behind: float
    ) -> Tuple[bool, str]:
        """
        Decide whether to pit this lap.

        Args:
            current_lap: Current lap number
            tire_state: Tire condition data
            fuel_kg: Current fuel level
            damage_state: Damage information
            weather_state: Weather conditions
            safety_car_active: Whether safety car is out
            position: Current race position
            gap_ahead: Gap to car ahead in seconds
            gap_behind: Gap to car behind in seconds

        Returns:
            (should_pit, reason) tuple
        """
        self.current_lap = current_lap
        self.position = position

        # Critical reasons to pit (mandatory)
        if damage_state.get('has_damage', False):
            if damage_state.get('damages', []):
                for damage in damage_state['damages']:
                    if damage.get('repairable', False):
                        return (True, f"Damage repair: {damage.get('component', 'unknown')}")

        # Puncture - immediate pit
        if tire_state.get('wear_percentage', 0) >= 95:
            return (True, "Critical tire wear")

        # Low fuel emergency
        if fuel_kg < self.fuel_reserve:
            return (True, "Low fuel")

        # Weather-driven pit (wrong tires for conditions)
        recommended_tire = weather_state.get('recommended_tire', 'slick')
        current_compound = tire_state.get('compound', 'medium')

        if recommended_tire == 'wet' and current_compound not in ['wet', 'intermediate']:
            return (True, "Weather change - switching to wet tires")
        elif recommended_tire == 'intermediate' and current_compound not in ['wet', 'intermediate']:
            if weather_state.get('rain_intensity', 0) > 0.3:
                return (True, "Weather change - switching to intermediates")
        elif recommended_tire == 'slick' and current_compound in ['wet', 'intermediate']:
            if weather_state.get('track_condition', 'wet') == 'dry':
                return (True, "Track drying - switching to slicks")

        # Safety car opportunity
        if safety_car_active:
            # Good time to pit - less time loss
            if self._should_pit_under_safety_car(tire_state, gap_ahead, gap_behind):
                return (True, "Safety car opportunity")

        # Planned pit stop window
        if self._is_in_pit_window(current_lap):
            # Check if conditions are right
            tire_wear = tire_state.get('wear_percentage', 0)

            if tire_wear >= self.tire_wear_pit_threshold:
                return (True, f"Planned pit stop (tire wear {tire_wear:.0f}%)")

            # Even if tires okay, stick to plan if close enough
            if tire_wear >= self.tire_wear_pit_threshold - 10:
                if gap_ahead > 3.0 or gap_behind > 3.0:  # Safe gap
                    return (True, "Planned pit stop")

        # Undercut opportunity
        if self._should_attempt_undercut(current_lap, position, gap_ahead, tire_state):
            return (True, "Undercut attempt")

        # Emergency tire wear
        if tire_state.get('wear_percentage', 0) >= 90:
            return (True, "Emergency - tire wear critical")

        return (False, "")

    def _is_in_pit_window(self, current_lap: int) -> bool:
        """Check if current lap is in a planned pit window."""
        if not self.planned_pit_laps:
            return False

        # Window is ±2 laps around planned stop
        for planned_lap in self.planned_pit_laps:
            if abs(current_lap - planned_lap) <= 2:
                return True

        return False

    def _should_pit_under_safety_car(
        self,
        tire_state: Dict[str, Any],
        gap_ahead: float,
        gap_behind: float
    ) -> bool:
        """Decide whether to pit during safety car."""
        tire_wear = tire_state.get('wear_percentage', 0)

        # Always pit if tires are worn
        if tire_wear >= 60:
            return True

        # Pit if we have a safe gap
        if gap_ahead > 5.0 and gap_behind > 5.0:
            if tire_wear >= 40:
                return True

        # Aggressive drivers take more risks
        if self.risk_profile == RiskProfile.AGGRESSIVE:
            return tire_wear >= 35

        return False

    def _should_attempt_undercut(
        self,
        current_lap: int,
        position: int,
        gap_ahead: float,
        tire_state: Dict[str, Any]
    ) -> bool:
        """Decide whether to attempt an undercut."""
        # Only attempt if in podium battle (top 5)
        if position > 5:
            return False

        # Only if close to car ahead
        if gap_ahead > 2.0:
            return False

        # Only if our tires are relatively fresh
        if tire_state.get('wear_percentage', 100) > 50:
            return False

        # Check if we're before planned stop
        if self.planned_pit_laps:
            next_planned = min(self.planned_pit_laps)
            if current_lap >= next_planned - 3:
                # Close to planned stop anyway
                return self.risk_profile == RiskProfile.AGGRESSIVE

        return False

    def choose_tire_compound(
        self,
        weather_state: Dict[str, Any],
        remaining_laps: int,
        position: int,
        tire_history: List[str]
    ) -> str:
        """
        Choose optimal tire compound for next stint.

        Args:
            weather_state: Current weather
            remaining_laps: Laps remaining in race
            position: Current position
            tire_history: List of compounds used

        Returns:
            Tire compound name
        """
        track_condition = weather_state.get('track_condition', 'dry')

        # Weather-based choice
        if track_condition in ['wet', 'soaking']:
            return 'wet'
        elif track_condition == 'damp':
            return 'intermediate'

        # Dry conditions - choose slick compound
        # Need to use at least 2 different compounds in dry race
        used_compounds = set(tire_history)

        # Strategy based on remaining laps and position
        stint_length = remaining_laps

        # Conservative approach for leaders
        if position <= 3:
            if stint_length <= 15:
                return 'soft' if 'soft' not in used_compounds else 'medium'
            elif stint_length <= 25:
                return 'medium' if 'medium' not in used_compounds else 'hard'
            else:
                return 'hard'

        # Aggressive approach for midfield
        if self.risk_profile == RiskProfile.AGGRESSIVE:
            if stint_length <= 20:
                return 'soft'
            elif stint_length <= 30:
                return 'medium'
            else:
                return 'hard'

        # Balanced approach
        if stint_length <= 15:
            return 'soft' if 'soft' not in used_compounds else 'medium'
        elif stint_length <= 30:
            return 'medium' if 'medium' not in used_compounds else 'hard'
        else:
            return 'hard'

    def should_deploy_ers(
        self,
        position: int,
        gap_ahead: float,
        gap_behind: float,
        ers_percentage: float,
        drs_available: bool,
        remaining_laps: int
    ) -> bool:
        """
        Decide whether to deploy ERS.

        Args:
            position: Current position
            gap_ahead: Gap to car ahead
            gap_behind: Gap to car behind
            ers_percentage: Current ERS charge percentage
            drs_available: Whether DRS is available
            remaining_laps: Laps remaining

        Returns:
            True if should deploy ERS
        """
        # Don't deploy if ERS is low
        if ers_percentage < 20:
            return False

        # Save ERS for final laps if leading
        if position == 1 and remaining_laps > 5:
            if gap_behind > 1.0:
                return False  # Save ERS

        # Deploy when attacking (close to car ahead)
        if gap_ahead < 1.0:
            return True

        # Deploy when defending (car close behind)
        if gap_behind < 1.0:
            return True

        # Deploy in combination with DRS
        if drs_available and gap_ahead < 2.0:
            return True

        # Aggressive drivers use ERS more liberally
        if self.risk_profile == RiskProfile.AGGRESSIVE:
            if ers_percentage > 50:
                return True

        return False

    def should_attempt_overtake(
        self,
        gap_ahead: float,
        speed_advantage: float,
        drs_available: bool,
        ers_percentage: float,
        tire_advantage: float
    ) -> bool:
        """
        Decide whether to attempt an overtake.

        Args:
            gap_ahead: Gap to car ahead in seconds
            speed_advantage: Speed advantage in km/h
            drs_available: Whether DRS is available
            ers_percentage: ERS charge level
            tire_advantage: Tire grip advantage (positive = better tires)

        Returns:
            True if should attempt overtake
        """
        # Need to be close
        if gap_ahead > 1.0:
            return False

        # Calculate overtaking probability
        overtake_score = 0

        # Speed advantage helps
        if speed_advantage > 10:
            overtake_score += 3
        elif speed_advantage > 5:
            overtake_score += 2
        elif speed_advantage > 0:
            overtake_score += 1

        # DRS is crucial
        if drs_available:
            overtake_score += 3

        # ERS deployment helps
        if ers_percentage > 50:
            overtake_score += 2
        elif ers_percentage > 20:
            overtake_score += 1

        # Tire advantage
        if tire_advantage > 0.2:
            overtake_score += 3
        elif tire_advantage > 0.1:
            overtake_score += 2
        elif tire_advantage > 0:
            overtake_score += 1

        # Risk profile affects threshold
        thresholds = {
            RiskProfile.CONSERVATIVE: 7,
            RiskProfile.BALANCED: 5,
            RiskProfile.AGGRESSIVE: 3,
        }

        threshold = thresholds.get(self.risk_profile, 5)

        return overtake_score >= threshold

    def update_strategy(
        self,
        current_lap: int,
        position: int,
        safety_car_deployed: bool,
        weather_changed: bool
    ) -> Optional[str]:
        """
        Update strategy based on race developments.

        Args:
            current_lap: Current lap
            position: Current position
            safety_car_deployed: Whether SC was just deployed
            weather_changed: Whether weather just changed

        Returns:
            Strategy change message if any
        """
        # Adapt to safety car
        if safety_car_deployed:
            # Recalculate pit windows
            return self._adapt_to_safety_car(current_lap)

        # Adapt to weather
        if weather_changed:
            return "Strategy updated for weather conditions"

        return None

    def _adapt_to_safety_car(self, current_lap: int) -> str:
        """Adapt strategy when safety car is deployed."""
        # If we haven't pitted yet, might bring forward the stop
        if self.completed_pit_stops < len(self.planned_pit_laps):
            next_planned = self.planned_pit_laps[self.completed_pit_stops]

            if next_planned > current_lap + 5:
                # Bring stop forward
                self.planned_pit_laps[self.completed_pit_stops] = current_lap
                return "Brought pit stop forward due to safety car"

        return "Monitoring safety car situation"

    def record_decision(self, decision_type: str, decision: Any, lap: int) -> None:
        """
        Record a strategy decision.

        Args:
            decision_type: Type of decision
            decision: Decision details
            lap: Lap number
        """
        self.decisions.append({
            'lap': lap,
            'type': decision_type,
            'decision': decision,
            'position': self.position
        })

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert strategy state to dictionary.

        Returns:
            Strategy data dictionary
        """
        return {
            'driver_id': self.driver_id,
            'risk_profile': self.risk_profile.value,
            'strategy_type': self.strategy_type.value,
            'planned_pit_laps': self.planned_pit_laps,
            'completed_pit_stops': self.completed_pit_stops,
            'tire_wear_threshold': self.tire_wear_pit_threshold,
            'current_lap': self.current_lap,
            'total_laps': self.total_laps,
            'position': self.position,
            'decisions_made': len(self.decisions)
        }
