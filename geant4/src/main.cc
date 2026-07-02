// main.cc -- G4BrainAtlasDose Monte Carlo entry point (headless / batch).
// PENDING BUILD VERIFICATION (Geant4 11.x): built via scripts/setup_geant4_conda.sh.
//
// Batch only: always runs a macro, no interactive UI/visualization (so the build
// needs no X11/Qt/OpenGL). Usage:
//   g4brainatlasdose <macro>
//
// Geometry/material come from the file named by env var G4BAD_RUNCONFIG
// (see geant4/run.config.example). Beam and scoring mesh come from the macro.
#include <cstdlib>

#include "G4RunManagerFactory.hh"
#include "G4ScoringManager.hh"
#include "G4UImanager.hh"
#include "Randomize.hh"

#include "ActionInitialization.hh"
#include "DetectorConstruction.hh"
#include "PhysicsList.hh"
#include "RunConfig.hh"

int main(int argc, char** argv) {
  if (argc < 2) {
    G4cerr << "usage: " << argv[0] << " <macro>" << G4endl;
    return 1;
  }

  // Seed the RNG from G4BAD_SEED (nonzero). Without this every run uses the same
  // default seed, so "independent" runs are identical -- which breaks statistical
  // uncertainty propagation on ratios and any batch-variance estimate. Default
  // (unset/0) keeps the reproducible fixed seed.
  if (const char* seedEnv = std::getenv("G4BAD_SEED")) {
    const long seed = std::atol(seedEnv);
    if (seed != 0) {
      CLHEP::HepRandom::setTheSeed(seed);
      G4cout << "[main] RNG seed = " << seed << G4endl;
    }
  }

  const RunConfig cfg = RunConfig::Load();

  auto* runManager =
      G4RunManagerFactory::CreateRunManager(G4RunManagerType::Default);

  // Activate command-based scoring (/score/... commands in the macro).
  G4ScoringManager::GetScoringManager();

  runManager->SetUserInitialization(new DetectorConstruction(cfg));
  runManager->SetUserInitialization(
      new PhysicsList(cfg.emPhysics, cfg.productionCutMm));
  runManager->SetUserInitialization(new ActionInitialization());

  auto* uiManager = G4UImanager::GetUIpointer();
  uiManager->ApplyCommand(G4String("/control/execute ") + argv[1]);

  delete runManager;
  return 0;
}
