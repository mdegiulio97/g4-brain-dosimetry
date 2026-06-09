# G4BrainAtlasDose -- Geant4 build/run environment.
# PENDING BUILD VERIFICATION: this Dockerfile has NOT been built on the authoring
# machine (no Docker present). It uses conda-forge Geant4 to avoid a multi-hour
# from-source build and to pin a reproducible toolkit + datasets.
#
# Build:  docker build -t g4brainatlasdose -f docker/Dockerfile .
# Run  :  docker run --rm -it -v "$PWD":/work -w /work g4brainatlasdose \
#             micromamba run -n base bash -lc \
#             "cmake -S . -B build && cmake --build build -j && \
#              G4BAD_RUNCONFIG=geant4/run.config.example \
#              ./build/geant4/g4brainatlasdose geant4/macros/benchmark_water.mac"
FROM mambaorg/micromamba:1.5.8

# Toolkit + build tools. Pin Geant4 major.minor for reproducibility; bump
# deliberately. conda-forge geant4 pulls the G4 datasets and sets data env vars
# through its activation scripts (hence `micromamba run -n base`).
RUN micromamba install -y -n base -c conda-forge \
        "geant4=11.2" \
        cmake \
        make \
        "cxx-compiler" \
    && micromamba clean --all --yes

# Headless EM-only runs need no GUI; vis libs come with the conda package.
ENV G4BAD_RUNCONFIG=/work/geant4/run.config.example

WORKDIR /work
# Source code is bind-mounted at run time (-v "$PWD":/work) so edits don't need
# a rebuild of the image.
