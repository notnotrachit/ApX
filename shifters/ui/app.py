"""
Enhanced F1 Simulator FastAPI Server

Production-ready WebSocket server with all advanced features.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import json
from typing import List, Dict, Any
import os
from pathlib import Path

from ..simcore.simulator import MobilitySimulation
from ..environment.track import Track
from ..agents.f1_vehicle import F1Vehicle, TireCompound
from ..environment.weather import WeatherSystem, WeatherCondition
from ..environment.safety_car import SafetyCarSystem
from ..agents.ai_strategy import AIStrategyEngine, RiskProfile
from ..replay import ReplayRecorder

app = FastAPI(title="F1 Simulator API")

# Global state
simulation: MobilitySimulation = None
weather_system: WeatherSystem = None
safety_car_system: SafetyCarSystem = None
replay_recorder: ReplayRecorder = None
connected_clients: List[WebSocket] = []
simulation_running = False

# Configuration
UPDATE_INTERVAL = 0.05  # 20 updates per second


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


def create_simulation(config: Dict[str, Any]) -> None:
    """Create a new simulation with given configuration."""
    global simulation, weather_system, safety_car_system, replay_recorder

    track_name = config.get("track", "monaco")
    num_drivers = config.get("num_drivers", 20)
    num_laps = config.get("num_laps", 5)
    enable_weather = config.get("enable_weather", True)
    enable_safety_car = config.get("enable_safety_car", True)
    initial_weather = config.get("initial_weather", "sunny")

    # Load track
    track_file = f"tracks/{track_name}.geojson"
    if os.path.exists(track_file):
        track = Track(
            length=5000,
            num_laps=num_laps,
            track_type="circuit",
            geojson_file=track_file
        )
    else:
        track = Track(
            length=5000,
            num_laps=num_laps,
            track_type="circuit",
            name=track_name.title()
        )

    # Create simulation
    simulation = MobilitySimulation(track=track, time_step=0.1, enable_live_updates=True)

    # Create weather system
    if enable_weather:
        weather_condition = getattr(WeatherCondition, initial_weather.upper(), WeatherCondition.SUNNY)
        weather_system = WeatherSystem(
            initial_condition=weather_condition,
            enable_dynamic_weather=True
        )
    else:
        weather_system = None

    # Create safety car system
    if enable_safety_car:
        safety_car_system = SafetyCarSystem()
    else:
        safety_car_system = None

    # Create replay recorder
    replay_recorder = ReplayRecorder(f"{track_name}_race")

    # Teams and drivers
    teams = [
        ("Red Bull Racing", "#1E41FF"),
        ("Ferrari", "#DC0000"),
        ("Mercedes", "#00D2BE"),
        ("McLaren", "#FF8700"),
        ("Aston Martin", "#006F62"),
        ("Alpine", "#0090FF"),
        ("Williams", "#005AFF"),
        ("AlphaTauri", "#2B4562"),
        ("Alfa Romeo", "#900000"),
        ("Haas", "#FFFFFF"),
    ]

    driver_names = [
        "Verstappen", "Perez", "Leclerc", "Sainz", "Hamilton", "Russell",
        "Norris", "Piastri", "Alonso", "Stroll", "Gasly", "Ocon",
        "Albon", "Sargeant", "Tsunoda", "Ricciardo", "Bottas", "Zhou",
        "Magnussen", "Hulkenberg"
    ]

    # Create drivers
    for i in range(min(num_drivers, 20)):
        team_idx = i // 2
        team_name, team_color = teams[team_idx % len(teams)]

        vehicle = F1Vehicle(
            model=simulation,
            unique_id=f"driver_{i}",
            name=driver_names[i % len(driver_names)],
            team_name=team_name,
            team_color=team_color,
            driver_skill=0.80 + (i % 10) * 0.02,
        )

        # Add AI strategy
        risk_profiles = [RiskProfile.CONSERVATIVE, RiskProfile.BALANCED, RiskProfile.AGGRESSIVE]
        vehicle.ai_strategy = AIStrategyEngine(
            driver_id=vehicle.unique_id,
            risk_profile=risk_profiles[i % 3]
        )
        vehicle.ai_strategy.initialize_strategy(num_laps, track.get_info())

        # Vary starting tire compounds
        start_compounds = [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]
        vehicle.tires.compound = start_compounds[i % 3]

        simulation.add_agent(vehicle)


def get_simulation_state() -> Dict[str, Any]:
    """Get current simulation state for frontend."""
    if not simulation:
        return {"status": "not_initialized"}

    agents = list(simulation.agent_set)
    track = simulation.environment.track

    # Get agent states with telemetry
    agents_data = []
    for agent in agents:
        if isinstance(agent, F1Vehicle):
            telemetry = agent.get_telemetry()

            # Get 2D position
            pos_2d = track.get_2d_position(agent.position)

            agents_data.append({
                **telemetry,
                "x": pos_2d[0] if pos_2d else None,
                "y": pos_2d[1] if pos_2d else None,
            })

    # Get leaderboard
    rankings = simulation.leaderboard.get_rankings()
    
    # Calculate gaps to leader
    leader_time = rankings[0]["time"] if rankings else 0
    leaderboard = []
    for rank in rankings:
        # Find the agent object to get team info
        agent = next((a for a in agents if a.unique_id == rank["id"]), None)
        leaderboard.append({
            "position": rank["rank"],
            "driver_id": rank["id"],
            "driver_name": rank["name"],
            "team_name": agent.team_name if agent and hasattr(agent, 'team_name') else "Unknown",
            "gap_to_leader": rank["time"] - leader_time if rank["rank"] > 1 else 0.0,
            "total_time": rank["time"],
        })

    state = {
        "status": "running" if simulation_running else "paused",
        "simulation_time": simulation.simulation_time,
        "current_step": simulation.current_step,
        "is_complete": simulation.is_race_complete(),
        "track": track.get_track_data_for_ui(),
        "agents": agents_data,
        "leaderboard": leaderboard,
    }

    # Add weather data
    if weather_system:
        state["weather"] = weather_system.to_dict()

    # Add safety car data
    if safety_car_system:
        state["safety_car"] = safety_car_system.to_dict()

    return state


async def simulation_loop():
    """Main simulation loop that broadcasts updates."""
    global simulation_running
    
    print("🔄 Simulation loop started")

    while simulation_running:
        if simulation and not simulation.is_race_complete():
            # Update systems
            if weather_system:
                weather_system.update(simulation.time_step)

            if safety_car_system:
                safety_car_system.update(
                    simulation.time_step,
                    simulation.agent_set[0].lap if simulation.agent_set else 0,
                    weather_system.to_dict() if weather_system else None
                )

            # AI decisions for each vehicle
            for agent in simulation.agent_set:
                if isinstance(agent, F1Vehicle) and hasattr(agent, 'ai_strategy'):
                    # Get position in race
                    rankings = simulation.leaderboard.get_rankings()
                    position = next((r["rank"] for r in rankings if r["id"] == agent.unique_id), 999)

                    # AI decides whether to pit
                    should_pit, reason = agent.ai_strategy.should_pit(
                        current_lap=agent.lap,
                        tire_state=agent.tires.to_dict(),
                        fuel_kg=agent.fuel_kg,
                        damage_state=agent.damage.to_dict() if hasattr(agent, 'damage') else {},
                        weather_state=weather_system.to_dict() if weather_system else {},
                        safety_car_active=safety_car_system.is_active() if safety_car_system else False,
                        position=position,
                        gap_ahead=agent.gap_to_car_ahead,
                        gap_behind=10.0
                    )

                    if should_pit:
                        # Choose tire compound
                        compound = agent.ai_strategy.choose_tire_compound(
                            weather_state=weather_system.to_dict() if weather_system else {},
                            remaining_laps=simulation.environment.track.num_laps - agent.lap,
                            position=position,
                            tire_history=[agent.tires.compound.value]
                        )

                        compound_map = {
                            'soft': TireCompound.SOFT,
                            'medium': TireCompound.MEDIUM,
                            'hard': TireCompound.HARD,
                            'intermediate': TireCompound.INTERMEDIATE,
                            'wet': TireCompound.WET
                        }
                        agent.pit_stop(compound_map.get(compound, TireCompound.MEDIUM))

            # Step simulation
            simulation.step()

            # Record replay frame
            if replay_recorder and replay_recorder.recording:
                replay_recorder.record_frame(
                    step=simulation.current_step,
                    agents_state=[agent.get_telemetry() for agent in simulation.agent_set if isinstance(agent, F1Vehicle)],
                    weather_state=weather_system.to_dict() if weather_system else None,
                    safety_car_state=safety_car_system.to_dict() if safety_car_system else None
                )

            # Broadcast state to all clients
            state = get_simulation_state()
            await manager.broadcast(state)

            await asyncio.sleep(UPDATE_INTERVAL)
        else:
            # Race complete
            simulation_running = False
            state = get_simulation_state()
            state["status"] = "complete"
            await manager.broadcast(state)
            break


@app.get("/")
async def get_index():
    """Serve the main HTML page."""
    html_file = Path(__file__).parent / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>F1 Simulator</h1><p>UI file not found</p>")


@app.post("/api/simulation/create")
async def create_simulation_endpoint(config: Dict[str, Any]):
    """Create a new simulation."""
    try:
        create_simulation(config)
        print(f"✅ Simulation created with {len(list(simulation.agent_set))} agents")
        
        # Broadcast initial state immediately
        initial_state = get_simulation_state()
        await manager.broadcast(initial_state)
        print(f"📡 Broadcasted initial state: track={initial_state.get('track', {}).get('name')}, agents={len(initial_state.get('agents', []))}")
        
        return {"status": "success", "message": "Simulation created"}
    except Exception as e:
        print(f"❌ Error creating simulation: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/api/simulation/start")
async def start_simulation():
    """Start the simulation."""
    global simulation_running

    if not simulation:
        return {"status": "error", "message": "No simulation created"}

    simulation_running = True

    # Start replay recording
    if replay_recorder:
        replay_recorder.start_recording({
            "track": simulation.environment.track.name,
            "drivers": len(list(simulation.agent_set)),
            "laps": simulation.environment.track.num_laps
        })

    # Start simulation loop in background
    asyncio.create_task(simulation_loop())

    return {"status": "success", "message": "Simulation started"}


@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop the simulation."""
    global simulation_running
    simulation_running = False

    # Stop replay recording
    if replay_recorder and replay_recorder.recording:
        replay_recorder.stop_recording()

    return {"status": "success", "message": "Simulation stopped"}


@app.post("/api/simulation/reset")
async def reset_simulation():
    """Reset the simulation."""
    global simulation, simulation_running
    simulation_running = False
    simulation = None

    return {"status": "success", "message": "Simulation reset"}


@app.get("/api/simulation/state")
async def get_state():
    """Get current simulation state."""
    return get_simulation_state()


@app.get("/api/tracks")
async def get_available_tracks():
    """Get list of available tracks."""
    tracks_dir = Path("tracks")
    if tracks_dir.exists():
        tracks = [f.stem for f in tracks_dir.glob("*.geojson")]
    else:
        tracks = ["monaco", "silverstone", "spa"]

    return {"tracks": tracks}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()

            # Handle client messages if needed
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Mount static files if they exist
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
