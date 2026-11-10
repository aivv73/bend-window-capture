# EffectRegistration

TLC reached 6 states and 3 steps. The chart draws 2 states and 1 arrows.

## ReadyHasHandler breaks
The shortest path has 1 step:
0. Module loading
1. module loads without registering capture: Capture handler missing

## NoDeadlock breaks
The shortest path has 1 step:
0. Module loading
1. module loads without registering capture: Capture handler missing

## Rules that hold
UnsupportedReturnsENOTSUP
