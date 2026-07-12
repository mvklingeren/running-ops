"""Run all analyses: python -m analysis"""
from . import (bests, correlate, cp, decoupling, durability, dynamics,
               elevation, fitness, intervals, load, quadrant, recovery,
               vo2max, volume, wbal, zones)

for mod in (volume, load, recovery, fitness, cp, wbal, vo2max, durability,
            decoupling, intervals, zones, quadrant, dynamics, elevation,
            correlate, bests):
    mod.main()
    print()
