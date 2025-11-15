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
    print("  ✓ Dynamic weather system")
    print("  ✓ Safety car (VSC & Full SC)")
    print("  ✓ AI strategy engine")
    print("  ✓ Damage system")
    print("  ✓ Real-time telemetry")
    print()
    print("=" * 60)
    print()
    print("🌐 Server starting on http://localhost:8765")
    print("📱 Open http://localhost:8765 in your browser")
    print()

    # Run the FastAPI app
    import uvicorn
    from shifters.ui.app import app

    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")


if __name__ == "__main__":
    main()
