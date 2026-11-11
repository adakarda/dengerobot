"""Pleksi (akrilik) lazer kesim DXF uretici: 3 kat plakasi, sadece vida delikleri.
Calistir: python cad/pleksi_dxf.py
Uretir: cad/dxf/kat1.dxf, kat2.dxf, kat3.dxf, pleksi_hepsi.dxf (plakalar yan yana), cad/dxf/onizleme.png
Birim mm, 1:1, tek katman KES, kapali cizgiler. Plaka olculeri PLAKA'da; kat1 tekerlek yuzunden daha kisa.
Braket delikleri cad/robot_cad.py MOTOR_TAB_DELIK (L braket ayagi) ile ayni."""
import itertools
import math
import pathlib
import sys

import ezdxf

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import olcu as o  # noqa: E402
from robot_cad import MOTOR_TAB_DELIK  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "dxf"
OUT.mkdir(exist_ok=True)

DELIK = 3.4                      # M3 gecis
KOSE_R = 6.0
PLAKA_ARA = 15.0                 # pleksi_hepsi.dxf'te plakalar arasi bosluk
# (x boyu = ileri, y boyu = yanlara). Kat1, teker ic yuzune (|y| 82,5) 2,5 mm kala biter.
PLAKA = {"kat1": (80.0, 160.0), "kat2": (80.0, 170.0), "kat3": (80.0, 170.0)}
DISTANS = [(sx * 32.0, sy * 72.0) for sx in (-1, 1) for sy in (-1, 1)]
BTS_XY = (-12.0, 38.0)           # BTS7960 merkezi (x, |y|)
ANAKART_XY = (-10.0, 0.0)        # ana kart (altta asili) merkezi


def daire(cx, cy, d=DELIK):
    return ("circle", cx, cy, d / 2)


def yuvarlak_dikdortgen(sx, sy, r):
    b = math.tan(math.pi / 8)
    x, y = sx / 2, sy / 2
    pts = [(-x + r, -y), (x - r, -y), (x, -y + r), (x, y - r), (x - r, y), (-x + r, y), (-x, y - r), (-x, -y + r)]
    return ("poly", pts, [0, b, 0, b, 0, b, 0, b])


def dort_delik(cx, cy, ax, ay):
    return [daire(cx + sx * ax / 2, cy + sy * ay / 2) for sx in (-1, 1) for sy in (-1, 1)]


def kat1():
    """4 kose distansi + 2 BTS7960 (4'er delik) + 2 L braket (4'er delik)."""
    s = [daire(x, y) for x, y in DISTANS]
    s += [daire(x, y) for x, y in MOTOR_TAB_DELIK]                  # sol taraf (y > 0)
    s += [daire(x, -y) for x, y in MOTOR_TAB_DELIK]                 # sag taraf
    for sy in (1, -1):
        s += dort_delik(BTS_XY[0], sy * BTS_XY[1], o.BTS_DELIK, o.BTS_DELIK)
    return s


def kat2():
    """4 kose distansi + ana kart (altta asili) 4 delik."""
    s = [daire(x, y) for x, y in DISTANS]
    s += dort_delik(*ANAKART_XY, o.ANAKART_DELIK[1], o.ANAKART_DELIK[0])
    return s


def kat3():
    return [daire(x, y) for x, y in DISTANS]


PLAKALAR = {"kat1": kat1, "kat2": kat2, "kat3": kat3}


def yaz(msp, sekiller, dx=0.0):
    for sh in sekiller:
        if sh[0] == "circle":
            msp.add_circle((sh[1] + dx, sh[2]), sh[3], dxfattribs={"layer": "KES"})
        else:
            pts = [(x + dx, y) for x, y in sh[1]]
            msp.add_lwpolyline([(x, y, 0, 0, b) for (x, y), b in zip(pts, sh[2])], close=True, dxfattribs={"layer": "KES"})


def yeni_dxf():
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    doc.layers.add("KES", color=1)
    return doc, doc.modelspace()


def kontrol(ad, sekiller):
    """Delikler kenardan >= 4 mm iceride; deliklerin kenar-kenar arasi >= 3 mm."""
    px, py = PLAKA[ad]
    hata = []
    d = [(sh[1], sh[2], sh[3]) for sh in sekiller]
    for i, (x, y, r) in enumerate(d):
        if abs(x) + r > px / 2 - 4 or abs(y) + r > py / 2 - 4:
            hata.append(f"{ad}: delik {i} ({x:.1f},{y:.1f}) kenara <4 mm")
    for (i, a), (j, b) in itertools.combinations(enumerate(d), 2):
        if math.hypot(a[0] - b[0], a[1] - b[1]) - a[2] - b[2] < 3:
            hata.append(f"{ad}: delik {i} ve {j} birbirine <3 mm")
    return hata


def main():
    tum, msp_t = yeni_dxf()
    hatalar, dx = [], 0.0
    for ad, f in PLAKALAR.items():
        px, py = PLAKA[ad]
        sekiller = f()
        hatalar += kontrol(ad, sekiller)
        dis = yuvarlak_dikdortgen(px, py, KOSE_R)
        doc, msp = yeni_dxf()
        yaz(msp, [dis] + sekiller)
        doc.saveas(OUT / f"{ad}.dxf")
        yaz(msp_t, [dis] + sekiller, dx=dx + px / 2)
        dx += px + PLAKA_ARA
        print(f"{ad}: {px:g} x {py:g} mm, {len(sekiller)} delik")
    tum.saveas(OUT / "pleksi_hepsi.dxf")
    if hatalar:
        print("HATA:\n" + "\n".join(hatalar))
        return 1
    print("DXF kontrol: tamam")
    return 0


if __name__ == "__main__":
    sys.exit(main())
