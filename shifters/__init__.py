"""
Shifters - Competitive Mobility Systems Simulator

A lightweight mobility event simulator for racing, drones, and traffic management.
"""

__version__ = "0.1.0"

from shifters.agents.base_agent import MobilityAgent, RacingVehicle
from shifters.agents.f1_vehicle import F1Vehicle
from shifters.agents.tire_system import TireSet, TireCompound, TireStrategy
from shifters.environment.track import Track, Environment, Checkpoint, SectorTime
from shifters.environment.geojson_parser import GeoJSONTrackParser
from shifters.simcore.simulator import MobilitySimulation
from shifters.leaderboard.leaderboard import Leaderboard, AgentRanking

__all__ = [
    "MobilityAgent",
    "RacingVehicle",
    "F1Vehicle",
    "TireSet",
    "TireCompound",
    "TireStrategy",
    "Track",
    "Environment",
    "Checkpoint",
    "SectorTime",
    "GeoJSONTrackParser",
    "MobilitySimulation",
    "Leaderboard",
    "AgentRanking",
]
