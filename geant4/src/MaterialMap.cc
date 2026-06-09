// MaterialMap.cc -- see header. PENDING BUILD VERIFICATION.
#include "MaterialMap.hh"

#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "G4Material.hh"

#include "MaterialFactory.hh"

namespace {

std::string trim(const std::string& s) {
  const auto b = s.find_first_not_of(" \t\r\n");
  if (b == std::string::npos) return "";
  const auto e = s.find_last_not_of(" \t\r\n");
  return s.substr(b, e - b + 1);
}

std::vector<std::string> splitCsv(const std::string& line) {
  std::vector<std::string> out;
  std::stringstream ss(line);
  std::string cell;
  while (std::getline(ss, cell, ',')) out.push_back(trim(cell));
  return out;
}

}  // namespace

std::map<G4int, G4Material*> MaterialMap::Load(const G4String& csvPath) {
  std::ifstream in(csvPath);
  if (!in) {
    G4Exception("MaterialMap::Load", "BAD_MM_001", FatalException,
                ("cannot open " + csvPath).c_str());
  }

  std::map<G4int, G4Material*> out;
  std::string line;
  bool header = true;
  G4int labelCol = 0, matCol = 1, densCol = 2;

  while (std::getline(in, line)) {
    if (trim(line).empty() || line[0] == '#') continue;
    const auto cells = splitCsv(line);
    if (header) {
      // Resolve columns by name if a header row is present.
      for (std::size_t i = 0; i < cells.size(); ++i) {
        if (cells[i] == "label") labelCol = static_cast<G4int>(i);
        else if (cells[i] == "material_id") matCol = static_cast<G4int>(i);
        else if (cells[i] == "density_g_cm3") densCol = static_cast<G4int>(i);
      }
      header = false;
      continue;
    }
    if (static_cast<G4int>(cells.size()) <= densCol) continue;
    const G4int label = std::stoi(cells[labelCol]);
    const G4String matId = cells[matCol];
    const G4double dens = std::stod(cells[densCol]);
    out[label] = MaterialFactory::Get(matId, dens);
  }

  if (out.empty()) {
    G4Exception("MaterialMap::Load", "BAD_MM_002", FatalException,
                "no material rows parsed");
  }
  G4cout << "[MaterialMap] " << csvPath << " -> " << out.size()
         << " labels" << G4endl;
  return out;
}
