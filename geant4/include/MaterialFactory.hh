// MaterialFactory.hh -- map a string id to a G4Material.
// PENDING BUILD VERIFICATION (Geant4 11.x).
//
// Supported ids:
//   * any NIST id, e.g. G4_WATER, G4_AIR, G4_BONE_CORTICAL_ICRP, G4_Fe,
//     G4_BRAIN_ICRP, G4_TISSUE_SOFT_ICRP  -> built via G4NistManager
//   * custom Woodard&White brain tissues not in NIST:
//       CSF, GRAY_MATTER, WHITE_MATTER     -> built from frozen compositions
//       (docs/MATERIAL_ASSIGNMENT_METHODOLOGY.md)
//   * FE_LOADED:<mg_per_g>  -> water host with a dilute elemental-iron fraction,
//     to model pathological brain iron at a realistic concentration.
#ifndef G4BAD_MATERIALFACTORY_HH
#define G4BAD_MATERIALFACTORY_HH

#include "globals.hh"

class G4Material;

class MaterialFactory {
public:
  // densityOverride > 0 g/cm3 builds a copy at that density (used to sweep
  // calcification density); <= 0 keeps the material's native density.
  static G4Material* Get(const G4String& id, G4double densityOverrideGcm3 = -1.);
};

#endif  // G4BAD_MATERIALFACTORY_HH
