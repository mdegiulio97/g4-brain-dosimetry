// ActionInitialization.hh -- registers the (GPS-based) primary generator.
// PENDING BUILD VERIFICATION (Geant4 11.x).
#ifndef G4BAD_ACTIONINITIALIZATION_HH
#define G4BAD_ACTIONINITIALIZATION_HH

#include "G4VUserActionInitialization.hh"

class ActionInitialization : public G4VUserActionInitialization {
public:
  void Build() const override;
  // Master thread in MT mode has no primary generator.
  void BuildForMaster() const override {}
};

#endif  // G4BAD_ACTIONINITIALIZATION_HH
