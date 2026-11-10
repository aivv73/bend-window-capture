# X11ErrorTrap

TLC reached 54 states and 66 steps. The chart draws 8 states and 8 arrows.
The chart does not draw 25 steps that stay in one chart state.

## FirstErrorWins breaks
The shortest path has 4 steps:
0. Previous handler active
1. publish capture context: Capture context published
2. install capture handler: Capture handler active
3. capture request fails: First capture error retained
4. another error replaces the first: First capture error overwritten

## Rules that hold
RestoredHandler, NoDeadlock
