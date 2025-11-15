"""
Production-Ready F1 Simulator UI with Solara

Features:
- Real track visualization from GeoJSON
- F1-style timing tower
- Telemetry dashboard
- Sector timing
- Tire and fuel management display
- Professional styling
"""

import solara
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from typing import Optional, Dict, Any, List
import threading
import time
import os

from ..simcore.simulator import MobilitySimulation
from ..environment.track import Track
from ..agents.f1_vehicle import F1Vehicle, TireCompound


# Reactive state management
simulation_state = solara.reactive(None)
running = solara.reactive(False)
current_step = solara.reactive(0)
selected_track = solara.reactive("monaco")
num_drivers = solara.reactive(20)
num_laps = solara.reactive(5)

# Background simulation thread
simulation_thread = None
stop_thread = False


def run_simulation_loop():
    """Background thread to run simulation continuously."""
    global stop_thread

    while not stop_thread and running.value:
        sim = simulation_state.value
        if sim and not sim.is_race_complete():
            sim.step()
            current_step.value = sim.current_step
            time.sleep(0.1)  # 10 steps per second
        else:
            running.value = False
            break


def start_simulation():
    """Start the simulation."""
    global simulation_thread, stop_thread

    if running.value:
        return

    # Create or reset simulation
    if simulation_state.value is None:
        create_simulation()

    running.value = True
    stop_thread = False

    # Start background thread
    simulation_thread = threading.Thread(target=run_simulation_loop, daemon=True)
    simulation_thread.start()


def stop_simulation():
    """Stop the simulation."""
    global stop_thread
    stop_thread = True
    running.value = False


def reset_simulation():
    """Reset the simulation."""
    stop_simulation()
    simulation_state.value = None
    current_step.value = 0


def create_simulation():
    """Create a new simulation with selected parameters."""
    # Load track GeoJSON
    track_file = f"/home/user/ApX/tracks/{selected_track.value}.geojson"

    # Create track with default length (will be updated by GeoJSON)
    if os.path.exists(track_file):
        track = Track(
            length=5000,  # Default, will be overwritten
            num_laps=num_laps.value,
            track_type="circuit",
            geojson_file=track_file
        )
    else:
        # Fallback to simple track
        track = Track(
            length=5000,
            num_laps=num_laps.value,
            track_type="circuit",
            name="Default Circuit"
        )

    # Create simulation
    sim = MobilitySimulation(
        track=track,
        time_step=0.1,
        enable_live_updates=True
    )

    # Create F1 vehicles with different teams and colors
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
        "Hamilton", "Verstappen", "Leclerc", "Sainz", "Russell", "Perez",
        "Norris", "Piastri", "Alonso", "Stroll", "Gasly", "Ocon",
        "Albon", "Sargeant", "Tsunoda", "Ricciardo", "Bottas", "Zhou",
        "Magnussen", "Hulkenberg"
    ]

    for i in range(min(num_drivers.value, 20)):
        team_idx = i // 2  # 2 drivers per team
        team_name, team_color = teams[team_idx % len(teams)]

        vehicle = F1Vehicle(
            model=sim,
            unique_id=f"driver_{i}",
            name=driver_names[i % len(driver_names)],
            team_name=team_name,
            team_color=team_color,
            driver_skill=0.8 + (i % 10) * 0.02,  # Varying skill levels
        )

        # Random starting compounds
        start_compounds = [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]
        vehicle.tires.compound = start_compounds[i % 3]

        sim.add_agent(vehicle)

    simulation_state.value = sim


