"""Run all analyses: python -m analysis"""
from . import (bests, cp, decoupling, dynamics, fitness, intervals, quadrant,
               recovery, volume, wbal, zones)

for mod in (volume, fitness, cp, wbal, intervals, zones, quadrant,
            recovery, decoupling, dynamics, bests):
    mod.main()
    print()
