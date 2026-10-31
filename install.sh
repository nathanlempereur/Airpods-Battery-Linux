#!/usr/bin/env bash
# Installe / désinstalle AirPods Battery pour l'utilisateur courant (sans sudo).
#   ./install.sh              installe + entrée dans le menu d'applications
#   ./install.sh --autostart  idem + lancement au démarrage de session (icône seule)
#   ./install.sh --uninstall  supprime tout
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin/airpods-battery"
APPS="$HOME/.local/share/applications/airpods-battery.desktop"
AUTO="$HOME/.config/autostart/airpods-battery.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$BIN" "$APPS" "$AUTO"
    echo "Désinstallé."
    exit 0
fi

install -Dm755 "$SRC/airpods-battery.py" "$BIN"

mkdir -p "$(dirname "$APPS")"
cat > "$APPS" << EOF
[Desktop Entry]
Type=Application
Name=AirPods Batterie
Comment=Niveau de batterie des AirPods
Exec=$BIN
Icon=audio-headphones
Terminal=false
Categories=Utility;
EOF

if [[ "${1:-}" == "--autostart" ]]; then
    mkdir -p "$(dirname "$AUTO")"
    cat > "$AUTO" << EOF
[Desktop Entry]
Type=Application
Name=AirPods Batterie
Exec=$BIN --hidden
Icon=audio-headphones
Terminal=false
EOF
    echo "Démarrage automatique activé."
fi

echo "Installé : $BIN"
echo "Dépendances (Arch/Garuda) : sudo pacman -S python-bleak python-pyqt6"