@solara.component
def TrackVisualization():
    """Render the track with live car positions."""

    sim = simulation_state.value

    if sim is None:
        return solara.Markdown("## 🏁 Select parameters and click Start to begin")

    # Create matplotlib figure
    fig = Figure(figsize=(12, 8), facecolor='#0A0A0A')
    ax = fig.add_subplot(111)
    ax.set_facecolor('#1A1A1A')

    track = sim.environment.track

    # Draw track layout
    if track.has_geojson and track.geojson_parser:
        # Draw actual track from GeoJSON
        points = track.geojson_parser.track_points

        if points:
            xs = [p.x for p in points]
            ys = [p.y for p in points]

            # Draw track outline
            ax.plot(xs + [xs[0]], ys + [ys[0]], 'w-', linewidth=8, alpha=0.3)
            ax.plot(xs + [xs[0]], ys + [ys[0]], 'w-', linewidth=4, alpha=0.6)

            # Draw DRS zones
            for zone in track.drs_zones:
                if zone.zone_type == 'drs_activation':
                    # Highlight DRS zones in green
                    start_point = track.geojson_parser.get_point_at_distance(zone.start_distance)
                    end_point = track.geojson_parser.get_point_at_distance(zone.end_distance)

                    if start_point and end_point:
                        ax.plot([start_point.x, end_point.x],
                               [start_point.y, end_point.y],
                               'g-', linewidth=10, alpha=0.4, label='DRS Zone')

            # Draw sector boundaries
            sector_colors = ['#FF0000', '#FFFF00', '#00FF00']
            for i, boundary in enumerate(track.sector_boundaries[1:-1], 1):
                point = track.geojson_parser.get_point_at_distance(boundary)
                if point:
                    ax.plot(point.x, point.y, 'o', color=sector_colors[i-1],
                           markersize=15, alpha=0.7, label=f'Sector {i}')

    else:
        # Draw simple circular track
        circle = patches.Circle((500, 500), 400, fill=False,
                               edgecolor='white', linewidth=8, alpha=0.3)
        ax.add_patch(circle)
        circle2 = patches.Circle((500, 500), 400, fill=False,
                                edgecolor='white', linewidth=4, alpha=0.6)
        ax.add_patch(circle2)

    # Draw cars
    agents = list(sim.agent_set)
    for agent in agents:
        if isinstance(agent, F1Vehicle):
            # Get 2D position
            pos_2d = track.get_2d_position(agent.position)

            if pos_2d:
                x, y = pos_2d
            else:
                # Fallback to circular layout
                angle = (agent.position / track.length) * 2 * 3.14159
                x = 500 + 400 * float(solara.use_memo(lambda: __import__('math').cos(angle)))
                y = 500 + 400 * float(solara.use_memo(lambda: __import__('math').sin(angle)))

            # Draw car
            color = agent.team_color
            ax.plot(x, y, 'o', color=color, markersize=12,
                   markeredgecolor='white', markeredgewidth=2)

            # Draw DRS indicator if active
            if agent.drs_active:
                ax.plot(x, y, '*', color='#00FF00', markersize=20, alpha=0.7)

    # Styling
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1000)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"{track.name} - Lap {agents[0].lap if agents else 0}/{track.num_laps}",
                color='white', fontsize=20, fontweight='bold', pad=20)

    # Add legend
    if track.has_geojson:
        ax.legend(loc='upper right', facecolor='#1A1A1A', edgecolor='white',
                 labelcolor='white', fontsize=10)

    fig.tight_layout()

    return solara.FigureMatplotlib(fig, dependencies=[current_step.value])


