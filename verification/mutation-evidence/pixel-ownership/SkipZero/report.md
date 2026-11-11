# PixelOwnership

TLC reached 59 states and 74 steps. The chart draws 8 states and 10 arrows.
The chart does not draw 34 steps that stay in one chart state.

## PaddingZeroAndOwned breaks
The shortest path has 10 steps:
0. No image acquired
1. acquire client image: Temporary image owned
2. choose array capacity: Temporary image owned
3. choose array capacity: Temporary image owned
4. allocate pixel array: Pixel array allocated
5. skip clearing pixel storage: Copying client pixels
6. copy a pixel: Copying client pixels
7. copy a pixel: Copying client pixels
8. copy a pixel: Copying client pixels
9. release client image: Temporary image released
10. return independent capture: Capture returned with stale padding

## Rules that hold
AllImagesReleased, NoDeadlock
