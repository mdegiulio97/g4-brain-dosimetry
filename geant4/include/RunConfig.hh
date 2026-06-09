// RunConfig.hh -- minimal key=value run configuration for G4BrainAtlasDose.
//
// PENDING BUILD VERIFICATION: this code targets Geant4 11.x and has NOT been
// compiled on the authoring machine (no Geant4/compiler present). Build inside
// the provided Docker image before trusting it.
//
// The geometry is intentionally minimal:
// a water box with one optional rectangular insert whose
// material/size/depth are set here. Beam and scoring mesh live in the macros
// (GPS + command-based scoring), so the C++ surface stays small and leans on
// Geant4's already-tested machinery.
#ifndef G4BAD_RUNCONFIG_HH
#define G4BAD_RUNCONFIG_HH

#include "globals.hh"
#include "G4ThreeVector.hh"

class RunConfig {
public:
  // geometry: "water_box" | "water_with_insert" | "voxel_phantom"
  G4String geometry = "water_box";

  // --- voxel phantom (only used when geometry == "voxel_phantom") ---
  // Paths to the frozen C++/Python contract inputs (docs/CPP_PYTHON_INTERFACE.md).
  G4String tissueLabelsMha = "data/derived/tissue_labels.mha";
  G4String materialMapCsv = "configs/examples/material_map.brain.csv";

  // Full phantom side lengths (cm). Default 30x30x30 water cube.
  G4ThreeVector phantomSizeCm = G4ThreeVector(30., 30., 30.);

  // EM physics: "option4" (default), "option3", "livermore", "penelope".
  // Livermore/Penelope are recommended at kV energies.
  G4String emPhysics = "option4";

  // Range production cut (mm). 0.1 mm ~ half of a 1 mm voxel (AAPM TG-105).
  G4double productionCutMm = 0.1;

  // --- insert (only used when geometry == "water_with_insert") ---
  // Material id understood by MaterialFactory, e.g. G4_BONE_CORTICAL_ICRP,
  // G4_AIR, G4_Fe, G4_WATER, or FE_LOADED:<mg_per_g>.
  G4String insertMaterial = "G4_BONE_CORTICAL_ICRP";
  G4ThreeVector insertSizeCm = G4ThreeVector(4., 4., 2.);
  // Depth (cm) of the insert centre from the beam-entrance face, along +z.
  G4double insertDepthCm = 10.;
  // Optional density override (g/cm3); <=0 keeps the material default.
  G4double insertDensityOverride = -1.;

  // Load from the file pointed to by env var G4BAD_RUNCONFIG; missing file or
  // missing keys keep the defaults above. Format: one "key = value" per line,
  // '#' starts a comment. Tolerant by design.
  static RunConfig Load();

  void Print() const;
};

#endif  // G4BAD_RUNCONFIG_HH
