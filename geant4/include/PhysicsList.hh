// PhysicsList.hh -- EM-only modular physics list.
// PENDING BUILD VERIFICATION (Geant4 11.x).
//
// Default G4EmStandardPhysics_option4 ("EMZ"), the IAEA G4-Med reference for
// medical photons (docs/PHYSICS_LIST_AND_CONVERGENCE.md). Livermore/Penelope
// are selectable for kV studies where atomic shells matter.
// No hadronic physics: pure photon/electron/positron transport.
#ifndef G4BAD_PHYSICSLIST_HH
#define G4BAD_PHYSICSLIST_HH

#include "G4VModularPhysicsList.hh"
#include "globals.hh"

class PhysicsList : public G4VModularPhysicsList {
public:
  explicit PhysicsList(const G4String& emName = "option4",
                       G4double cutMm = 0.1);
};

#endif  // G4BAD_PHYSICSLIST_HH
