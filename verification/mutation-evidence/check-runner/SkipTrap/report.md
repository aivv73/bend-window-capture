# CheckRunner

TLC reached 12 states and 17 steps. The chart draws 9 states and 12 arrows.
The chart does not draw 3 steps that stay in one chart state.

## ExitCleansBuild breaks
The shortest path has 5 steps:
0. Checking the Bend proof
1. proof passes: Creating a build directory
2. create temporary directory: Build directory exists
3. continue without exit cleanup: Cleanup missing
4. a check fails: Script exiting
5. exit with the directory still present: Build directory leaked

## Rules that hold
NoDeadlock
