#!/usr/bin/env python3
"""
airpods-gui.py — batterie des AirPods dans une fenêtre façon macOS
(coins arrondis, boutons rouge / jaune / vert, jauges rondes animées).

Dépendances : sudo pacman -S python-bleak python-pyqt6
Lancer (SANS sudo) : python3 airpods-gui.py

Une icône apparaît dans la zone de notification (à côté du Bluetooth, de la
batterie...) : clic gauche = afficher / masquer la fenêtre, clic droit = menu.

Boutons : rouge = masquer (l'icône reste), jaune = masquer, vert = épingler
(la fenêtre reste affichée au premier plan au lieu de se fermer quand on clique
ailleurs). Glisse la fenêtre n'importe où pour la déplacer.
Option : --hidden pour démarrer uniquement dans la zone de notification.
"""
import asyncio
import subprocess
import sys
import threading
import time

from bleak import BleakScanner
from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QAction, QColor, QFont, QFontMetrics, QGuiApplication,
                         QIcon, QPainter, QPainterPath, QPen, QPixmap,
                         QPolygonF, QRegion)
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

APPLE_ID = 0x004C
RSSI_MIN = -70       # ignore les AirPods trop loin
SCAN_SECONDS = 5     # durée d'un cycle de scan
STALE_AFTER = 30     # secondes sans signal avant de griser

state = {"info": None, "ts": 0.0, "error": None, "name": None}
lock = threading.Lock()


# ---------- décodage BLE ----------
def pct(v):
    if v == 15:
        return None
    return 100 if v >= 10 else v * 10 + 5


def parse(data: bytes):
    i = 0
    while i + 1 < len(data):
        t, ln = data[i], data[i + 1]
        payload = data[i + 2 : i + 2 + ln]
        if t == 0x07 and len(payload) >= 6:
            status, pods, extra = payload[3], payload[4], payload[5]
            flip = (status & 0x20) == 0
            hi, lo = pods >> 4, pods & 0x0F
            left, right = (hi, lo) if flip else (lo, hi)
            flags = extra >> 4
            return {
                "left": (pct(left), bool(flags & (0x02 if flip else 0x01))),
                "right": (pct(right), bool(flags & (0x01 if flip else 0x02))),
                "case": (pct(extra & 0x0F), bool(flags & 0x04)),
            }
        i += 2 + ln
    return None


def get_rssi(device, adv):
    for obj in (adv, device):
        v = getattr(obj, "rssi", None)
        if isinstance(v, int):
            return v
    try:
        for item in adv.platform_data:
            if isinstance(item, dict) and "RSSI" in item:
                v = item["RSSI"]
                return int(getattr(v, "value", v))
    except Exception:
        pass
    return None


def find_device_name():
    """Nom réel des AirPods appairés (ex. « AirPods Pro de Nathan »)."""
    try:
        out = subprocess.run(["bluetoothctl", "devices"], capture_output=True,
                             text=True, timeout=4).stdout
        for line in out.splitlines():
            parts = line.split(" ", 2)
            if len(parts) == 3 and "airpods" in parts[2].lower():
                return parts[2].strip()
    except Exception:
        pass
    return None


# ---------- scan en arrière-plan ----------
async def scan_forever():
    while True:
        best = None

        def on_detect(device, adv):
            nonlocal best
            raw = adv.manufacturer_data.get(APPLE_ID)
            if not raw:
                return
            rssi = get_rssi(device, adv)
            if rssi is not None and rssi < RSSI_MIN:
                return
            info = parse(bytes(raw))
            if not info:
                return
            score = rssi if rssi is not None else -50
            if best is None or score > best[0]:
                best = (score, info)

        try:
            async with BleakScanner(detection_callback=on_detect):
                await asyncio.sleep(SCAN_SECONDS)
            with lock:
                state["error"] = None
                if best:
                    state["info"], state["ts"] = best[1], time.time()
        except Exception as e:
            with lock:
                state["error"] = str(e)
            await asyncio.sleep(5)


