--------------------------- MODULE PixelOwnership ---------------------------
EXTENDS Naturals
CONSTANTS SkipZero, SkipRelease
VARIABLES phase, count, capacity, copied, image, zeroed, destroyed
vars == <<phase, count, capacity, copied, image, zeroed, destroyed>>

Init == /\ phase = "Start" /\ count \in {1, 3, 4, 5}
        /\ capacity = 1 /\ copied = 0 /\ image = FALSE
        /\ zeroed = FALSE /\ destroyed = 0
Acquire == /\ phase = "Start" /\ phase' = "Image" /\ image' = TRUE
           /\ UNCHANGED <<count, capacity, copied, zeroed, destroyed>>
FailBeforeImage == /\ phase = "Start" /\ phase' = "Failed"
                   /\ UNCHANGED <<count, capacity, copied, image, zeroed, destroyed>>
FailAfterImage == /\ phase = "Image" /\ phase' = "Failed"
                  /\ image' = SkipRelease
                  /\ destroyed' = IF SkipRelease THEN destroyed ELSE destroyed + 1
                  /\ UNCHANGED <<count, capacity, copied, zeroed>>
Grow == /\ phase = "Image" /\ capacity < count
        /\ capacity' = capacity * 2
        /\ UNCHANGED <<phase, count, copied, image, zeroed, destroyed>>
Allocate == /\ phase = "Image" /\ capacity >= count /\ phase' = "Buffer"
            /\ UNCHANGED <<count, capacity, copied, image, zeroed, destroyed>>
Zero == /\ phase = "Buffer" /\ phase' = "Copying" /\ zeroed' = ~SkipZero
        /\ UNCHANGED <<count, capacity, copied, image, destroyed>>
Copy == /\ phase = "Copying" /\ copied < count /\ copied' = copied + 1
        /\ UNCHANGED <<phase, count, capacity, image, zeroed, destroyed>>
ReleaseImage == /\ phase = "Copying" /\ copied = count /\ phase' = "Copied"
                /\ image' = FALSE /\ destroyed' = destroyed + 1
                /\ UNCHANGED <<count, capacity, copied, zeroed>>
Publish == /\ phase = "Copied" /\ phase' = "Returned"
           /\ UNCHANGED <<count, capacity, copied, image, zeroed, destroyed>>
Finished == /\ phase \in {"Returned", "Failed"} /\ UNCHANGED vars
Next == Acquire \/ FailBeforeImage \/ FailAfterImage \/ Grow \/ Allocate
        \/ Zero \/ Copy \/ ReleaseImage \/ Publish \/ Finished

PaddingZeroAndOwned == phase = "Returned"
                      => /\ ~image /\ destroyed = 1 /\ copied = count
                         /\ capacity >= count /\ capacity < 2 * count
                         /\ (capacity > count => zeroed)
AllImagesReleased == phase \in {"Returned", "Failed"} => ~image
=============================================================================
