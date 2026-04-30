cmake_minimum_required(VERSION 3.20)

find_package(Geant4 REQUIRED)

include(${Geant4_USE_FILE})
include_directories(${PROJECT_SOURCE_DIR}/geant4/include)

file(GLOB sources ${PROJECT_SOURCE_DIR}/geant4/src/*.cc)
file(GLOB headers ${PROJECT_SOURCE_DIR}/geant4/include/*.hh)

add_executable(g4brainatlasdose ${sources} ${headers})
target_link_libraries(g4brainatlasdose ${Geant4_LIBRARIES})
