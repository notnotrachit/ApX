"""
F1 Damage System

Realistic damage modeling affecting car performance.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import random


class DamageType(Enum):
    """Types of car damage."""
    FRONT_WING = "front_wing"
    REAR_WING = "rear_wing"
    FLOOR = "floor"
    SIDEPOD = "sidepod"
    SUSPENSION = "suspension"
    GEARBOX = "gearbox"
    ENGINE = "engine"
    BRAKES = "brakes"
    PUNCTURE = "puncture"


class DamageSeverity(Enum):
    """Severity levels for damage."""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    TERMINAL = "terminal"


@dataclass
class DamageComponent:
    """Represents damage to a specific component."""
    component: DamageType
    severity: DamageSeverity
    performance_loss: float  # Percentage performance loss (0.0-1.0)
    repair_time: float  # Time to repair in pit stop (seconds)
    repairable: bool  # Whether damage can be repaired


class DamageSystem:
    """
    Manages car damage and performance degradation.
    """

    def __init__(self):
        """Initialize damage system."""
        self.damages: Dict[DamageType, DamageComponent] = {}

        # Incident probabilities (per step)
        self.contact_probability = 0.0001
        self.mechanical_failure_probability = 0.00005

        # Performance impacts
        self.total_performance_loss = 0.0
        self.downforce_loss = 0.0
        self.power_loss = 0.0

        # Status flags
        self.can_continue = True
        self.terminal_damage = False

    def apply_damage(
        self,
        component: DamageType,
        severity: DamageSeverity,
        cause: str = "Unknown"
    ) -> bool:
        """
        Apply damage to a component.

        Args:
            component: Component that was damaged
            severity: Severity of damage
            cause: Cause of damage

        Returns:
            True if damage was applied
        """
        # Check if this damage would be terminal
        if severity == DamageSeverity.TERMINAL:
            self.terminal_damage = True
            self.can_continue = False

        # Calculate performance loss based on component and severity
        performance_loss = self._calculate_performance_loss(component, severity)
        repair_time = self._calculate_repair_time(component, severity)
        repairable = severity != DamageSeverity.TERMINAL

        damage = DamageComponent(
            component=component,
            severity=severity,
            performance_loss=performance_loss,
            repair_time=repair_time,
            repairable=repairable
        )

        # Add or update damage
        self.damages[component] = damage

        # Recalculate total performance impact
        self._update_performance_impact()

        return True

    def _calculate_performance_loss(
        self, component: DamageType, severity: DamageSeverity
    ) -> float:
        """Calculate performance loss percentage for damage."""
        # Base performance loss by severity
        severity_multipliers = {
            DamageSeverity.NONE: 0.0,
            DamageSeverity.MINOR: 0.02,  # 2%
            DamageSeverity.MODERATE: 0.05,  # 5%
            DamageSeverity.MAJOR: 0.15,  # 15%
            DamageSeverity.TERMINAL: 1.0,  # 100%
        }

        # Component-specific impact multipliers
        component_multipliers = {
            DamageType.FRONT_WING: 3.0,  # Very important for downforce
            DamageType.REAR_WING: 2.5,
            DamageType.FLOOR: 4.0,  # Most critical for aero
            DamageType.SIDEPOD: 1.5,
            DamageType.SUSPENSION: 2.0,
            DamageType.GEARBOX: 2.5,
            DamageType.ENGINE: 3.5,
            DamageType.BRAKES: 2.0,
            DamageType.PUNCTURE: 5.0,  # Immediate major impact
        }

        base_loss = severity_multipliers.get(severity, 0.0)
        component_factor = component_multipliers.get(component, 1.0)

        return min(1.0, base_loss * component_factor)

    def _calculate_repair_time(
        self, component: DamageType, severity: DamageSeverity
    ) -> float:
        """Calculate repair time in seconds."""
        if severity == DamageSeverity.TERMINAL:
            return float('inf')  # Cannot repair

        # Base repair times by component (seconds)
        base_times = {
            DamageType.FRONT_WING: 10.0,
            DamageType.REAR_WING: 15.0,
            DamageType.FLOOR: 0.0,  # Cannot repair during race
            DamageType.SIDEPOD: 0.0,  # Cannot repair during race
            DamageType.SUSPENSION: 0.0,  # Cannot repair during race
            DamageType.GEARBOX: 0.0,  # Cannot repair during race
            DamageType.ENGINE: 0.0,  # Cannot repair during race
            DamageType.BRAKES: 5.0,
            DamageType.PUNCTURE: 3.0,  # Tire change
        }

        # Severity multipliers for repair time
        severity_multipliers = {
            DamageSeverity.MINOR: 0.5,
            DamageSeverity.MODERATE: 1.0,
            DamageSeverity.MAJOR: 2.0,
            DamageSeverity.TERMINAL: 0.0,
        }

        base_time = base_times.get(component, 0.0)
        multiplier = severity_multipliers.get(severity, 1.0)

        return base_time * multiplier

    def _update_performance_impact(self) -> None:
        """Update total performance impact from all damages."""
        self.total_performance_loss = 0.0
        self.downforce_loss = 0.0
        self.power_loss = 0.0

        for component, damage in self.damages.items():
            loss = damage.performance_loss

            # Add to total
            self.total_performance_loss += loss

            # Component-specific impacts
            if component in [DamageType.FRONT_WING, DamageType.REAR_WING, DamageType.FLOOR]:
                self.downforce_loss += loss
            elif component in [DamageType.ENGINE, DamageType.GEARBOX]:
                self.power_loss += loss

        # Cap total loss at 100%
        self.total_performance_loss = min(1.0, self.total_performance_loss)
        self.downforce_loss = min(1.0, self.downforce_loss)
        self.power_loss = min(1.0, self.power_loss)

    def simulate_contact_damage(self, impact_severity: float = 0.5) -> Optional[DamageType]:
        """
        Simulate damage from contact/collision.

        Args:
            impact_severity: Severity of impact (0.0-1.0)

        Returns:
            Damaged component if any
        """
        # Determine which component was damaged
        # Front wing is most likely in contact
        components_probabilities = {
            DamageType.FRONT_WING: 0.4,
            DamageType.REAR_WING: 0.15,
            DamageType.SIDEPOD: 0.2,
            DamageType.FLOOR: 0.15,
            DamageType.SUSPENSION: 0.1,
        }

        component = random.choices(
            list(components_probabilities.keys()),
            weights=list(components_probabilities.values())
        )[0]

        # Determine severity based on impact
        if impact_severity < 0.2:
            severity = DamageSeverity.MINOR
        elif impact_severity < 0.5:
            severity = DamageSeverity.MODERATE
        elif impact_severity < 0.8:
            severity = DamageSeverity.MAJOR
        else:
            severity = DamageSeverity.TERMINAL

        self.apply_damage(component, severity, cause="Contact/Collision")

        return component

    def simulate_mechanical_failure(self) -> Optional[DamageType]:
        """
        Simulate random mechanical failure.

        Returns:
            Failed component if any
        """
        # Mechanical components that can fail
        components = [
            DamageType.ENGINE,
            DamageType.GEARBOX,
            DamageType.BRAKES,
            DamageType.SUSPENSION,
        ]

        component = random.choice(components)

        # Mechanical failures tend to be major or terminal
        if random.random() < 0.3:
            severity = DamageSeverity.TERMINAL
        elif random.random() < 0.6:
            severity = DamageSeverity.MAJOR
        else:
            severity = DamageSeverity.MODERATE

        self.apply_damage(component, severity, cause="Mechanical Failure")

        return component

    def simulate_puncture(self) -> None:
        """Simulate tire puncture."""
        self.apply_damage(
            DamageType.PUNCTURE,
            DamageSeverity.MAJOR,
            cause="Tire Puncture"
        )

    def repair_component(self, component: DamageType) -> bool:
        """
        Attempt to repair a component during pit stop.

        Args:
            component: Component to repair

        Returns:
            True if repaired successfully
        """
        if component not in self.damages:
            return True  # No damage to repair

        damage = self.damages[component]

        if not damage.repairable:
            return False  # Cannot repair

        if damage.repair_time == 0:
            return False  # Cannot repair this component

        # Remove the damage
        del self.damages[component]

        # Update performance impact
        self._update_performance_impact()

        # Check if car can continue
        if self.terminal_damage and len(self.damages) == 0:
            self.terminal_damage = False
            self.can_continue = True

        return True

    def get_speed_multiplier(self) -> float:
        """
        Get speed multiplier based on total damage.

        Returns:
            Speed multiplier (0.0-1.0)
        """
        if not self.can_continue:
            return 0.0

        # Total performance loss affects speed
        return 1.0 - self.total_performance_loss

    def get_downforce_multiplier(self) -> float:
        """
        Get downforce multiplier based on aero damage.

        Returns:
            Downforce multiplier (0.0-1.0)
        """
        return 1.0 - self.downforce_loss

    def get_power_multiplier(self) -> float:
        """
        Get power multiplier based on engine/gearbox damage.

        Returns:
            Power multiplier (0.0-1.0)
        """
        return 1.0 - self.power_loss

    def has_damage(self, component: Optional[DamageType] = None) -> bool:
        """
        Check if car has damage.

        Args:
            component: Specific component to check, or None for any damage

        Returns:
            True if damage exists
        """
        if component:
            return component in self.damages
        return len(self.damages) > 0

    def get_damage_report(self) -> List[Dict[str, Any]]:
        """
        Get detailed damage report.

        Returns:
            List of damage information
        """
        report = []

        for component, damage in self.damages.items():
            report.append({
                'component': component.value,
                'severity': damage.severity.value,
                'performance_loss': round(damage.performance_loss * 100, 1),
                'repair_time': damage.repair_time if damage.repair_time != float('inf') else None,
                'repairable': damage.repairable
            })

        return report

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert damage state to dictionary.

        Returns:
            Dictionary with damage data
        """
        return {
            'has_damage': self.has_damage(),
            'can_continue': self.can_continue,
            'terminal_damage': self.terminal_damage,
            'total_performance_loss': round(self.total_performance_loss * 100, 1),
            'speed_multiplier': round(self.get_speed_multiplier(), 3),
            'downforce_loss': round(self.downforce_loss * 100, 1),
            'power_loss': round(self.power_loss * 100, 1),
            'damage_count': len(self.damages),
            'damages': self.get_damage_report()
        }
