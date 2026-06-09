// DetectorConstruction.cc -- see header. PENDING BUILD VERIFICATION.
//
// Three geometries (beam travels +z, enters the -z face):
//   water_box          : homogeneous 30^3 cm water cube
//   water_with_insert  : water cube + one rectangular insert (Stage-1 study)
//   voxel_phantom      : regular voxel grid from tissue_labels.mha +
//                        material_map.csv (Stage C2), via G4PhantomParameterisation
//
// The command-based scoring mesh (defined in the macro) overlays whichever
// geometry is built, so dose is scored per mesh voxel regardless.
#include "DetectorConstruction.hh"

#include <map>
#include <vector>

#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVParameterised.hh"
#include "G4PVPlacement.hh"
#include "G4PhantomParameterisation.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4VisAttributes.hh"

#include "MaterialFactory.hh"
#include "MaterialMap.hh"
#include "MetaImageIO.hh"

G4VPhysicalVolume* DetectorConstruction::Construct() {
  fCfg.Print();
  auto* nist = G4NistManager::Instance();
  G4Material* air = nist->FindOrBuildMaterial("G4_AIR");
  const G4double margin = 20. * cm;

  // World extent depends on geometry.
  G4double hx, hy, hz;
  LabelVolume vol;
  const G4bool isVoxel = (fCfg.geometry == "voxel_phantom");
  if (isVoxel) {
    vol = MetaImageIO::Read(fCfg.tissueLabelsMha);
    hx = 0.5 * vol.nx() * vol.spacingMm[0] * mm;
    hy = 0.5 * vol.ny() * vol.spacingMm[1] * mm;
    hz = 0.5 * vol.nz() * vol.spacingMm[2] * mm;
  } else {
    hx = 0.5 * fCfg.phantomSizeCm.x() * cm;
    hy = 0.5 * fCfg.phantomSizeCm.y() * cm;
    hz = 0.5 * fCfg.phantomSizeCm.z() * cm;
  }

  auto* worldBox = new G4Box("world", hx + margin, hy + margin, hz + margin);
  auto* worldLV = new G4LogicalVolume(worldBox, air, "world");
  worldLV->SetVisAttributes(G4VisAttributes::GetInvisible());
  auto* worldPV = new G4PVPlacement(nullptr, {}, worldLV, "world",
                                    nullptr, false, 0, true);

  if (isVoxel)
    BuildVoxelPhantom(worldLV, vol);
  else
    BuildWaterPhantom(worldLV);

  return worldPV;
}

void DetectorConstruction::BuildWaterPhantom(G4LogicalVolume* worldLV) const {
  auto* nist = G4NistManager::Instance();
  const G4double Lx = fCfg.phantomSizeCm.x() * cm;
  const G4double Ly = fCfg.phantomSizeCm.y() * cm;
  const G4double Lz = fCfg.phantomSizeCm.z() * cm;

  G4Material* water = nist->FindOrBuildMaterial("G4_WATER");
  auto* phantomBox = new G4Box("phantom", 0.5 * Lx, 0.5 * Ly, 0.5 * Lz);
  auto* phantomLV = new G4LogicalVolume(phantomBox, water, "phantom");
  new G4PVPlacement(nullptr, {}, phantomLV, "phantom", worldLV, false, 0, true);

  if (fCfg.geometry == "water_with_insert") {
    G4Material* insMat =
        MaterialFactory::Get(fCfg.insertMaterial, fCfg.insertDensityOverride);
    const G4double ix = fCfg.insertSizeCm.x() * cm;
    const G4double iy = fCfg.insertSizeCm.y() * cm;
    const G4double iz = fCfg.insertSizeCm.z() * cm;
    const G4double zc = -0.5 * Lz + fCfg.insertDepthCm * cm;
    auto* insBox = new G4Box("insert", 0.5 * ix, 0.5 * iy, 0.5 * iz);
    auto* insLV = new G4LogicalVolume(insBox, insMat, "insert");
    insLV->SetVisAttributes(new G4VisAttributes(G4Colour(1., 0.3, 0.3)));
    new G4PVPlacement(nullptr, G4ThreeVector(0., 0., zc), insLV, "insert",
                      phantomLV, false, 0, true);
    G4cout << "[Detector] insert '" << insMat->GetName() << "' rho="
           << insMat->GetDensity() / (g / cm3) << " g/cm3 at z=" << zc / cm
           << " cm" << G4endl;
  }
}

