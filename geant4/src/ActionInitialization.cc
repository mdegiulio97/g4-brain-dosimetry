// ActionInitialization.cc -- see header. PENDING BUILD VERIFICATION.
#include "ActionInitialization.hh"

#include "PrimaryGeneratorAction.hh"

void ActionInitialization::Build() const {
  SetUserAction(new PrimaryGeneratorAction());
  // Dose is collected by command-based scoring (G4ScoringManager), so no custom
  // RunAction/SteppingAction is needed at this stage.
}
