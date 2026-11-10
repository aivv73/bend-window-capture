---------------------------- MODULE X11ErrorTrap ----------------------------
EXTENDS Naturals, Sequences
CONSTANTS SkipRestore, OverwriteFirstError
VARIABLES phase, context, handler, drained, errors, first, forwarded
vars == <<phase, context, handler, drained, errors, first, forwarded>>

Init == /\ phase = "Idle" /\ context = FALSE /\ handler = "Previous"
        /\ drained = FALSE /\ errors = <<>> /\ first = 0 /\ forwarded = 0
SetContext == /\ phase = "Idle" /\ phase' = "Context"
              /\ context' = TRUE
              /\ UNCHANGED <<handler, drained, errors, first, forwarded>>
Install == /\ phase = "Context" /\ phase' = "Active"
           /\ handler' = "Capture"
           /\ UNCHANGED <<context, drained, errors, first, forwarded>>
OwnedError == /\ phase = "Active" /\ Len(errors) < 2
              /\ \E code \in {1, 2}:
                    /\ errors' = Append(errors, code)
                    /\ first' = IF first = 0 \/ OverwriteFirstError THEN code ELSE first
              /\ UNCHANGED <<phase, context, handler, drained, forwarded>>
UnrelatedError == /\ phase = "Active" /\ Len(errors) < 2
                  /\ errors' = Append(errors, 0) /\ forwarded' = forwarded + 1
                  /\ UNCHANGED <<phase, context, handler, drained, first>>
Drain == /\ phase = "Active" /\ phase' = "Drained" /\ drained' = TRUE
         /\ UNCHANGED <<context, handler, errors, first, forwarded>>
Restore == /\ phase = "Drained" /\ phase' = "Restored"
           /\ handler' = IF SkipRestore THEN "Capture" ELSE "Previous"
           /\ UNCHANGED <<context, drained, errors, first, forwarded>>
ClearContext == /\ phase = "Restored" /\ phase' = "Returned"
                /\ context' = FALSE
                /\ UNCHANGED <<handler, drained, errors, first, forwarded>>
Finished == /\ phase = "Returned" /\ UNCHANGED vars
Next == SetContext \/ Install \/ OwnedError \/ UnrelatedError \/ Drain
        \/ Restore \/ ClearContext \/ Finished

RestoredHandler == /\ (handler = "Capture" => context)
                   /\ (phase = "Returned" => (drained /\ handler = "Previous"))
OwnedIndices == {i \in 1..Len(errors) : errors[i] # 0}
FirstErrorWins == first = IF OwnedIndices = {} THEN 0
                         ELSE errors[CHOOSE i \in OwnedIndices :
                              \A j \in OwnedIndices : i <= j]
=============================================================================
