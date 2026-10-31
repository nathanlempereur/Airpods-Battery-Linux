# AirPods Battery Linux

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

## Installation

Dépendances (Arch / Garuda / Manjaro) :

```bash
sudo pacman -S python-bleak python-pyqt6
```

Autres distributions : `pip install bleak PyQt6`.

Puis :

```bash
git clone (https://github.com/nathanlempereur/Airpods-Battery-Linux.git)
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

## Licence

MIT, voir [LICENSE](LICENSE).