void DetectorConstruction::BuildVoxelPhantom(G4LogicalVolume* worldLV,
                                             const LabelVolume& vol) const {
  // label -> G4Material
  const std::map<G4int, G4Material*> byLabel = MaterialMap::Load(fCfg.materialMapCsv);

  // Compact, de-duplicated material table + label -> table-index.
  std::vector<G4Material*> materials;
  std::map<G4Material*, std::size_t> matToIdx;
  std::map<G4int, std::size_t> labelToIdx;
  for (const auto& kv : byLabel) {
    G4Material* m = kv.second;
    auto it = matToIdx.find(m);
    if (it == matToIdx.end()) {
      matToIdx[m] = materials.size();
      labelToIdx[kv.first] = materials.size();
      materials.push_back(m);
    } else {
      labelToIdx[kv.first] = it->second;
    }
  }

  const G4int nx = vol.nx(), ny = vol.ny(), nz = vol.nz();
  const G4double hvx = 0.5 * vol.spacingMm[0] * mm;
  const G4double hvy = 0.5 * vol.spacingMm[1] * mm;
  const G4double hvz = 0.5 * vol.spacingMm[2] * mm;

  // Per-voxel material index, in X-fastest copy-number order (matches the .mha).
  auto* matIDs = new size_t[vol.count()];
  G4int unmapped = 0;
  for (std::size_t i = 0; i < vol.count(); ++i) {
    const auto it = labelToIdx.find(vol.labels[i]);
    if (it == labelToIdx.end()) {
      // Should never happen: build_tissue_labels_mha.py validates the labels.
      matIDs[i] = labelToIdx.count(0) ? labelToIdx.at(0) : 0;
      ++unmapped;
    } else {
      matIDs[i] = it->second;
    }
  }
  if (unmapped)
    G4cout << "[Detector] WARNING: " << unmapped
           << " voxels had labels absent from material_map.csv" << G4endl;

  // Container box holding the whole grid, centred at world origin.
  G4Material* containerMat = materials.empty()
      ? G4NistManager::Instance()->FindOrBuildMaterial("G4_AIR")
      : materials.front();
  auto* containerBox =
      new G4Box("phantomContainer", nx * hvx, ny * hvy, nz * hvz);
  auto* containerLV = new G4LogicalVolume(containerBox, containerMat,
                                          "phantomContainer");
  containerLV->SetVisAttributes(G4VisAttributes::GetInvisible());
  auto* containerPV = new G4PVPlacement(nullptr, {}, containerLV,
                                        "phantomContainer", worldLV, false, 0, true);

  // One voxel logical volume, parameterised over the grid.
  auto* voxelBox = new G4Box("voxel", hvx, hvy, hvz);
  auto* voxelLV = new G4LogicalVolume(voxelBox, containerMat, "voxel");

  auto* param = new G4PhantomParameterisation();
  param->SetVoxelDimensions(hvx, hvy, hvz);
  param->SetNoVoxels(nx, ny, nz);
  param->SetMaterials(materials);
  param->SetMaterialIndices(matIDs);
  param->BuildContainerSolid(containerPV);
  param->SetSkipEqualMaterials(false);

  auto* phantom = new G4PVParameterised("phantom", voxelLV, containerLV,
                                        kXAxis, nx * ny * nz, param);
  phantom->SetRegularStructureId(1);  // enable regular (fast) navigation

  G4cout << "[Detector] voxel phantom " << nx << "x" << ny << "x" << nz
         << " voxels, " << materials.size() << " distinct materials" << G4endl;
}
