cmake_minimum_required(VERSION 3.20)
project(G4BrainAtlasDose LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Geant4 REQUIRED)

add_subdirectory(geant4)
