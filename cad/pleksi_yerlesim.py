"""Pleksi katlarin ustundeki/altindaki parcalarin onerilen yerlesimi -> cad/dxf/yerlesim.png (x ileri yukari, y sol)."""
import pathlib
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import olcu as o
import pleksi_dxf as d

TEKER = [(-27.2, 27.2, 82.5, 107.5)]   # kat1 z=22'de tekerlek x yari genisligi 27,2 (referans)


def cizim(ax, ad, parcalar, baslik):
    px, py = PLAKA = d.PLAKA[ad]
    ax.add_patch(Rectangle((-px / 2, -py / 2), px, py, fc="#e8f3f8", ec="navy", lw=1.5, zorder=0))
    for sh in d.PLAKALAR[ad]():
        ax.add_patch(Circle((sh[1], sh[2]), sh[3], fc="white", ec="gray", lw=.8, zorder=1))
    for (n, cx, cy, sx, sy, renk, alt) in parcalar:
        ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy, fc=renk, ec="k", lw=1.1, alpha=.25 if alt else .55,
                               ls="--" if alt else "-", zorder=2))
        ax.text(cx, cy, n, ha="center", va="center", fontsize=7.5, zorder=3)
    ax.set_xlim(-60, 60); ax.set_ylim(-100, 100); ax.set_aspect("equal")
    ax.set_title(f"{baslik}  [{px:g} x {py:g} mm]", fontsize=9)
    ax.set_xlabel("x (ileri) mm"); ax.set_ylabel("y (sol) mm")
    ax.annotate("ON", (0, 93), ha="center", fontsize=8, color="crimson")


fig, axs = plt.subplots(1, 3, figsize=(17, 11))
k1 = []
for s in (1, -1):
    k1.append(("BTS7960", d.BTS_XY[0], s * d.BTS_XY[1], o.BTS[1], o.BTS[0], "#f4a261", False))
    k1.append(("WAGO", 28.0, s * 28.0, o.WAGO[1], o.WAGO[0], "#adb5bd", False))
    k1.append(("L braket ayagi" + chr(10) + "(altta)", 0.0, s * (78 - 41 / 2), 40.0, 38.0, "#bdb2ff", True))
k1 += [("MPU6050", 0.0, 0.0, o.MPU[0], o.MPU[1], "#e76f51", False),
       ("1000uF", 24.0, 0.0, o.C5[0], o.C5[1], "#577590", False)]
cizim(axs[0], "kat1", k1, "KAT 1 (alt)")
k2 = [("3x18650 pil", 0.0, 0.0, o.PIL[1], o.PIL[0], "#43aa8b", False),
      ("BMS (yatik)", 0.0, 58.0, o.BMS[0], o.BMS[1], "#f9c74f", False),
      ("XT60", 0.0, 76.0, o.XT60[0], o.XT60[1], "#e63946", False),
      ("LM2596 (yatik)", 0.0, -60.0, o.LM2596[0], o.LM2596[1], "#90be6d", False),
      ("ANA KART" + chr(10) + "(altta asili)", d.ANAKART_XY[0], d.ANAKART_XY[1], o.ANAKART[1], o.ANAKART[0], "#6a4c93", True)]
cizim(axs[1], "kat2", k2, "KAT 2 (orta)")
k3 = [("sigorta (yatik)", 0.0, 0.0, o.SIGORTA[0], o.SIGORTA[1], "#f9c74f", False)]
cizim(axs[2], "kat3", k3, "KAT 3 (ust)")
fig.tight_layout()
fig.savefig(pathlib.Path(__file__).resolve().parent / "dxf" / "yerlesim.png", dpi=100)
print("tamam")
