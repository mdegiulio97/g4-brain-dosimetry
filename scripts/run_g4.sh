#!/usr/bin/env bash
# Activate the conda Geant4 env and run the g4brainatlasdose binary on a macro.
# Usage (inside WSL):
#   G4BAD_ENERGY="6 MeV" G4BAD_NPRIM=20000 G4BAD_OUT=reports/smoke/dose.txt \
#     bash scripts/run_g4.sh geant4/macros/run_score.mac
# G4BAD_RUNCONFIG defaults to geant4/run.config.example.
set -uo pipefail

# WSL can leak a Windows HOME; reset to a Linux home.
case "${HOME:-}" in
  /*) : ;;
  *) HOME="$(getent passwd "$(id -un)" | cut -d: -f6)"; export HOME ;;
esac
[ -n "${HOME:-}" ] && [ -d "$HOME" ] || { HOME="/root"; export HOME; }

ENV_NAME="g4bad"
export PATH="$HOME/.local/bin:$PATH"

# Geant4 activation scripts reference unset vars -> disable nounset around them.
set +u
eval "$(micromamba shell hook -s bash)"
micromamba activate "$ENV_NAME"
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

BIN="$REPO/build/geant4/g4brainatlasdose"
[ -x "$BIN" ] || { echo "binary not built: $BIN (run scripts/setup_geant4_conda.sh)"; exit 1; }

export G4BAD_RUNCONFIG="${G4BAD_RUNCONFIG:-$REPO/geant4/run.config.example}"
# command-based scoring won't create the dump's directory; do it here.
[ -n "${G4BAD_OUT:-}" ] && mkdir -p "$(dirname "$G4BAD_OUT")"

echo ">> running: $BIN $* (config=$G4BAD_RUNCONFIG)"
exec "$BIN" "$@"
