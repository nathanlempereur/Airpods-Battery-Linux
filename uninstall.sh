#!/usr/bin/env bash
# Désinstalle AirPods Battery (sans sudo).
# Lance simplement : ./uninstall.sh

BIN="$HOME/.local/bin/airpods-battery"
WATCH="$HOME/.local/bin/airpods-battery-watch"
APPS="$HOME/.local/share/applications/airpods-battery.desktop"
AUTO="$HOME/.config/autostart/airpods-battery.desktop"

echo "Désinstallation de AirPods Battery..."

# on arrête d'abord la surveillance
pkill -f "bash $WATCH\$" 2>/dev/null || true
pkill -f "$BIN( |\$)" 2>/dev/null || true

status=0
for f in "$BIN" "$WATCH" "$APPS" "$AUTO"; do
    rm -f "$f" || status=1
done

if [[ $status -eq 0 ]]; then
    echo "Désinstallé."
else
    echo "Erreur de suppression." >&2
    exit 1
fi