@solara.component
def TimingTower():
    """F1-style timing tower showing live positions."""

    sim = simulation_state.value

    if sim is None:
        return solara.Card("No simulation running")

    # Get leaderboard
    rankings = sim.leaderboard.get_rankings()

    # Create timing tower HTML
    html_rows = []

    html_rows.append("""
    <style>
        .timing-tower {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            border-radius: 8px;
            padding: 16px;
            color: white;
            font-family: 'Courier New', monospace;
            max-height: 600px;
            overflow-y: auto;
        }
        .timing-header {
            display: grid;
            grid-template-columns: 50px 200px 100px 100px 100px 120px;
            gap: 12px;
            padding: 12px;
            background: #FF1E00;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            margin-bottom: 8px;
        }
        .timing-row {
            display: grid;
            grid-template-columns: 50px 200px 100px 100px 100px 120px;
            gap: 12px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-left: 4px solid;
            margin-bottom: 4px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .timing-row:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(4px);
        }
        .position {
            font-weight: bold;
            font-size: 18px;
        }
        .driver-name {
            font-weight: bold;
        }
        .team-name {
            font-size: 11px;
            opacity: 0.7;
        }
        .sector-purple { color: #A020F0; font-weight: bold; }
        .sector-green { color: #00FF00; font-weight: bold; }
        .sector-yellow { color: #FFFF00; font-weight: bold; }
        .tire-soft { color: #FF0000; }
        .tire-medium { color: #FFFF00; }
        .tire-hard { color: #FFFFFF; }
    </style>
    <div class="timing-tower">
        <div class="timing-header">
            <div>POS</div>
            <div>DRIVER</div>
            <div>LAP TIME</div>
            <div>SECTOR</div>
            <div>TIRE</div>
            <div>GAP</div>
        </div>
    """)

    for rank in rankings[:20]:  # Top 20
        agent = rank.agent

        if not isinstance(agent, F1Vehicle):
            continue

        # Format lap time
        last_lap = f"{agent.lap_times[-1]:.3f}s" if agent.lap_times else "--"

        # Format sector
        sector_display = f"S{agent.current_sector}"

        # Tire info
        tire = agent.tires
        tire_color_class = f"tire-{tire.compound.value}"
        tire_display = f"{tire.compound.value[:3].upper()} {tire.wear_percentage:.0f}%"

        # Gap to leader
        if rank.position == 1:
            gap_display = "Leader"
        else:
            gap_display = f"+{rank.gap_to_leader:.1f}s"

        # Position color (top 3 get special colors)
        border_color = agent.team_color

        html_rows.append(f"""
        <div class="timing-row" style="border-left-color: {border_color};">
            <div class="position">{rank.position}</div>
            <div>
                <div class="driver-name">{agent.name}</div>
                <div class="team-name">{agent.team_name}</div>
            </div>
            <div>{last_lap}</div>
            <div>{sector_display}</div>
            <div class="{tire_color_class}">{tire_display}</div>
            <div>{gap_display}</div>
        </div>
        """)

    html_rows.append("</div>")

    return solara.HTML("".join(html_rows), dependencies=[current_step.value])


@solara.component
def TelemetryPanel():
    """Telemetry dashboard showing detailed car data."""

    sim = simulation_state.value

    if sim is None:
        return solara.Card("No simulation running")

    # Get leader
    rankings = sim.leaderboard.get_rankings()
    if not rankings:
        return solara.Card("No drivers")

    leader = rankings[0].agent

    if not isinstance(leader, F1Vehicle):
        return solara.Card("No F1 vehicle found")

    telemetry = leader.get_telemetry()

    # Create telemetry display
    html = f"""
    <style>
        .telemetry {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            border-radius: 8px;
            padding: 20px;
            color: white;
            font-family: 'Courier New', monospace;
        }}
        .telemetry-header {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid {leader.team_color};
        }}
        .telemetry-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}
        .telemetry-item {{
            background: rgba(255, 255, 255, 0.05);
            padding: 12px;
            border-radius: 4px;
            border-left: 3px solid {leader.team_color};
        }}
        .telemetry-label {{
            font-size: 11px;
            opacity: 0.7;
            margin-bottom: 4px;
        }}
        .telemetry-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            margin-top: 8px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            transition: width 0.3s;
        }}
    </style>
    <div class="telemetry">
        <div class="telemetry-header">
            📊 {leader.name} ({leader.team_name})
        </div>
        <div class="telemetry-grid">
            <div class="telemetry-item">
                <div class="telemetry-label">SPEED</div>
                <div class="telemetry-value">{telemetry['speed_kmh']:.1f} km/h</div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">LAP / SECTOR</div>
                <div class="telemetry-value">L{telemetry['lap']} / S{telemetry['sector']}</div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">TIRE WEAR</div>
                <div class="telemetry-value">{telemetry['tire']['wear_percentage']:.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {telemetry['tire']['wear_percentage']}%; background: #FF1E00;"></div>
                </div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">TIRE COMPOUND</div>
                <div class="telemetry-value">{telemetry['tire']['compound_name']}</div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">FUEL</div>
                <div class="telemetry-value">{telemetry['fuel_kg']:.1f} kg</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {(telemetry['fuel_kg']/110)*100}%; background: #00D2BE;"></div>
                </div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">ERS BATTERY</div>
                <div class="telemetry-value">{telemetry['ers_percentage']:.0f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {telemetry['ers_percentage']}%; background: #00FF00;"></div>
                </div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">DRS STATUS</div>
                <div class="telemetry-value">{'🟢 ACTIVE' if telemetry['drs_active'] else '🟡 AVAILABLE' if telemetry['drs_available'] else '🔴 DISABLED'}</div>
            </div>
            <div class="telemetry-item">
                <div class="telemetry-label">PIT STOPS</div>
                <div class="telemetry-value">{telemetry['pit_stops']}</div>
            </div>
        </div>
    </div>
    """

    return solara.HTML(html, dependencies=[current_step.value])


