----------------------------- MODULE CheckRunner -----------------------------
CONSTANT SkipTrap
VARIABLES phase, directory, armed, status
vars == <<phase, directory, armed, status>>

Init == /\ phase = "Proof" /\ directory = FALSE /\ armed = FALSE /\ status = "None"
ProofPasses == /\ phase = "Proof" /\ phase' = "Create"
               /\ UNCHANGED <<directory, armed, status>>
ProofFails == /\ phase = "Proof" /\ phase' = "Exiting" /\ status' = "Fail"
              /\ UNCHANGED <<directory, armed>>
Create == /\ phase = "Create" /\ phase' = "Arm" /\ directory' = TRUE
          /\ UNCHANGED <<armed, status>>
CreateFails == /\ phase = "Create" /\ phase' = "Exiting" /\ status' = "Fail"
               /\ UNCHANGED <<directory, armed>>
Arm == /\ phase = "Arm" /\ phase' = "Compile" /\ armed' = ~SkipTrap
       /\ UNCHANGED <<directory, status>>
Compile == /\ phase = "Compile" /\ phase' = "Run"
           /\ UNCHANGED <<directory, armed, status>>
Run == /\ phase = "Run" /\ phase' = "Compare"
       /\ UNCHANGED <<directory, armed, status>>
Fail == /\ phase \in {"Compile", "Run", "Compare"}
        /\ phase' = "Exiting" /\ status' = "Fail"
        /\ UNCHANGED <<directory, armed>>
Pass == /\ phase = "Compare" /\ phase' = "Exiting" /\ status' = "Pass"
        /\ UNCHANGED <<directory, armed>>
Exit == /\ phase = "Exiting" /\ phase' = "Exited"
        /\ directory' = IF armed THEN FALSE ELSE directory
        /\ UNCHANGED <<armed, status>>
Finished == /\ phase = "Exited" /\ UNCHANGED vars
Next == ProofPasses \/ ProofFails \/ Create \/ CreateFails \/ Arm \/ Compile
        \/ Run \/ Fail \/ Pass \/ Exit \/ Finished

ExitCleansBuild == phase = "Exited" => ~directory
=============================================================================
