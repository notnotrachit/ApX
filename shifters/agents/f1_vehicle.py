"""
F1 Vehicle Agent with realistic Formula 1 features.

Includes tire management, fuel system, ERS, DRS, and sector timing.
"""

from typing import Optional, Dict, Any, List
from .base_agent import RacingVehicle
from .tire_system import TireSet, TireCompound, TireStrategy
from ..environment.track import SectorTime


class F1Vehicle(RacingVehicle):
    """
    Formula 1 racing vehicle with realistic F1 features.

    Features:
    - Tire management with degradation
    - Fuel system with weight effects
    - ERS (Energy Recovery System)
    - DRS (Drag Reduction System)
    - Sector timing
    """

    def __init__(
        self,
        model,
        unique_id: str,
        name: Optional[str] = None,
        team_name: str = "Team",
        team_color: str = "#FF0000",
        driver_skill: float = 0.85,  # 0.0 to 1.0
        **kwargs,
    ):
        """
        Initialize an F1 vehicle.

        Args:
            model: The simulation model
            unique_id: Unique identifier
            name: Driver name
            team_name: Team/constructor name
            team_color: Team color (hex)
            driver_skill: Driver skill level (affects consistency, tire management)
            **kwargs: Additional properties
        """
        # F1 car specifications
        super().__init__(
            model=model,
            unique_id=unique_id,
            name=name,
            max_speed=350.0,  # ~350 km/h max speed
            acceleration=25.0,  # High acceleration
            **kwargs
        )

        # Team and driver info
        self.team_name = team_name
        self.team_color = team_color
        self.driver_skill = driver_skill

        # Tire system
        self.tires = TireSet(compound=TireCompound.MEDIUM)
        self.tire_strategy = TireStrategy()
        self.tire_strategy.record_tire_change(None, self.tires, 0)

        # Fuel system
        self.fuel_kg = 110.0  # Start with full fuel (110kg max in F1)
        self.fuel_consumption_rate = 0.75  # kg per kilometer
        self.min_fuel_kg = 0.0

        # ERS (Energy Recovery System)
        self.ers_energy_mj = 4.0  # Megajoules (4 MJ deployment per lap max)
        self.ers_max_mj = 4.0
        self.ers_recovery_rate = 2.0  # MJ per km recovered
        self.ers_deployment_rate = 0.5  # MJ per second when deployed
        self.ers_deployed = False  # Whether ERS is currently being deployed

        # DRS (Drag Reduction System)
        self.drs_available = False
        self.drs_active = False
        self.drs_speed_bonus = 15.0  # km/h speed bonus when DRS active
        self.gap_to_car_ahead = float('inf')  # Gap in seconds

        # Sector timing
        self.current_sector = 1
        self.sector_times: List[SectorTime] = []
        self.sector_start_time = 0.0
        self.best_sector_times = {1: float('inf'), 2: float('inf'), 3: float('inf')}

        # Performance state
        self.current_grip = 1.0
        self.car_weight_kg = 798.0  # Minimum car weight (without fuel)
        self.downforce_level = 1.0  # Aerodynamic downforce
        self.effective_max_speed = self.max_speed  # Initialize effective max speed

        # Strategy
        self.pit_stop_duration = 2.5  # seconds
        self.in_pit_lane = False
        self.pit_lap = None

    def step(self):
        """
        Execute one simulation step for the F1 vehicle.
        """
        if self.finished:
            return

        # Update sector if needed
        self._update_sector()

        # Update tire condition
        self._update_tires()

        # Update fuel
        self._update_fuel()

        # Update ERS
        self._update_ers()

        # Check DRS availability and activation
        self._update_drs()

        # Calculate performance modifiers
        self._calculate_performance()

        # Execute movement
        self._accelerate()
        self._move()

        # Update total time
        self.total_time += self.model.time_step

    def _update_sector(self):
        """Update current sector and record sector times."""
        track = self.model.environment.track
        new_sector = track.get_sector(self.position)

        if new_sector != self.current_sector:
            # Sector changed - record sector time
            sector_time = self.total_time - self.sector_start_time

            # Check if personal best
            is_pb = sector_time < self.best_sector_times[self.current_sector]
            if is_pb:
                self.best_sector_times[self.current_sector] = sector_time

            sector = SectorTime(
                sector_number=self.current_sector,
                time=sector_time,
                is_personal_best=is_pb
            )
            self.sector_times.append(sector)

            # Move to next sector
            self.current_sector = new_sector
            self.sector_start_time = self.total_time

    def _update_tires(self):
        """Update tire wear and temperature."""
        # Calculate distance traveled this step
        distance_delta = self.speed * self.model.time_step / 3.6  # Convert km/h to m/s

        # Update tire wear
        track_temp = self.model.environment.temperature
        self.tires.update_wear(distance_delta, self.speed, track_temp)

        # Update current grip
        self.current_grip = self.tires.get_current_grip()

    def _update_fuel(self):
        """Update fuel level based on consumption."""
        # Distance in kilometers
        distance_km = (self.speed * self.model.time_step) / 3600.0

        # Fuel consumption (higher at high speeds)
        speed_factor = 1.0 + (self.speed / 350.0) * 0.3
        fuel_used = self.fuel_consumption_rate * distance_km * speed_factor

        self.fuel_kg = max(self.min_fuel_kg, self.fuel_kg - fuel_used)

    def _update_ers(self):
        """Update ERS energy recovery and deployment."""
        # Distance in kilometers
        distance_km = (self.speed * self.model.time_step) / 3600.0

        if self.ers_deployed and self.ers_energy_mj > 0:
            # Deploy ERS energy
            deployment = self.ers_deployment_rate * self.model.time_step
            self.ers_energy_mj = max(0, self.ers_energy_mj - deployment)

            # If depleted, stop deployment
            if self.ers_energy_mj <= 0:
                self.ers_deployed = False
        else:
            # Recover ERS energy (from braking and heat recovery)
            recovery = self.ers_recovery_rate * distance_km * 0.1  # 10% recovery rate
            self.ers_energy_mj = min(self.ers_max_mj, self.ers_energy_mj + recovery)

    def _update_drs(self):
        """Update DRS availability and activation."""
        track = self.model.environment.track

        # Check if in DRS detection zone (within 1 second of car ahead)
        if track.is_in_drs_zone(self.position, 'drs_detection'):
            self.drs_available = self.gap_to_car_ahead < 1.0
        elif not track.is_in_drs_zone(self.position, 'drs_activation'):
            # Outside activation zone - DRS not active
            self.drs_active = False

        # DRS can only be active in activation zones if available
        if self.drs_available and track.is_in_drs_zone(self.position, 'drs_activation'):
            self.drs_active = True
        else:
            self.drs_active = False

    def _calculate_performance(self):
        """Calculate overall performance based on all factors."""
        # Base performance
        performance = 1.0

        # Tire grip factor
        performance *= self.current_grip

        # Fuel weight penalty (heavier = slower)
        total_weight = self.car_weight_kg + self.fuel_kg
        weight_factor = 798.0 / total_weight  # Normalized to minimum weight
        performance *= weight_factor

        # Driver skill factor (affects consistency)
        performance *= (0.9 + self.driver_skill * 0.1)

        # Update effective max speed
        self.effective_max_speed = self.max_speed * performance

        # DRS bonus
        if self.drs_active:
            self.effective_max_speed += self.drs_speed_bonus

        # ERS bonus
        if self.ers_deployed and self.ers_energy_mj > 0:
            self.effective_max_speed += 10.0  # ~10 km/h from ERS

    def _accelerate(self):
        """Accelerate considering tire grip, car performance, and cornering."""
        # Get corner speed limit based on track curvature
        corner_speed_limit = self._get_corner_speed_limit()
        
        # Target speed is the minimum of effective max speed and corner limit
        target_speed = min(self.effective_max_speed, corner_speed_limit)
        
        if self.speed < target_speed:
            # Acceleration affected by tire grip
            effective_acceleration = self.acceleration * self.current_grip
            self.speed = min(
                self.speed + effective_acceleration * self.model.time_step,
                target_speed
            )
        elif self.speed > target_speed:
            # Brake for corners
            braking_force = 35.0  # F1 cars have very strong brakes
            self.speed = max(
                self.speed - braking_force * self.model.time_step,
                target_speed
            )

    def pit_stop(self, new_compound: Optional[TireCompound] = None):
        """
        Perform a pit stop with tire change and refueling.

        Args:
            new_compound: Tire compound for new tires (None = same compound)
        """
        self.in_pit_lane = True
        self.speed = 80.0  # Pit lane speed limit (km/h)
        self.pit_stops += 1
        self.pit_lap = self.lap

        # Change tires
        old_tires = self.tires
        compound = new_compound if new_compound else old_tires.compound
        self.tires = TireSet(compound=compound)

        # Record tire change
        self.tire_strategy.record_tire_change(old_tires, self.tires, self.lap)

        # Refuel
        self.fuel_kg = 110.0

        # Reset ERS
        self.ers_energy_mj = self.ers_max_mj
    
    def _get_corner_speed_limit(self) -> float:
        """Calculate speed limit based on current track position and corner type."""
        track = self.model.environment.track
        
        # Get track point at current position
        if not hasattr(track, 'geojson_parser') or not track.geojson_parser:
            return self.effective_max_speed  # No corner data, no limit
        
        parser = track.geojson_parser
        if not parser.track_points:
            return self.effective_max_speed
        
        # Find nearest track point
        total_distance = track.length
        current_distance = (self.position / 100.0) * total_distance
        
        # Find closest point
        closest_point = min(parser.track_points, 
                          key=lambda p: abs(p.distance - current_distance))
        
        # Apply speed limits based on corner type
        # Note: corner_type can be None, 'straight', 'slow', 'medium', 'fast'
        if not closest_point.corner_type or closest_point.corner_type == 'straight':
            # Straight: full speed, no limit
            return self.effective_max_speed
        elif closest_point.corner_type == 'fast':
            # Fast corners (sweeping turns): 250-280 km/h
            return 265.0 * self.current_grip
        elif closest_point.corner_type == 'medium':
            # Medium corners: 150-200 km/h
            return 175.0 * self.current_grip
        elif closest_point.corner_type == 'slow':
            # Slow corners (hairpins, tight chicanes): 80-120 km/h
            return 100.0 * self.current_grip
        else:
            # Default: no limit
            return self.effective_max_speed

    def exit_pit_lane(self):
        """Exit pit lane and return to track."""
        self.in_pit_lane = False
        self.speed = 80.0  # Exit pit lane at speed limit

    def deploy_ers(self):
        """Activate ERS deployment."""
        if self.ers_energy_mj > 0:
            self.ers_deployed = True

    def save_ers(self):
        """Deactivate ERS deployment to save energy."""
        self.ers_deployed = False

    def complete_lap(self, lap_time: float):
        """
        Complete a lap and update tire/fuel state.

        Args:
            lap_time: Time taken for the lap
        """
        super().complete_lap(lap_time)

        # Update tire lap counter
        self.tires.complete_lap()

        # Reset sector tracking
        self.current_sector = 1
        self.sector_start_time = self.total_time

        # Auto pit stop if tires are critically worn or fuel is low
        if self.tires.is_worn_out() or self.fuel_kg < 5.0:
            # Suggest pit stop
            suggested_compound = self.tire_strategy.suggest_compound(
                self.lap,
                self.model.environment.track.num_laps,
                self.tires.compound
            )
            self.pit_stop(suggested_compound)
            self.exit_pit_lane()

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Get detailed telemetry data.

        Returns:
            Dictionary containing all telemetry information
        """
        return {
            # Basic state
            "id": self.unique_id,
            "name": self.name,
            "team": self.team_name,
            "team_color": self.team_color,
            "position_m": round(self.position, 2),
            "speed_kmh": round(self.speed, 1),
            "lap": self.lap,
            "sector": self.current_sector,
            "finished": self.finished,

            # Tires
            "tire": self.tires.to_dict(),

            # Fuel and weight
            "fuel_kg": round(self.fuel_kg, 1),
            "total_weight_kg": round(self.car_weight_kg + self.fuel_kg, 1),

            # ERS
            "ers_energy_mj": round(self.ers_energy_mj, 2),
            "ers_deployed": self.ers_deployed,
            "ers_percentage": round((self.ers_energy_mj / self.ers_max_mj) * 100, 1),

            # DRS
            "drs_available": self.drs_available,
            "drs_active": self.drs_active,
            "gap_ahead_s": round(self.gap_to_car_ahead, 2) if self.gap_to_car_ahead != float('inf') else None,

            # Performance
            "grip": round(self.current_grip, 3),
            "effective_max_speed": round(self.effective_max_speed, 1),

            # Lap times
            "lap_times": [round(t, 3) for t in self.lap_times],
            "best_lap": round(min(self.lap_times), 3) if self.lap_times else None,
            "last_lap": round(self.lap_times[-1], 3) if self.lap_times else None,

            # Sector times (last 3 sectors)
            "recent_sector_times": [
                {
                    "sector": st.sector_number,
                    "time": round(st.time, 3),
                    "is_pb": st.is_personal_best
                }
                for st in self.sector_times[-3:]
            ],
            "best_sectors": {
                sector: round(time, 3) if time != float('inf') else None
                for sector, time in self.best_sector_times.items()
            },

            # Pit stops
            "pit_stops": self.pit_stops,
            "in_pit": self.in_pit_lane,

            # Total stats
            "total_time_s": round(self.total_time, 2),
            "distance_traveled_km": round(self.distance_traveled / 1000.0, 2),
        }

    def get_state(self) -> Dict[str, Any]:
        """Get simplified state for basic displays."""
        return {
            "id": self.unique_id,
            "name": self.name,
            "team": self.team_name,
            "position": round(self.position, 2),
            "speed": round(self.speed, 1),
            "lap": self.lap,
            "sector": self.current_sector,
            "finished": self.finished,
            "tire_compound": self.tires.compound.value,
            "tire_wear": round(self.tires.wear_percentage, 1),
            "fuel": round(self.fuel_kg, 1),
            "pit_stops": self.pit_stops,
            "last_lap_time": round(self.lap_times[-1], 3) if self.lap_times else None,
        }
