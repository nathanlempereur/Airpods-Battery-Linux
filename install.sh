#!/bin/bash
# Installe / désinstalle AirPods Battery pour l'utilisateur courant (sans sudo).
# Lance simplement : ./install.sh   (le script te pose les questions)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin/airpods-battery"
WATCH="$HOME/.local/bin/airpods-battery-watch"
APPS="$HOME/.local/share/applications/airpods-battery.desktop"
AUTO="$HOME/.config/autostart/airpods-battery.desktop"

# choose "question" défaut max : pose une question à choix numérique
choose() {
    local ans
    while true; do
        read -rp "$1" ans || ans=""
        ans="${ans:-$2}"
        if [[ "$ans" =~ ^[1-$3]$ ]]; then
            echo "$ans"
            return
        fi
        echo "Réponse invalide : tape un chiffre entre 1 et $3." >&2
    done
}

stop_watcher() { pkill -f "bash $WATCH\$" 2>/dev/null || true; }


# --- vérifications (avertissements seulement) ---
if ! python3 -c "import bleak, PyQt6" 2>/dev/null; then
    echo
    echo "⚠ Il manque des dépendances Python. Sur Arch / Garuda :"
    echo "    sudo pacman -S python-bleak python-pyqt6"
    echo "  Ailleurs : pip install bleak PyQt6"
fi

# --- installation de l'appli ---
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

# --- mode de lancement ---
echo "=== AirPods Battery Linux ==="
echo
echo "Comment veux-tu lancer l'appli ?"
echo "  1) À la main, depuis le menu d'applications"
echo "  2) Au démarrage de ma session (icône dans la zone de notification)"
echo "  3) Automatiquement dès que mes AirPods se connectent"
mode=$(choose "Ton choix [3] : " 3 3)

stop_watcher
rm -f "$AUTO" "$WATCH"

case "$mode" in
    1)
        echo "Aucun lancement automatique."
        ;;
    2)
        mkdir -p "$(dirname "$AUTO")"
        cat > "$AUTO" << EOF
[Desktop Entry]
Type=Application
Name=AirPods Batterie
Exec=$BIN --hidden
Icon=audio-headphones
Terminal=false
EOF
        echo "L'appli démarrera avec ta session (icône seule)."
        ;;
    3)
        if ! command -v bluetoothctl >/dev/null; then
            echo "⚠ La commande 'bluetoothctl' est introuvable (paquet bluez-utils sur Arch)."
            echo "  Ce mode en a besoin pour détecter la connexion des AirPods."
        fi
        cat > "$WATCH" << 'EOF'
#!/usr/bin/env bash
# Lance AirPods Battery quand des AirPods se connectent, la ferme quand ils se déconnectent.
APP="$HOME/.local/bin/airpods-battery"
PATTERN="${APP}( |\$)"

airpods_connected() {
    local mac name
    while read -r _ mac name; do
        [[ "${name,,}" == *airpods* ]] || continue
        if bluetoothctl info "$mac" 2>/dev/null | grep -q "Connected: yes"; then
            return 0
        fi
    done < <(bluetoothctl devices 2>/dev/null)
    return 1
}

was_connected=0
while true; do
    if airpods_connected; then
        if [[ $was_connected -eq 0 ]]; then      # vient de se connecter
            pgrep -f "$PATTERN" >/dev/null || "$APP" &
            was_connected=1
        fi
    elif [[ $was_connected -eq 1 ]]; then        # vient de se déconnecter
        pkill -f "$PATTERN" 2>/dev/null || true
        was_connected=0
    fi
    sleep 5
done
EOF
        chmod +x "$WATCH"
        mkdir -p "$(dirname "$AUTO")"
        cat > "$AUTO" << EOF
[Desktop Entry]
Type=Application
Name=AirPods Batterie (surveillance)
Exec=$WATCH
Icon=audio-headphones
Terminal=false
EOF
        setsid nohup "$WATCH" </dev/null >/dev/null 2>&1 &
        echo "L'appli s'ouvrira dès que tes AirPods se connecteront, et se fermera à leur déconnexion."
        echo "(Si tu la quittes toi-même, elle ne se relance qu'à la prochaine connexion.)"
        ;;
esac

echo
echo "Installé : $BIN"
echo "Pour changer de mode, relance ./install.sh et ./uninstall.sh pour supprimer l'app"
