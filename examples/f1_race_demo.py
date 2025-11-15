#!/usr/bin/env python3
"""
F1 Race Demo

Demonstrates how to use the F1 simulator programmatically.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shifters import Track, F1Vehicle, MobilitySimulation, TireCompound


def main():
    """Run a demo F1 race."""
    print("🏎️  F1 Race Simulation Demo")
    print("=" * 60)

    # Create track from GeoJSON
    print("\n📍 Loading Monaco Circuit...")
    track_file = os.path.join(os.path.dirname(__file__), '..', 'tracks', 'monaco.geojson')

    track = Track(
        length=3337,  # Will be overwritten by GeoJSON
        num_laps=3,
        track_type="circuit",
        geojson_file=track_file
    )

    print(f"   Track: {track.name}")
    print(f"   Length: {track.length:.0f}m")
    print(f"   Laps: {track.num_laps}")
    print(f"   Sectors: 3")
    print(f"   DRS Zones: {len(track.drs_zones)}")

    # Create simulation
    print("\n🏁 Creating simulation...")
    sim = MobilitySimulation(
        track=track,
        time_step=0.1,
        enable_live_updates=True
    )

    # Create F1 drivers
    teams = [
        ("Red Bull Racing", "#1E41FF", "Verstappen"),
        ("Red Bull Racing", "#1E41FF", "Perez"),
        ("Ferrari", "#DC0000", "Leclerc"),
        ("Ferrari", "#DC0000", "Sainz"),
        ("Mercedes", "#00D2BE", "Hamilton"),
        ("Mercedes", "#00D2BE", "Russell"),
    ]

    print("\n👥 Creating drivers...")
    for i, (team_name, team_color, driver_name) in enumerate(teams):
        vehicle = F1Vehicle(
            model=sim,
            unique_id=f"driver_{i}",
            name=driver_name,
            team_name=team_name,
            team_color=team_color,
            driver_skill=0.85 + (i % 3) * 0.05,
        )

        # Vary starting tire compounds
        compounds = [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]
        vehicle.tires.compound = compounds[i % 3]

        sim.add_agent(vehicle)
        print(f"   {driver_name} ({team_name}) - {compounds[i % 3].value.upper()} tires")

    # Run simulation
    print("\n🏁 Starting race...")
    print("=" * 60)

    max_steps = 3000  # Limit simulation steps
    step_count = 0

    while not sim.is_race_complete() and step_count < max_steps:
        sim.step()
        step_count += 1

        # Print updates every 100 steps
        if step_count % 100 == 0:
            rankings = sim.leaderboard.get_rankings()
            leader = rankings[0].agent if rankings else None

            if leader and isinstance(leader, F1Vehicle):
                print(f"\n⏱️  Step {step_count} | Lap {leader.lap}/{track.num_laps}")
                print(f"   Leader: {leader.name} ({leader.team_name})")
                print(f"   Speed: {leader.speed:.1f} km/h")
                print(f"   Tire: {leader.tires.compound.value.upper()} ({leader.tires.wear_percentage:.1f}% worn)")
                print(f"   Fuel: {leader.fuel_kg:.1f} kg")
                print(f"   Position: {leader.position:.0f}m / {track.length:.0f}m")

                # Show top 3
                print("\n   Top 3:")
                for i, rank in enumerate(rankings[:3], 1):
                    agent = rank.agent
                    if isinstance(agent, F1Vehicle):
                        gap = f"+{rank.gap_to_leader:.1f}s" if i > 1 else "Leader"
                        print(f"   {i}. {agent.name} - {gap}")

    # Final results
    print("\n" + "=" * 60)
    print("🏁 RACE FINISHED!")
    print("=" * 60)

    rankings = sim.leaderboard.get_rankings()

    print("\n🏆 Final Results:\n")
    for i, rank in enumerate(rankings, 1):
        agent = rank.agent
        if isinstance(agent, F1Vehicle):
            best_lap = min(agent.lap_times) if agent.lap_times else 0
            gap = f"+{rank.gap_to_leader:.1f}s" if i > 1 else "WINNER"

            print(f"{i:2d}. {agent.name:15s} ({agent.team_name:20s}) - {gap}")
            print(f"     Laps: {agent.lap} | Best Lap: {best_lap:.3f}s | Pit Stops: {agent.pit_stops}")
            print(f"     Final Tire: {agent.tires.compound.value.upper()} ({agent.tires.wear_percentage:.0f}% worn)")
            print()

    print("=" * 60)
    print("\n✅ Simulation complete!")


if __name__ == "__main__":
    main()
