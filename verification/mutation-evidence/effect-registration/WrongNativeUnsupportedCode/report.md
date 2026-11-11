# EffectRegistration

TLC reached 9 states and 9 steps. The chart draws 5 states and 4 arrows.
The chart does not draw 3 steps that stay in one chart state.

## UnsupportedReturnsENOTSUP breaks
The shortest path has 2 steps:
0. Module loading
1. initialize the module: Capture handler registered
2. return an unexpected error: Window and unexpected error returned

## Rules that hold
ReadyHasHandler, NoDeadlock
