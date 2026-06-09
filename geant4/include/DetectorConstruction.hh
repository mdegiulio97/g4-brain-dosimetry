// DetectorConstruction.hh -- water phantom with one optional insert.
// PENDING BUILD VERIFICATION (Geant4 11.x).
#ifndef G4BAD_DETECTORCONSTRUCTION_HH
#define G4BAD_DETECTORCONSTRUCTION_HH

#include "G4VUserDetectorConstruction.hh"
#include "RunConfig.hh"

class G4VPhysicalVolume;
class G4LogicalVolume;
struct LabelVolume;

class DetectorConstruction : public G4VUserDetectorConstruction {
public:
  explicit DetectorConstruction(const RunConfig& cfg) : fCfg(cfg) {}
  G4VPhysicalVolume* Construct() override;

private:
  // Water box (+ optional insert): the benchmark geometry.
  void BuildWaterPhantom(G4LogicalVolume* worldLV) const;
  // Voxelised phantom from tissue_labels.mha + material_map.csv (Stage C2).
  void BuildVoxelPhantom(G4LogicalVolume* worldLV, const LabelVolume& vol) const;

  RunConfig fCfg;
};

#endif  // G4BAD_DETECTORCONSTRUCTION_HH
