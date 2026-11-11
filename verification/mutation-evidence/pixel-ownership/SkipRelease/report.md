# PixelOwnership

TLC reached 59 states and 74 steps. The chart draws 8 states and 7 arrows.
The chart does not draw 39 steps that stay in one chart state.

## AllImagesReleased breaks
The shortest path has 2 steps:
0. No image acquired
1. acquire client image: Temporary image owned
2. validation fails without image cleanup: Capture failed, image leaked

## Rules that hold
PaddingZeroAndOwned, NoDeadlock
