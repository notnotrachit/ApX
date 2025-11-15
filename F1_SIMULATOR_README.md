# 🏎️ F1 Simulator - Production-Ready Formula 1 Racing Simulation

A comprehensive, production-ready Formula 1 simulator with realistic tire management, fuel systems, ERS, DRS, and beautiful visualizations.

## ✨ Features

### 🏁 Core F1 Features
- **Real Track Layouts**: Load actual F1 circuits from GeoJSON (Monaco, Silverstone, Spa-Francorchamps)
- **Tire Management**: Realistic tire compounds (Soft, Medium, Hard, Intermediate, Wet) with degradation
- **Fuel System**: Fuel consumption and weight effects on performance
- **ERS (Energy Recovery System)**: Battery deployment and recovery simulation
- **DRS (Drag Reduction System)**: Detection and activation zones with speed boost
- **Sector Timing**: 3-sector timing just like real F1
- **Pit Stop Strategy**: Tire changes, refueling, and strategic pit stops

### 📊 Production-Ready UI
- **Track Visualization**: Real-time 2D track rendering from GeoJSON
- **F1-Style Timing Tower**: Live leaderboard with gaps, sectors, and tire info
- **Telemetry Dashboard**: Detailed car data (speed, tire wear, fuel, ERS, DRS)
- **Race Controls**: Configure tracks, drivers, and race parameters
- **Professional Styling**: Dark theme with F1-inspired design

### 🎮 Simulation Features
- **Multi-Agent**: Support for up to 20 drivers
- **Real-Time Updates**: Live simulation with smooth animations
- **Performance Tracking**: Lap times, sector times, best laps
- **Team Management**: Multiple teams with custom colors
- **Driver Skills**: Varying driver skill levels affecting performance

## 🚀 Quick Start

### Installation

1. Install dependencies:
```bash
pip install -e .
```

2. Launch the F1 simulator UI:
```bash
python run_f1_simulator.py
```

The simulator will open in your browser at `http://localhost:8765`

### Running a Demo Race

Run the demo script to see a programmatic F1 race:
```bash
python examples/f1_race_demo.py
```

## 📖 Usage Guide

### Using the UI

1. **Select Track**: Choose from Monaco, Silverstone, or Spa
2. **Configure Race**: Set number of drivers (2-20) and laps (1-20)
3. **Start Race**: Click "▶️ Start" to begin the simulation
4. **Watch Live**:
   - Track visualization shows cars in real-time
   - Timing tower displays live positions and gaps
   - Telemetry shows detailed data for the leader

### Custom Track Integration

Load your own F1 track from GeoJSON:

```python
from shifters import Track

# Load custom track
track = Track(
    length=5000,  # Default length, will be updated
    num_laps=10,
    track_type="circuit",
    geojson_file="path/to/your/track.geojson"
)
```

### Creating F1 Vehicles

```python
from shifters import F1Vehicle, TireCompound

vehicle = F1Vehicle(
    model=simulation,
    unique_id="driver_1",
    name="Hamilton",
    team_name="Mercedes",
    team_color="#00D2BE",
    driver_skill=0.95,  # 0.0 to 1.0
)

# Set tire compound
vehicle.tires.compound = TireCompound.SOFT
```

### Running a Simulation

```python
from shifters import MobilitySimulation, Track, F1Vehicle, TireCompound

# Create track
track = Track(
    length=5891,
    num_laps=5,
    track_type="circuit",
    name="Silverstone",
    geojson_file="tracks/silverstone.geojson"
)

# Create simulation
sim = MobilitySimulation(track=track, time_step=0.1)

# Add drivers
for i in range(20):
    vehicle = F1Vehicle(
        model=sim,
        unique_id=f"driver_{i}",
        name=f"Driver {i+1}",
        team_name=f"Team {i//2 + 1}",
        team_color="#FF0000"
    )
    sim.add_agent(vehicle)

# Run simulation
while not sim.is_race_complete():
    sim.step()

# Get results
rankings = sim.leaderboard.get_rankings()
for rank in rankings:
    print(f"{rank.position}. {rank.agent.name} - {rank.total_time:.2f}s")
```

## 🗺️ Track Format

Tracks are defined using GeoJSON with the following structure:

```json
{
  "type": "FeatureCollection",
  "properties": {
    "name": "Circuit Name",
    "length": 5891,
    "turns": 18
  },
  "features": [
    {
      "type": "Feature",
      "properties": {"type": "track"},
      "geometry": {
        "type": "LineString",
        "coordinates": [[lon1, lat1], [lon2, lat2], ...]
      }
    },
    {
      "type": "Feature",
      "properties": {"type": "drs_activation"},
      "geometry": {
        "type": "LineString",
        "coordinates": [[lon1, lat1], [lon2, lat2]]
      }
    }
  ]
}
```

### Included Tracks

- **Monaco** (`tracks/monaco.geojson`) - 3.337 km, 19 turns
- **Silverstone** (`tracks/silverstone.geojson`) - 5.891 km, 18 turns
- **Spa-Francorchamps** (`tracks/spa.geojson`) - 7.004 km, 19 turns

## 🏗️ Architecture

### Core Components

```
shifters/
├── agents/
│   ├── base_agent.py          # Base MobilityAgent and RacingVehicle
│   ├── f1_vehicle.py          # F1Vehicle with tires, fuel, ERS, DRS
│   └── tire_system.py         # TireSet, TireCompound, degradation
├── environment/
│   ├── track.py               # Track with GeoJSON support, sectors, DRS
│   └── geojson_parser.py      # GeoJSON parsing and coordinate conversion
├── simcore/
│   └── simulator.py           # MobilitySimulation engine
├── leaderboard/
│   └── leaderboard.py         # Real-time ranking system
└── ui/
    ├── f1_simulator_ui.py     # Production Solara UI
    ├── mesa_visualization.py  # Mesa native UI
    └── server.py              # WebSocket server
```

