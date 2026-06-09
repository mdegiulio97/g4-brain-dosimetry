// MetaImageIO.cc -- see header. PENDING BUILD VERIFICATION.
#include "MetaImageIO.hh"

#include <cstdint>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string trim(const std::string& s) {
  const auto b = s.find_first_not_of(" \t\r\n");
  if (b == std::string::npos) return "";
  const auto e = s.find_last_not_of(" \t\r\n");
  return s.substr(b, e - b + 1);
}

template <typename T>
void appendCast(const char* base, std::size_t n, std::vector<G4int>& out) {
  const T* p = reinterpret_cast<const T*>(base);
  out.resize(n);
  for (std::size_t i = 0; i < n; ++i) out[i] = static_cast<G4int>(p[i]);
}

}  // namespace

LabelVolume MetaImageIO::Read(const G4String& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    G4Exception("MetaImageIO::Read", "BAD_MHA_001", FatalException,
                ("cannot open " + path).c_str());
  }
  std::vector<char> all((std::istreambuf_iterator<char>(in)),
                        std::istreambuf_iterator<char>());

  const std::string marker = "ElementDataFile = LOCAL\n";
  const std::string blob(all.begin(), all.end());
  const auto pos = blob.find(marker);
  if (pos == std::string::npos) {
    G4Exception("MetaImageIO::Read", "BAD_MHA_002", FatalException,
                "only uncompressed ElementDataFile = LOCAL is supported");
  }
  const std::string header = blob.substr(0, pos + marker.size());
  const char* dataStart = all.data() + pos + marker.size();
  const std::size_t dataBytes = all.size() - (pos + marker.size());

  std::map<std::string, std::string> kv;
  std::istringstream hs(header);
  std::string line;
  while (std::getline(hs, line)) {
    const auto eq = line.find('=');
    if (eq == std::string::npos) continue;
    kv[trim(line.substr(0, eq))] = trim(line.substr(eq + 1));
  }

  LabelVolume vol;
  {
    std::istringstream ds(kv.at("DimSize"));
    ds >> vol.dim[0] >> vol.dim[1] >> vol.dim[2];
  }
  if (kv.count("ElementSpacing")) {
    std::istringstream ss(kv.at("ElementSpacing"));
    ss >> vol.spacingMm[0] >> vol.spacingMm[1] >> vol.spacingMm[2];
  }
  if (kv.count("Offset")) {
    std::istringstream os(kv.at("Offset"));
    os >> vol.offsetMm[0] >> vol.offsetMm[1] >> vol.offsetMm[2];
  }

  const std::size_t n = static_cast<std::size_t>(vol.dim[0]) * vol.dim[1] * vol.dim[2];
  const std::string et = kv.at("ElementType");
  std::size_t itemSize = 0;
  if (et == "MET_UCHAR") itemSize = 1;
  else if (et == "MET_SHORT" || et == "MET_USHORT") itemSize = 2;
  else if (et == "MET_INT" || et == "MET_UINT") itemSize = 4;
  else
    G4Exception("MetaImageIO::Read", "BAD_MHA_003", FatalException,
                ("unsupported ElementType " + et).c_str());

  if (dataBytes < n * itemSize) {
    G4Exception("MetaImageIO::Read", "BAD_MHA_004", FatalException,
                "binary payload smaller than DimSize implies");
  }
  // NB: assumes little-endian host and BinaryDataByteOrderMSB = False (default
  // from our writer). MSB handling is a TODO if a big-endian source appears.
  if (et == "MET_UCHAR") appendCast<std::uint8_t>(dataStart, n, vol.labels);
  else if (et == "MET_SHORT") appendCast<std::int16_t>(dataStart, n, vol.labels);
  else if (et == "MET_USHORT") appendCast<std::uint16_t>(dataStart, n, vol.labels);
  else appendCast<std::int32_t>(dataStart, n, vol.labels);

  G4cout << "[MetaImageIO] " << path << " dim=" << vol.dim[0] << "x" << vol.dim[1]
         << "x" << vol.dim[2] << " spacing(mm)=" << vol.spacingMm[0] << ","
         << vol.spacingMm[1] << "," << vol.spacingMm[2] << G4endl;
  return vol;
}
