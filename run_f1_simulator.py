#!/usr/bin/env python3
"""
F1 Simulator Launcher

Launch the production-ready F1 simulator UI.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Launch the F1 simulator UI."""
    print("🏎️  Starting F1 Simulator...")
    print("=" * 60)
    print()
    print("Production-Ready Formula 1 Racing Simulation")
    print()
    print("Features:")
    print("  ✓ Real F1 track layouts (Monaco, Silverstone, Spa)")
    print("  ✓ Tire management with degradation")
    print("  ✓ Fuel system and weight effects")
    print("  ✓ ERS (Energy Recovery System)")
    print("  ✓ DRS (Drag Reduction System)")
    print("  ✓ Sector timing")
    print("  ✓ F1-style timing tower")
    print("  ✓ Live telemetry dashboard")
    print()
    print("=" * 60)
    print()
    print("🌐 Opening in your browser...")
    print()

    # Import and run the Solara app
    from shifters.ui import f1_simulator_ui

    # Run with solara
    import solara.server.starlette
    solara.server.starlette.run(f1_simulator_ui.Page, port=8765)


if __name__ == "__main__":
    main()