### Key Classes

#### F1Vehicle
The main F1 car agent with:
- **Tire System**: Compound selection, wear, temperature, grip
- **Fuel System**: Consumption, weight effects
- **ERS**: Energy recovery and deployment
- **DRS**: Automatic activation in DRS zones
- **Telemetry**: Comprehensive data output

#### Track
Enhanced track system supporting:
- **GeoJSON Loading**: Parse real circuit layouts
- **2D Coordinates**: Convert distance to (x, y) positions
- **Sector Timing**: 3-sector division
- **DRS Zones**: Detection and activation zones
- **Backward Compatible**: Works with simple 1D tracks too

#### TireSet
Realistic tire simulation:
- **5 Compounds**: Soft, Medium, Hard, Intermediate, Wet
- **Degradation**: Based on distance, speed, temperature
- **Temperature Model**: Optimal operating windows
- **Performance**: Grip reduction with wear

## 🎨 UI Components

### Track Visualization
- Real-time car positions on track layout
- DRS zone highlighting (green)
- Sector boundaries (red/yellow/green markers)
- Team colors for each car
- DRS activation indicators

### Timing Tower
- Live positions and gaps
- Lap times and sector numbers
- Tire compound and wear percentage
- Team identification
- Gap to leader

### Telemetry Dashboard
- Speed (km/h)
- Current lap and sector
- Tire wear with progress bar
- Tire compound
- Fuel level with progress bar
- ERS battery percentage
- DRS status (active/available/disabled)
- Pit stops count

### Race Controls
- Track selection dropdown
- Driver count slider (2-20)
- Lap count slider (1-20)
- Start/Pause button
- Reset button

### Race Statistics
- Track name and length
- Simulation time
- Step count
- Active drivers
- Finished count

## 🔧 Advanced Configuration

### Custom Tire Strategy

```python
from shifters.agents.tire_system import TireCompound, TireStrategy

# Manual pit stop with compound change
vehicle.pit_stop(new_compound=TireCompound.HARD)
vehicle.exit_pit_lane()

# Check tire condition
if vehicle.tires.needs_change(threshold=70.0):
    suggested = vehicle.tire_strategy.suggest_compound(
        current_lap=vehicle.lap,
        total_laps=50,
        current_compound=vehicle.tires.compound
    )
    vehicle.pit_stop(suggested)
```

### ERS Management

```python
# Deploy ERS for overtaking
vehicle.deploy_ers()

# Save ERS for later
vehicle.save_ers()

# Check ERS level
if vehicle.ers_energy_mj < 1.0:
    vehicle.save_ers()  # Save remaining energy
```

### DRS Configuration

```python
# Add DRS zones to track
track.add_drs_zone(
    zone_type='drs_detection',
    start_distance=1000,
    end_distance=1100,
    metadata={'name': 'Turn 1 Detection'}
)

track.add_drs_zone(
    zone_type='drs_activation',
    start_distance=1100,
    end_distance=1500,
    metadata={'name': 'Main Straight DRS'}
)
```

## 📊 Data Collection

### Telemetry Access

```python
# Get full telemetry for a vehicle
telemetry = vehicle.get_telemetry()

print(f"Speed: {telemetry['speed_kmh']} km/h")
print(f"Tire Wear: {telemetry['tire']['wear_percentage']}%")
print(f"Fuel: {telemetry['fuel_kg']} kg")
print(f"ERS: {telemetry['ers_percentage']}%")
print(f"DRS Active: {telemetry['drs_active']}")
print(f"Best Lap: {telemetry['best_lap']}s")
```

### Race Results

```python
# Get final rankings
rankings = simulation.leaderboard.get_rankings()

for rank in rankings:
    agent = rank.agent
    print(f"{rank.position}. {agent.name}")
    print(f"   Time: {rank.total_time:.2f}s")
    print(f"   Gap: +{rank.gap_to_leader:.2f}s")
    print(f"   Laps: {agent.lap}")
    print(f"   Best Lap: {min(agent.lap_times):.3f}s")
    print(f"   Pit Stops: {agent.pit_stops}")
```

## 🎯 Performance Tips

1. **Tire Strategy**: Soft tires are fastest but degrade quickly - plan pit stops carefully
2. **Fuel Management**: Heavy fuel at start reduces speed - cars get faster as fuel burns
3. **ERS Deployment**: Save ERS for overtaking or defending position
4. **DRS Usage**: DRS activates automatically when within 1 second in detection zones
5. **Driver Skill**: Higher skill = better tire management and consistency

## 🐛 Troubleshooting

### Track not loading
- Ensure GeoJSON file exists in `tracks/` directory
- Check GeoJSON format matches specification
- Verify coordinates are valid lat/lon pairs

### UI not updating
- Check that simulation is running (running.value == True)
- Verify background thread is active
- Refresh browser page

### Performance issues
- Reduce number of drivers
- Decrease simulation speed (increase time.sleep in loop)
- Simplify track (fewer points in GeoJSON)

## 📝 License

This project is part of the Shifters mobility simulator framework.

## 🤝 Contributing

Contributions welcome! See CONTRIBUTING.md for guidelines.

---

**Built with ❤️ using Mesa, Solara, and Python**
