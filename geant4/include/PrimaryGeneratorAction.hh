// PrimaryGeneratorAction.hh -- thin wrapper over G4GeneralParticleSource so the
// beam (particle, energy, field, direction) is configured entirely from macros.
// PENDING BUILD VERIFICATION (Geant4 11.x).
#ifndef G4BAD_PRIMARYGENERATORACTION_HH
#define G4BAD_PRIMARYGENERATORACTION_HH

#include "G4VUserPrimaryGeneratorAction.hh"

class G4GeneralParticleSource;
class G4Event;

class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
public:
  PrimaryGeneratorAction();
  ~PrimaryGeneratorAction() override;
  void GeneratePrimaries(G4Event* event) override;

private:
  G4GeneralParticleSource* fGPS = nullptr;
};

#endif  // G4BAD_PRIMARYGENERATORACTION_HH