def run_scanner():
    name = find_device_name()
    with lock:
        state["name"] = name
    asyncio.run(scan_forever())


# ---------- couleurs ----------
RED = QColor(255, 69, 58)
GRAY = QColor(142, 142, 147)
LIGHTS = [QColor("#ff5f57"), QColor("#febc2e"), QColor("#28c840")]  # fermer, réduire, épingler
# dégradé de la jauge : plein = vert, puis jaune, orange, rouge quand ça descend
STOPS = [(0, (255, 69, 58)), (25, (255, 159, 10)), (50, (255, 214, 10)),
         (80, (48, 209, 88)), (100, (48, 209, 88))]


def level_color(v):
    v = max(0.0, min(100.0, v))
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            return QColor(*[round(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)])
    return QColor(*STOPS[-1][1])


ITEMS = [("Gauche", "left"), ("Boîtier", "case"), ("Droit", "right")]


# ---------- fenêtre façon macOS ----------
class Card(QWidget):
    W, H = 330, 190
    R = 12            # rayon des coins

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setWindowTitle("AirPods")
        self.setFixedSize(self.W, self.H)

        # masque arrondi : plus de carré flou autour de la fenêtre
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.W, self.H), self.R, self.R)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

        self.pinned = False
        self.tray_ok = False
        self.last_auto_hide = 0.0
        self.hover = False
        self.disp = {"left": 0.0, "right": 0.0, "case": 0.0}   # valeurs animées
        self.info, self.age, self.err, self.name = None, None, None, None

        self.font_ = QFont()
        self.font_.setFamilies(["SF Pro Text", "Inter", "Noto Sans", "Sans Serif"])

        t = QTimer(self)
        t.timeout.connect(self.tick)
        t.start(33)

    def tick(self):
        with lock:
            info, ts, err, name = (state["info"], state["ts"],
                                   state["error"], state["name"])
        self.info, self.err, self.name = info, err, name
        self.age = (time.time() - ts) if info else None
        for key in self.disp:
            target = (info[key][0] or 0) if info else 0
            self.disp[key] += (target - self.disp[key]) * 0.18
        self.update()

    @property
    def stale(self):
        return self.age is None or self.age > STALE_AFTER

    # -- boutons --
    def light_center(self, i):
        return QPointF(20 + i * 20, 19)

    def light_at(self, pos):
        for i in range(3):
            c = self.light_center(i)
            if (pos.x() - c.x()) ** 2 + (pos.y() - c.y()) ** 2 <= 8 ** 2:
                return i
        return None

    def group_rect(self):
        return QRectF(8, 7, 66, 24)

    def mouseMoveEvent(self, e):
        h = self.group_rect().contains(e.position())
        if h != self.hover:
            self.hover = h
            self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def event(self, e):
        if (e.type() == QEvent.Type.WindowDeactivate and self.tray_ok
                and not self.pinned):
            QTimer.singleShot(120, self._auto_hide)
        return super().event(e)

    def _auto_hide(self):
        if self.isVisible() and not self.pinned and not self.isActiveWindow():
            self.last_auto_hide = time.monotonic()
            self.hide()

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        i = self.light_at(e.position())
        if i == 0:
            self.hide() if self.tray_ok else QApplication.quit()
        elif i == 1:
            self.hide() if self.tray_ok else self.showMinimized()
        elif i == 2:
            self.pinned = not self.pinned
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.pinned)
            self.show()
        elif self.windowHandle():
            self.windowHandle().startSystemMove()

    # -- dessin --
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H, R = self.W, self.H, self.R

        # corps
        body = QRectF(0, 0, W, H)
        path = QPainterPath()
        path.addRoundedRect(body, R, R)
        p.fillPath(path, QColor(32, 32, 35, 252))
        p.setPen(QPen(QColor(255, 255, 255, 38), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body.adjusted(.5, .5, -.5, -.5), R, R)

        # titre = vrai nom des AirPods
        p.setPen(QPen(QColor(0, 0, 0, 90), 1))
        p.drawLine(QPointF(1, 38), QPointF(W - 1, 38))
        f = QFont(self.font_)
        f.setPixelSize(13)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        title = self.name or "AirPods Pro"
        title = QFontMetrics(f).elidedText(title, Qt.TextElideMode.ElideRight, W - 150)
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(QRectF(0, 0, W, 38), Qt.AlignmentFlag.AlignCenter, title)

        # boutons rouge / jaune / vert
        for i, col in enumerate(LIGHTS):
            c = self.light_center(i)
            p.setPen(QPen(QColor(0, 0, 0, 40), 1))
            p.setBrush(col)
            p.drawEllipse(c, 6, 6)
            if i == 2 and self.pinned and not self.hover:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 0, 0, 120))
                p.drawEllipse(c, 2, 2)
            if self.hover:
                p.setPen(QPen(QColor(0, 0, 0, 140), 1.4, Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap))
                if i == 0:
                    p.drawLine(QPointF(c.x() - 2, c.y() - 2), QPointF(c.x() + 2, c.y() + 2))
                    p.drawLine(QPointF(c.x() - 2, c.y() + 2), QPointF(c.x() + 2, c.y() - 2))
                else:
                    p.drawLine(QPointF(c.x() - 2.5, c.y()), QPointF(c.x() + 2.5, c.y()))
                    if i == 2:
                        p.drawLine(QPointF(c.x(), c.y() - 2.5), QPointF(c.x(), c.y() + 2.5))

        # jauges rondes
        d, pw = 70, 7
        cell = W / 3
        cy = 38 + 20 + d / 2
        vf = QFont(self.font_)
        vf.setPixelSize(15)
        vf.setWeight(QFont.Weight.DemiBold)
        lf = QFont(self.font_)
        lf.setPixelSize(12)
        for n, (label, key) in enumerate(ITEMS):
            cx = cell * n + cell / 2
            value, charging = (self.info[key] if self.info else (None, False))
            no_value = value is None
            color = GRAY if (no_value or self.stale) else level_color(self.disp[key])

            r = QRectF(cx - d / 2 + pw / 2, cy - d / 2 + pw / 2, d - pw, d - pw)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 30), pw))
            p.drawEllipse(r)
            if not no_value and self.disp[key] > 0.3:
                p.setPen(QPen(color, pw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(r, 90 * 16, -int(self.disp[key] * 3.6 * 16))

            # texte au centre
            text = "—" if no_value else f"{value}%"
            p.setFont(vf)
            p.setPen(QColor(255, 255, 255, 150 if (no_value or self.stale) else 240))
            dy = 5 if (charging and not no_value) else 0
            p.drawText(QRectF(cx - d / 2, cy - d / 2 + dy, d, d),
                       Qt.AlignmentFlag.AlignCenter, text)

            # éclair si ça charge
            if charging and not no_value:
                bx, by = cx - 4, cy - 21
                bolt = QPolygonF([QPointF(bx + 5, by), QPointF(bx, by + 7.5),
                                  QPointF(bx + 3.5, by + 7.5), QPointF(bx + 2.5, by + 13),
                                  QPointF(bx + 8, by + 5), QPointF(bx + 4.5, by + 5)])
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color)
                p.drawPolygon(bolt)

            # nom sous la jauge
            p.setFont(lf)
            p.setPen(QColor(255, 255, 255, 200))
            p.drawText(QRectF(cx - cell / 2, cy + d / 2 + 6, cell, 18),
                       Qt.AlignmentFlag.AlignCenter, label)

        # état en bas
        if self.err:
            status, scol = f"Erreur Bluetooth : {self.err[:38]}", RED
        elif self.info is None:
            status, scol = "Recherche des AirPods… (ouvre le boîtier)", None
        elif self.stale:
            status, scol = f"Signal perdu depuis {int(self.age)} s", None
        else:
            status, scol = f"Mis à jour il y a {int(self.age)} s", None
        sf = QFont(self.font_)
        sf.setPixelSize(11)
        p.setFont(sf)
        p.setPen(scol or QColor(255, 255, 255, 105))
        p.drawText(QRectF(0, H - 28, W, 20), Qt.AlignmentFlag.AlignCenter, status)
        p.end()


# ---------- icône de la zone de notification ----------
def make_icon(value, stale):
    """Petit anneau coloré avec le niveau le plus bas des deux écouteurs."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = GRAY if (value is None or stale) else level_color(value)
    r = QRectF(6, 6, 52, 52)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(128, 128, 128, 90), 8))
    p.drawEllipse(r)
    if value is not None:
        p.setPen(QPen(color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, 90 * 16, -int(value * 3.6 * 16))
    f = QFont()
    f.setBold(True)
    text = "–" if value is None else str(value)
    f.setPixelSize(26 if len(text) < 3 else 20)
    p.setFont(f)
    p.setPen(color)
    p.drawText(QRectF(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return QIcon(pm)


class Tray:
    def __init__(self, card):
        self.card = card
        self.key = None
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(make_icon(None, True))
        self.tray.setToolTip("AirPods — recherche…")

        menu = QMenu()
        act_show = QAction("Afficher / masquer", menu)
        act_show.triggered.connect(self.toggle)
        act_quit = QAction("Quitter", menu)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_activated)
        self.tray.show()

        t = QTimer()
        t.timeout.connect(self.refresh)
        t.start(1000)
        self.timer = t

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle()

    def toggle(self):
        c = self.card
        if c.isVisible():
            c.hide()
        elif time.monotonic() - c.last_auto_hide > 0.4:   # évite le « réouvre aussitôt »
            self.show_popup()

    def show_popup(self):
        c = self.card
        g = self.tray.geometry()
        has_geo = g.isValid() and not g.isEmpty()
        screen = (QGuiApplication.screenAt(g.center()) if has_geo else None) \
            or QGuiApplication.primaryScreen()
        sg = screen.availableGeometry()
        if has_geo:
            x = g.center().x() - c.W // 2
            y = g.bottom() + 8 if g.center().y() < sg.center().y() else g.top() - c.H - 8
        else:                                   # position inconnue : coin haut droit
            x, y = sg.right() - c.W - 12, sg.top() + 12
        x = max(sg.left() + 8, min(x, sg.right() - c.W - 8))
        y = max(sg.top() + 8, min(y, sg.bottom() - c.H - 8))
        c.move(x, y)
        c.show()
        c.raise_()
        c.activateWindow()

    def refresh(self):
        c = self.card
        info, stale = c.info, c.stale
        pods = [info[k][0] for k in ("left", "right") if info and info[k][0] is not None]
        low = min(pods) if pods else (info["case"][0] if info else None)
        key = (low, stale)
        if key != self.key:
            self.key = key
            self.tray.setIcon(make_icon(low, stale))

        name = c.name or "AirPods Pro"
        if info is None:
            tip = f"{name}\nRecherche…"
        else:
            def fmt(k):
                v, ch = info[k]
                return "?" if v is None else f"{v}%" + (" ⚡" if ch else "")
            tip = (f"{name}\nGauche {fmt('left')} · Droit {fmt('right')}\n"
                   f"Boîtier {fmt('case')}")
            if stale:
                tip += "\n(signal perdu)"
        self.tray.setToolTip(tip)


def main():
    threading.Thread(target=run_scanner, daemon=True).start()
    app = QApplication(sys.argv)
    app.setApplicationName("AirPods")
    app.setDesktopFileName("airpods-battery")
    app.setQuitOnLastWindowClosed(False)

    card = Card()
    card.tray_ok = QSystemTrayIcon.isSystemTrayAvailable()
    tray = Tray(card) if card.tray_ok else None
    if "--hidden" not in sys.argv or tray is None:
        if tray:
            QTimer.singleShot(400, tray.show_popup)   # laisse l'icône s'enregistrer
        else:
            card.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
