// PhysicsList.cc -- see header. PENDING BUILD VERIFICATION.
#include "PhysicsList.hh"

#include "G4EmLivermorePhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4EmStandardPhysics_option3.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4SystemOfUnits.hh"

PhysicsList::PhysicsList(const G4String& emName, G4double cutMm)
    : G4VModularPhysicsList() {
  SetVerboseLevel(1);

  if (emName == "option4") {
    RegisterPhysics(new G4EmStandardPhysics_option4());
  } else if (emName == "option3") {
    RegisterPhysics(new G4EmStandardPhysics_option3());
  } else if (emName == "livermore") {
    RegisterPhysics(new G4EmLivermorePhysics());
  } else if (emName == "penelope") {
    RegisterPhysics(new G4EmPenelopePhysics());
  } else {
    G4Exception("PhysicsList", "BAD_PL_001", JustWarning,
                ("Unknown em physics '" + emName + "', using option4").c_str());
    RegisterPhysics(new G4EmStandardPhysics_option4());
  }

  // Range cut applied everywhere; ~half of a 1 mm voxel (AAPM TG-105).
  SetDefaultCutValue(cutMm * mm);
}
