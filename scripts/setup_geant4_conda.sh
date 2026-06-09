#!/usr/bin/env bash
# Set up Geant4 and build G4BrainAtlasDose WITHOUT Docker.
# Works in WSL Ubuntu or any Linux shell. No root, no from-source build:
# it bootstraps micromamba (a single static binary) and installs the
# conda-forge Geant4 11.2 toolkit + datasets + a C++ compiler into a local env.
#
# Usage (from the repo root, inside WSL):
#   bash scripts/setup_geant4_conda.sh
#   bash scripts/setup_geant4_conda.sh --benchmark   # also run the water PDD
#
# PENDING VERIFICATION: not executed on the authoring machine. Report the first
# compile error and we fix it.
set -euo pipefail

# WSL interop can leak a Windows HOME (e.g. "C:UsersName") into the shell, which
# breaks micromamba's root prefix. Reset it to a sane Linux home if so.
case "${HOME:-}" in
  /*) : ;;                                  # already a Linux path
  *) HOME="$(getent passwd "$(id -un)" | cut -d: -f6)"; export HOME ;;
esac
[ -n "${HOME:-}" ] && [ -d "$HOME" ] || { HOME="/root"; export HOME; }

ENV_NAME="g4bad"
G4_VERSION="11.2"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 0) Warn if building on the slow Windows mount; a native-WSL copy is faster and
#    avoids CRLF/permission quirks. Not fatal.
case "$REPO_ROOT" in
  /mnt/*) echo "NOTE: building under $REPO_ROOT (Windows mount). It works but is" \
               "slow; for repeated builds copy the repo into the WSL home fs." ;;
esac

# 1) micromamba (no install, just a binary in ~/.local/bin)
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-$HOME/micromamba}"
MM="$HOME/.local/bin/micromamba"
if ! command -v micromamba >/dev/null 2>&1 && [ ! -x "$MM" ]; then
  echo ">> downloading micromamba..."
  mkdir -p "$HOME/.local/bin"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest \
    | tar -xvj -C "$HOME/.local" bin/micromamba
fi
command -v micromamba >/dev/null 2>&1 || export PATH="$HOME/.local/bin:$PATH"
# Geant4's conda activation scripts reference variables that are unset until they
# run (e.g. G4ABLADATA), which trips `set -u`. Disable nounset around the
# micromamba hook + activate, restore it for the build.
set +u
eval "$(micromamba shell hook -s bash)"

# 2) Geant4 env (idempotent). zlib/expat dev headers are pulled in explicitly so
# CMake does not fall back to the older WSL system copies.
if ! micromamba env list | grep -qw "$ENV_NAME"; then
  echo ">> creating env '${ENV_NAME}' with Geant4 ${G4_VERSION}..."
  micromamba create -y -n "$ENV_NAME" -c conda-forge \
    "geant4=${G4_VERSION}" cmake make ninja cxx-compiler zlib expat
fi
# Ensure dev headers exist even if the env predates this line.
micromamba install -y -n "$ENV_NAME" -c conda-forge zlib expat >/dev/null
micromamba activate "$ENV_NAME"
set -u

# 3) build
# Force CMake to prefer the conda env's libraries over the WSL system ones
# (otherwise it finds Ubuntu's older expat, which Geant4 rejects).
echo ">> configuring + building..."
rm -rf build
# The conda toolchain re-roots find_* into the cos7 sysroot with NO_DEFAULT_PATH,
# so CMake's FindX11/FindOpenGL miss Geant4's vis deps, which are split: X11
# headers/libs in the host prefix, GL headers/libs in the sysroot. Pre-seed the
# cache variables (like expat/zlib) so the searches are bypassed entirely.
SR="$CONDA_PREFIX/x86_64-conda-linux-gnu/sysroot"
GLU_LIB="$CONDA_PREFIX/lib/libGLU.so"; [ -e "$GLU_LIB" ] || GLU_LIB="$SR/usr/lib64/libGLU.so"
cmake -S . -B build -G Ninja \
  -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DCMAKE_INCLUDE_PATH="$CONDA_PREFIX/include" \
  -DCMAKE_LIBRARY_PATH="$CONDA_PREFIX/lib" \
  -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH \
  -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH \
  -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=BOTH \
  -DEXPAT_INCLUDE_DIR="$CONDA_PREFIX/include" \
  -DEXPAT_LIBRARY="$CONDA_PREFIX/lib/libexpat.so" \
  -DZLIB_ROOT="$CONDA_PREFIX" \
  -DZLIB_INCLUDE_DIR="$CONDA_PREFIX/include" \
  -DZLIB_LIBRARY="$CONDA_PREFIX/lib/libz.so" \
  -DX11_X11_INCLUDE_PATH="$CONDA_PREFIX/include" \
  -DX11_X11_LIB="$CONDA_PREFIX/lib/libX11.so" \
  -DX11_FOUND=TRUE \
  -DOPENGL_INCLUDE_DIR="$SR/usr/include" \
  -DOPENGL_gl_LIBRARY="$SR/usr/lib64/libGL.so" \
  -DOPENGL_glu_LIBRARY="$GLU_LIB"
cmake --build build -j

BIN="$REPO_ROOT/build/geant4/g4brainatlasdose"
echo ">> build complete: $BIN"

# 4) optional smoke / benchmark
if [ "${1:-}" = "--benchmark" ]; then
  echo ">> running water PDD benchmark..."
  mkdir -p reports/benchmark_mc
  # PURE WATER config: run.config.example declares water_with_insert (bone at 10 cm)
  # which would corrupt the central-axis PDD. Use the dedicated benchmark config.
  G4BAD_RUNCONFIG="geant4/run.config.benchmark" "$BIN" geant4/macros/benchmark_water.mac
  python3 scripts/analyze_pdd.py --mc-dump reports/benchmark_mc/pdd_6MeV.txt || true
fi

cat <<EOF

Done. To use the binary later, in WSL:
  eval "\$(micromamba shell hook -s bash)" && micromamba activate ${ENV_NAME}
  G4BAD_RUNCONFIG=geant4/run.config.example \\
    ${BIN} geant4/macros/benchmark_water.mac
EOF
