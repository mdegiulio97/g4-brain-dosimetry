// MaterialMap.hh -- parse material_map.csv into label -> G4Material.
// PENDING BUILD VERIFICATION (Geant4 11.x).
//
// CSV schema (docs/MATERIAL_MAP_SCHEMA.md): label, material_id, density_g_cm3,
// [description]. The CSV density is authoritative and is passed to
// MaterialFactory as a density override, so the phantom uses exactly the frozen
// documented densities regardless of the NIST default.
#ifndef G4BAD_MATERIALMAP_HH
#define G4BAD_MATERIALMAP_HH

#include <map>

#include "globals.hh"

class G4Material;

class MaterialMap {
public:
  static std::map<G4int, G4Material*> Load(const G4String& csvPath);
};

#endif  // G4BAD_MATERIALMAP_HH
