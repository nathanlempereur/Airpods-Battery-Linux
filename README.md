# AirPods Battery Linux

![Version](https://img.shields.io/badge/version-1.1-blue.svg)
![Status](https://img.shields.io/badge/status-Libre-orange)
![Linux](https://img.shields.io/badge/Arch-compatible-success)


Affiche la batterie de tes **AirPods** (écouteur gauche, droit, boîtier) sous Linux,
dans une petite fenêtre façon macOS et une icône de la zone de notification.

Développé et utilisé sur **Garuda Linux (base Arch)** avec des **AirPods Pro 3**.

## Fonctionnalités

- Jauges rondes animées, avec un dégradé vert → jaune → orange → rouge selon le niveau
- Icône dans la zone de notification (niveau le plus bas + infobulle détaillée)
- Fenêtre sans bordure aux coins arrondis, boutons rouge / jaune / vert
  (rouge et jaune masquent, vert épingle au premier plan)
- Affiche le vrai nom de tes AirPods appairés
- Actualisation automatique, avec indication « signal perdu » si plus rien n'est reçu
- Aucune connexion, aucun compte, rien ne sort de ta machine : l'appli écoute simplement
  les annonces Bluetooth LE émises par les AirPods

## Compatibilité

Légende : ✅ testé · 🟡 devrait fonctionner (non testé) · ❔ inconnu · ❌ non géré

> Seule la combinaison **Garuda Linux + AirPods Pro 3** a été testée. Le reste est déduit
> du fonctionnement technique (même système Bluetooth, même format de message Apple).
> Un retour d'expérience, bon ou mauvais, est le bienvenu dans les *Issues*.

### Modèles d'AirPods

| Modèle | Statut | Remarque |
|---|---|---|
| AirPods Pro 3 | ✅ | Testé |
| AirPods Pro 2 (Lightning / USB-C) | 🟡 | Même format d'annonce |
| AirPods Pro (1re génération) | 🟡 | Même format d'annonce |
| AirPods 4 (avec ou sans réduction de bruit) | 🟡 | Même format d'annonce |
| AirPods 3 | 🟡 | Même format d'annonce |
| AirPods 2 | 🟡 | Même format d'annonce |
| AirPods (1re génération) | 🟡 | Même format d'annonce |
| AirPods Max | ❌ | Une seule batterie et pas de boîtier : l'affichage gauche / droit / boîtier ne serait pas correct |
| Beats (Powerbeats Pro, Beats Fit Pro, Studio Buds…) | ❔ | Format proche, mais non testé ; le nom réel n'est pas détecté (il doit contenir « AirPods ») |

Si plusieurs appareils Apple émettent à proximité, c'est le signal le plus fort (le plus proche) qui est retenu.

### Systèmes

| Système | Statut | Remarque |
|---|---|---|
| Garuda Linux | ✅ | Testé |
| Arch Linux, EndeavourOS, Manjaro | 🟡 | Mêmes paquets que Garuda |
| Debian, Ubuntu, Linux Mint, Pop!_OS | 🟡 | Paquets `python3-pyqt6` et `python3-bleak` (ou `pip install bleak`) |
| Fedora, openSUSE | 🟡 | Équivalents des paquets Python ci-dessus, ou `pip` |
| Windows | ❔ | Non prévu : `bleak` et PyQt6 existent, mais l'appli n'a pas été essayée et le nom réel des AirPods ne serait pas lu |
| macOS | ❔ | Non prévu (macOS affiche déjà la batterie nativement) |

Prérequis : Linux avec **BlueZ** (service `bluetooth` actif), un adaptateur **Bluetooth 4.0 ou plus**
(Bluetooth Low Energy) et **Python 3.9+**.

### Environnements de bureau

| Environnement | Statut | Remarque |
|---|---|---|
| KDE Plasma, XFCE, Cinnamon, MATE, LXQt, Budgie | 🟡 | Zone de notification native |
| GNOME | 🟡 | Il faut l'extension *AppIndicator / KStatusNotifierItem* pour voir l'icône ; sans elle, l'appli affiche directement la fenêtre (le bouton rouge quitte alors l'appli) |
| Hyprland, Sway, i3 | 🟡 | Avec une barre qui gère le tray (waybar, polybar…) |
| X11 | 🟡 | La fenêtre s'ouvre à côté de l'icône |
| Wayland | 🟡 | Le compositeur peut ignorer la position demandée ; la fenêtre reste déplaçable |

## Installation

Dépendances (Arch / Garuda / Manjaro) :

```bash
sudo pacman -S python-bleak python-pyqt6
```

Autres distributions : `pip install bleak PyQt6` (ou les paquets de ta distribution,
voir le tableau plus haut).

Puis :

```bash
git clone https://github.com/nathanlempereur/Airpods-Battery-Linux.git
cd Airpods-Battery-Linux
./install.sh               # ajoute l'appli au menu
./install.sh --autostart   # + démarrage automatique (icône seule)
```

Désinstaller : `./install.sh --uninstall`.

Ou sans installer : `python3 airpods-battery.py` (**sans sudo**).

## Utilisation

- Clic gauche sur l'icône : afficher / masquer la fenêtre
- Clic droit : menu (afficher / masquer, quitter)
- `--hidden` : démarre uniquement dans la zone de notification

## Comment ça marche

Les AirPods diffusent en Bluetooth LE un message Apple « proximity pairing » qui contient
le niveau de batterie de chaque écouteur et du boîtier (par paliers de 10 %). Le script
scanne ces annonces avec [bleak](https://github.com/hbldh/bleak), décode le message et
garde les AirPods les plus proches.

## Limites

- Les AirPods n'émettent pas en continu : ouvre le boîtier ou sors-les si rien n'apparaît
- Le format de message est celui des générations précédentes ; il fonctionne avec les Pro 3,
  mais Apple peut le modifier
- Sous Wayland, KDE peut ignorer la position demandée pour la fenêtre (elle reste déplaçable)
- La batterie est donnée par paliers, donc approximative

## Contribution & Licence

Ce module est **open-source**. Vous pouvez le modifier et proposer des améliorations via des **Pull Requests**.

**Licence** : Ce projet est sous licence libre.
**Contact** : contact@nlempereur.ovh

### Contact
- Email : **contact@nlempereur.ovh**
- Site web : https://nlempereur.ovh/contact.php
- Portfolio : https://nlempereur.ovh

