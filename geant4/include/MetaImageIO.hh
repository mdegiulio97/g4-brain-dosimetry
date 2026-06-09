// MetaImageIO.hh -- minimal reader for uncompressed LOCAL MetaImage (.mha).
// PENDING BUILD VERIFICATION (Geant4 11.x).
//
// Reads the tissue_labels.mha produced by scripts/build_tissue_labels_mha.py.
// Labels are kept in MetaImage native X-fastest order:
//     index = ix + nx*iy + nx*ny*iz
// which is exactly G4PhantomParameterisation's copy-number layout.
#ifndef G4BAD_METAIMAGEIO_HH
#define G4BAD_METAIMAGEIO_HH

#include <array>
#include <vector>

#include "globals.hh"

struct LabelVolume {
  std::array<G4int, 3> dim = {0, 0, 0};        // nx, ny, nz
  std::array<G4double, 3> spacingMm = {1, 1, 1};
  std::array<G4double, 3> offsetMm = {0, 0, 0};  // LPS pos of voxel (0,0,0)
  std::vector<G4int> labels;                    // size nx*ny*nz, X-fastest

  G4int nx() const { return dim[0]; }
  G4int ny() const { return dim[1]; }
  G4int nz() const { return dim[2]; }
  std::size_t count() const { return labels.size(); }
};

class MetaImageIO {
public:
  // Throws G4Exception on unsupported format. Only uncompressed,
  // ElementDataFile = LOCAL, ElementType in {MET_UCHAR, MET_SHORT, MET_USHORT,
  // MET_INT} is supported.
  static LabelVolume Read(const G4String& path);
};

#endif  // G4BAD_METAIMAGEIO_HH