@solara.component
def RaceControls():
    """Control panel for race configuration and controls."""

    with solara.Card("🏁 F1 Simulator Controls", style="background: linear-gradient(135deg, #FF1E00 0%, #DC0000 100%); color: white;"):
        with solara.Column(gap="20px"):
            # Track selection
            solara.Select(
                label="Track",
                value=selected_track,
                values=["monaco", "silverstone", "spa"],
                style="font-weight: bold;"
            )

            # Number of drivers
            solara.SliderInt(
                label=f"Drivers: {num_drivers.value}",
                value=num_drivers,
                min=2,
                max=20,
                disabled=running.value
            )

            # Number of laps
            solara.SliderInt(
                label=f"Laps: {num_laps.value}",
                value=num_laps,
                min=1,
                max=20,
                disabled=running.value
            )

            # Control buttons
            with solara.Row(gap="10px"):
                solara.Button(
                    "▶️ Start" if not running.value else "⏸️ Pause",
                    on_click=lambda: start_simulation() if not running.value else stop_simulation(),
                    color="success" if not running.value else "warning",
                    style="flex: 1; font-weight: bold;"
                )

                solara.Button(
                    "🔄 Reset",
                    on_click=reset_simulation,
                    color="error",
                    disabled=running.value,
                    style="flex: 1; font-weight: bold;"
                )


@solara.component
def RaceStats():
    """Display race statistics."""

    sim = simulation_state.value

    if sim is None:
        return solara.Card("No race data")

    track = sim.environment.track
    agents = list(sim.agent_set)
    active_count = sum(1 for a in agents if not a.finished)
    finished_count = sum(1 for a in agents if a.finished)

    stats_html = f"""
    <style>
        .race-stats {{
            background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
            border-radius: 8px;
            padding: 16px;
            color: white;
            font-family: 'Courier New', monospace;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .stat-label {{
            opacity: 0.7;
            font-size: 12px;
        }}
        .stat-value {{
            font-weight: bold;
            font-size: 14px;
        }}
    </style>
    <div class="race-stats">
        <div class="stat-row">
            <div class="stat-label">TRACK</div>
            <div class="stat-value">{track.name}</div>
        </div>
        <div class="stat-row">
            <div class="stat-label">LENGTH</div>
            <div class="stat-value">{track.length:.0f}m</div>
        </div>
        <div class="stat-row">
            <div class="stat-label">SIMULATION TIME</div>
            <div class="stat-value">{sim.simulation_time:.1f}s</div>
        </div>
        <div class="stat-row">
            <div class="stat-label">STEPS</div>
            <div class="stat-value">{sim.current_step}</div>
        </div>
        <div class="stat-row">
            <div class="stat-label">ACTIVE DRIVERS</div>
            <div class="stat-value">{active_count}</div>
        </div>
        <div class="stat-row">
            <div class="stat-label">FINISHED</div>
            <div class="stat-value">{finished_count}</div>
        </div>
    </div>
    """

    return solara.HTML(stats_html, dependencies=[current_step.value])


@solara.component
def Page():
    """Main F1 Simulator UI Page."""

    with solara.Column(gap="20px", style={"padding": "20px", "background": "#0A0A0A", "min-height": "100vh"}):
        # Title
        solara.HTML("""
        <h1 style="color: white; text-align: center; font-size: 48px; font-weight: bold; margin-bottom: 10px; text-shadow: 0 0 20px #FF1E00;">
            🏎️ F1 SIMULATOR
        </h1>
        <p style="color: #888; text-align: center; font-size: 16px; margin-bottom: 30px;">
            Production-Ready Formula 1 Racing Simulation
        </p>
        """)

        with solara.Columns([3, 9], gutters_dense=True):
            # Left sidebar - Controls and Stats
            with solara.Column(gap="20px"):
                RaceControls()
                RaceStats()

            # Right side - Main view
            with solara.Column(gap="20px"):
                # Track visualization
                TrackVisualization()

        # Bottom panels - Timing and Telemetry
        with solara.Columns([6, 6], gutters_dense=True):
            TimingTower()
            TelemetryPanel()
