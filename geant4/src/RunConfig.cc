// RunConfig.cc -- see RunConfig.hh. PENDING BUILD VERIFICATION (Geant4 11.x).
#include "RunConfig.hh"

#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>

#include "G4SystemOfUnits.hh"

namespace {

std::string trim(const std::string& s) {
  const auto b = s.find_first_not_of(" \t\r\n");
  if (b == std::string::npos) return "";
  const auto e = s.find_last_not_of(" \t\r\n");
  return s.substr(b, e - b + 1);
}

// Parse up to three whitespace-separated doubles into a G4ThreeVector,
// keeping the previous value for any component not provided.
G4ThreeVector parseVec(const std::string& v, const G4ThreeVector& fallback) {
  std::istringstream is(v);
  double x = fallback.x(), y = fallback.y(), z = fallback.z();
  is >> x >> y >> z;
  return G4ThreeVector(x, y, z);
}

}  // namespace

RunConfig RunConfig::Load() {
  RunConfig cfg;
  const char* path = std::getenv("G4BAD_RUNCONFIG");
  if (!path || std::string(path).empty()) return cfg;

  std::ifstream in(path);
  if (!in) {
    G4cout << "[RunConfig] WARNING: cannot open " << path
           << ", using defaults." << G4endl;
    return cfg;
  }

  std::string line;
  while (std::getline(in, line)) {
    const auto hash = line.find('#');
    if (hash != std::string::npos) line = line.substr(0, hash);
    const auto eq = line.find('=');
    if (eq == std::string::npos) continue;
    const std::string key = trim(line.substr(0, eq));
    const std::string val = trim(line.substr(eq + 1));
    if (key.empty() || val.empty()) continue;

    if (key == "geometry") cfg.geometry = val;
    else if (key == "tissue_labels_mha") cfg.tissueLabelsMha = val;
    else if (key == "material_map_csv") cfg.materialMapCsv = val;
    else if (key == "phantom_size_cm") cfg.phantomSizeCm = parseVec(val, cfg.phantomSizeCm);
    else if (key == "world_half_z_cm") cfg.worldHalfZcm = std::stod(val);
    else if (key == "em_physics") cfg.emPhysics = val;
    else if (key == "production_cut_mm") cfg.productionCutMm = std::stod(val);
    else if (key == "insert_material") cfg.insertMaterial = val;
    else if (key == "insert_size_cm") cfg.insertSizeCm = parseVec(val, cfg.insertSizeCm);
    else if (key == "insert_depth_cm") cfg.insertDepthCm = std::stod(val);
    else if (key == "insert_density_g_cm3") cfg.insertDensityOverride = std::stod(val);
    else
      G4cout << "[RunConfig] ignoring unknown key '" << key << "'" << G4endl;
  }
  return cfg;
}

void RunConfig::Print() const {
  G4cout << "[RunConfig] geometry=" << geometry
         << " phantom(cm)=" << phantomSizeCm
         << " em=" << emPhysics
         << " cut(mm)=" << productionCutMm << G4endl;
  if (geometry == "water_with_insert") {
    G4cout << "[RunConfig] insert mat=" << insertMaterial
           << " size(cm)=" << insertSizeCm
           << " depth(cm)=" << insertDepthCm
           << " rhoOverride=" << insertDensityOverride << G4endl;
  } else if (geometry == "voxel_phantom") {
    G4cout << "[RunConfig] labels=" << tissueLabelsMha
           << " materials=" << materialMapCsv << G4endl;
  }
}
