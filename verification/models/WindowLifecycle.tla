--------------------------- MODULE WindowLifecycle ---------------------------
EXTENDS Naturals
CONSTANT SkipClose
VARIABLES phase, owned, closed, outcome
vars == <<phase, owned, closed, outcome>>

Init == /\ phase = "Opening" /\ owned = FALSE
        /\ closed = FALSE /\ outcome = "None"
Open == /\ phase = "Opening" /\ phase' = "Drawing" /\ owned' = TRUE
        /\ UNCHANGED <<closed, outcome>>
OpenFails == /\ phase = "Opening" /\ phase' = "OpenFailed"
             /\ UNCHANGED <<owned, closed, outcome>>
Draw == /\ phase = "Drawing" /\ phase' = "Capturing"
        /\ UNCHANGED <<owned, closed, outcome>>
Capture == /\ phase = "Capturing" /\ phase' = "Returned"
           /\ outcome' \in {"Done", "Fail"} /\ UNCHANGED <<owned, closed>>
Close == /\ phase = "Returned" /\ phase' = "Reporting"
         /\ closed' = ~SkipClose /\ owned' = SkipClose
         /\ UNCHANGED outcome
Report == /\ phase = "Reporting"
          /\ phase' = IF outcome = "Done" THEN "Printed" ELSE "CaptureFailed"
          /\ UNCHANGED <<owned, closed, outcome>>
Finished == /\ phase \in {"Printed", "CaptureFailed", "OpenFailed"}
            /\ UNCHANGED vars
Next == Open \/ OpenFails \/ Draw \/ Capture \/ Close \/ Report \/ Finished

ReportAfterClose == phase \in {"Reporting", "Printed", "CaptureFailed"}
                   => (closed /\ ~owned)
=============================================================================
