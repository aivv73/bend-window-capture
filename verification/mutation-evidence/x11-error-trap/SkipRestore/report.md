# X11ErrorTrap

TLC reached 54 states and 66 steps. The chart draws 7 states and 7 arrows.
The chart does not draw 21 steps that stay in one chart state.

## RestoredHandler breaks
The shortest path has 5 steps:
0. Previous handler active
1. publish capture context: Capture context published
2. install capture handler: Capture handler active
3. finish pending requests: Requests drained
4. skip restoring the handler: Capture handler left installed
5. clear capture context: Handler points at cleared context

## Rules that hold
FirstErrorWins, NoDeadlock
