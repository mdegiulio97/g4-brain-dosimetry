# Geant4 core for G4BrainAtlasDose.
# PENDING BUILD VERIFICATION: not compiled on the authoring machine.
#
# Explicit source list (the previous file(GLOB) on empty dirs broke the build
# and is a CMake anti-pattern: new files are not picked up without re-running
# cmake). Add new .cc files here.

# Core Geant4 only: this is a headless batch MC (run macros, dump dose). No UI/vis
# components, so the build does not pull X11/Qt/OpenGL -- which keeps WSL/headless
# setups simple. Re-add `ui_all vis_all` only if interactive visualization is wanted.
find_package(Geant4 REQUIRED)
include(${Geant4_USE_FILE})

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

set(G4BAD_SOURCES
  src/main.cc
  src/RunConfig.cc
  src/MaterialFactory.cc
  src/MaterialMap.cc
  src/MetaImageIO.cc
  src/DetectorConstruction.cc
  src/PhysicsList.cc
  src/PrimaryGeneratorAction.cc
  src/ActionInitialization.cc
)

set(G4BAD_HEADERS
  include/RunConfig.hh
  include/MaterialFactory.hh
  include/MaterialMap.hh
  include/MetaImageIO.hh
  include/DetectorConstruction.hh
  include/PhysicsList.hh
  include/PrimaryGeneratorAction.hh
  include/ActionInitialization.hh
)

add_executable(g4brainatlasdose ${G4BAD_SOURCES} ${G4BAD_HEADERS})
target_link_libraries(g4brainatlasdose ${Geant4_LIBRARIES})

# Copy macros next to the binary for convenience.
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/macros
     DESTINATION ${CMAKE_BINARY_DIR}/geant4)
