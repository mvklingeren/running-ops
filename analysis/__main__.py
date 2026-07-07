"""Run all analyses: python -m analysis"""
from . import (bests, correlate, cp, decoupling, dynamics, elevation, fitness,
               intervals, load, quadrant, recovery, vo2max, volume, wbal,
               zones)

for mod in (volume, fitness, cp, wbal, intervals, zones, quadrant, load,
            vo2max, recovery, decoupling, dynamics, elevation, correlate,
            bests):
    mod.main()
    print()
