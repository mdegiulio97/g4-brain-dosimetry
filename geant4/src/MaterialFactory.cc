// MaterialFactory.cc -- see MaterialFactory.hh. PENDING BUILD VERIFICATION.
#include "MaterialFactory.hh"

#include <map>
#include <string>
#include <vector>

#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4SystemOfUnits.hh"

namespace {

// Woodard & White (1986) brain-tissue mass compositions, frozen in
// docs/MATERIAL_ASSIGNMENT_METHODOLOGY.md. element symbol -> mass fraction (%).
struct Tissue {
  G4double density_gcm3;
  std::vector<std::pair<G4String, G4double>> massFracPct;
};

const std::map<G4String, Tissue>& brainTissues() {
  static const std::map<G4String, Tissue> t = {
    {"CSF", {1.007, {{"H", 11.1}, {"O", 88.0}, {"Na", 0.5}, {"Cl", 0.4}}}},
    {"GRAY_MATTER", {1.045, {{"H", 10.7}, {"C", 9.5}, {"N", 1.8}, {"O", 76.7},
                             {"Na", 0.2}, {"P", 0.3}, {"S", 0.2}, {"Cl", 0.3},
                             {"K", 0.3}}}},
    {"WHITE_MATTER", {1.041, {{"H", 10.6}, {"C", 19.4}, {"N", 2.5}, {"O", 66.1},
                              {"Na", 0.2}, {"P", 0.4}, {"S", 0.2}, {"Cl", 0.3},
                              {"K", 0.3}}}},
  };
  return t;
}

G4Material* buildBrainTissue(const G4String& id) {
  const auto it = brainTissues().find(id);
  if (it == brainTissues().end()) return nullptr;
  auto* nist = G4NistManager::Instance();
  const Tissue& ts = it->second;
  auto* mat = new G4Material("BAD_" + id, ts.density_gcm3 * (g / cm3),
                             static_cast<G4int>(ts.massFracPct.size()));
  for (const auto& ef : ts.massFracPct) {
    G4Element* el = nist->FindOrBuildElement(ef.first);
    mat->AddElement(el, ef.second / 100.0);
  }
  return mat;
}

// FE_LOADED:<mg_per_g> -> water + dilute elemental iron at the given loading.
G4Material* buildIronLoaded(const G4String& id) {
  const G4String prefix = "FE_LOADED:";
  if (id.rfind(prefix, 0) != 0) return nullptr;
  const G4double mgPerG = std::stod(id.substr(prefix.size()));
  const G4double wFe = mgPerG / 1000.0;  // mg/g -> mass fraction
  auto* nist = G4NistManager::Instance();
  G4Material* water = nist->FindOrBuildMaterial("G4_WATER");
  G4Element* fe = nist->FindOrBuildElement("Fe");
  // Host is ~water; iron is so dilute the density barely moves.
  auto* mat = new G4Material("BAD_FE_LOADED_" + std::to_string(mgPerG),
                             1.00 * (g / cm3), 2);
  mat->AddMaterial(water, 1.0 - wFe);
  mat->AddElement(fe, wFe);
  return mat;
}

}  // namespace

namespace {
// The frozen material_map.brain.csv spells the brain tissues G4_CSF /
// G4_GRAY_MATTER / G4_WHITE_MATTER, but those are NOT NIST materials. Normalise
// them to the custom Woodard&White builders so the CSV works as written.
G4String normalizeId(const G4String& id) {
  if (id == "G4_CSF") return "CSF";
  if (id == "G4_GRAY_MATTER") return "GRAY_MATTER";
  if (id == "G4_WHITE_MATTER") return "WHITE_MATTER";
  return id;
}
}  // namespace

G4Material* MaterialFactory::Get(const G4String& rawId, G4double densityOverrideGcm3) {
  const G4String id = normalizeId(rawId);
  G4Material* base = nullptr;

  if (id.rfind("FE_LOADED:", 0) == 0) {
    base = buildIronLoaded(id);
  } else if (brainTissues().count(id)) {
    base = buildBrainTissue(id);
  } else {
    // NIST id (G4_WATER, G4_AIR, G4_BONE_CORTICAL_ICRP, G4_Fe, ...).
    base = G4NistManager::Instance()->FindOrBuildMaterial(id);
  }

  if (!base) {
    G4Exception("MaterialFactory::Get", "BAD_MAT_001", FatalException,
                ("Unknown material id: " + id).c_str());
    return nullptr;
  }

  if (densityOverrideGcm3 > 0.) {
    // Same composition, different density (e.g. calcification density sweep).
    return new G4Material(base->GetName() + "_rho" + std::to_string(densityOverrideGcm3),
                          densityOverrideGcm3 * (g / cm3), base);
  }
  return base;
}
