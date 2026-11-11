------------------------- MODULE CaptureTransaction -------------------------
EXTENDS Naturals
CONSTANT SkipResizeCheck
VARIABLES phase, failure, changed, result, validated
vars == <<phase, failure, changed, result, validated>>

Init == /\ phase = "Start" /\ failure = "None" /\ changed = FALSE
        /\ result = "None" /\ validated = FALSE
Supported == /\ phase = "Start" /\ phase' = "Synchronize"
             /\ UNCHANGED <<failure, changed, result, validated>>
Unsupported == /\ phase = "Start" /\ phase' = "Returned"
               /\ result' = "ENOTSUP"
               /\ UNCHANGED <<failure, changed, validated>>
Synchronize == /\ phase = "Synchronize" /\ phase' = "Eligibility"
               /\ UNCHANGED <<failure, changed, result, validated>>
PendingError == /\ phase = "Synchronize" /\ phase' = "Finalize"
                /\ failure' = "ENOENT"
                /\ UNCHANGED <<changed, result, validated>>
Eligible == /\ phase = "Eligibility" /\ phase' = "ReadPixels"
            /\ UNCHANGED <<failure, changed, result, validated>>
Rejected == /\ phase = "Eligibility" /\ phase' = "Finalize"
            /\ failure' \in {"EIO", "EINVAL", "EAGAIN", "EOVERFLOW", "ENOTSUP"}
            /\ UNCHANGED <<changed, result, validated>>
ReadPixels == /\ phase = "ReadPixels" /\ phase' = "Recheck"
              /\ UNCHANGED <<failure, changed, result, validated>>
ReadFails == /\ phase = "ReadPixels" /\ phase' = "Finalize"
             /\ failure' \in {"EIO", "ENOTSUP"}
             /\ UNCHANGED <<changed, result, validated>>
Recheck == /\ phase = "Recheck" /\ phase' = "Finalize"
           /\ changed' \in BOOLEAN
           /\ failure' = IF changed' /\ ~SkipResizeCheck THEN "EAGAIN" ELSE "None"
           /\ validated' = ~changed'
           /\ UNCHANGED result
Finalize == /\ phase = "Finalize" /\ phase' = "Returned"
            /\ result' = IF failure = "None" THEN "Done" ELSE failure
            /\ UNCHANGED <<failure, changed, validated>>
ProtocolError == /\ phase = "Finalize" /\ phase' = "Returned"
                 /\ result' \in {"ENOENT", "EAGAIN", "EINVAL", "EIO"}
                 /\ UNCHANGED <<failure, changed, validated>>
Finished == /\ phase = "Returned" /\ UNCHANGED vars
Next == Supported \/ Unsupported \/ Synchronize \/ PendingError \/ Eligible
        \/ Rejected \/ ReadPixels \/ ReadFails \/ Recheck \/ Finalize
        \/ ProtocolError \/ Finished

OnlyValidatedCaptureSucceeds == result = "Done" => (validated /\ ~changed)
=============================================================================
