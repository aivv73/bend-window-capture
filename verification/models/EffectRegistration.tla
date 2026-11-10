------------------------- MODULE EffectRegistration -------------------------
CONSTANTS SkipRegistration, WrongNativeUnsupportedCode
VARIABLES phase, backend, registered, returnedOwner, result
vars == <<phase, backend, registered, returnedOwner, result>>

Init == /\ phase = "Loading" /\ backend \in {"Native", "JavaScript", "UnsupportedNative"}
        /\ registered = FALSE /\ returnedOwner = FALSE /\ result = "None"
Register == /\ phase = "Loading" /\ phase' = "Ready"
            /\ registered' = ~SkipRegistration
            /\ UNCHANGED <<backend, returnedOwner, result>>
Dispatch == /\ phase = "Ready" /\ registered /\ phase' = "Returned"
            /\ returnedOwner' = TRUE
            /\ result' = IF backend = "Native" THEN "NativeResult"
                         ELSE IF backend = "UnsupportedNative" /\ WrongNativeUnsupportedCode
                              THEN "EIO" ELSE "ENOTSUP"
            /\ UNCHANGED <<backend, registered>>
Finished == /\ phase = "Returned" /\ UNCHANGED vars
Next == Register \/ Dispatch \/ Finished

ReadyHasHandler == phase \in {"Ready", "Returned"} => registered
UnsupportedReturnsENOTSUP == phase = "Returned" /\ backend # "Native" => result = "ENOTSUP"
=============================================================================
