"""cad/montaj.glb ve cad/stl/*.stl'den onizleme resimleri -> docs/img/cad_*.png"""
import pathlib

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMG = ROOT / "docs/img"
ISIK = np.array([0.4, -0.5, 0.8])
ISIK = ISIK / np.linalg.norm(ISIK)


def golgeli(ax, mesh, renk, alfa=1.0):
    n = mesh.face_normals
    k = 0.45 + 0.55 * np.clip(n @ ISIK, 0, 1)
    c = np.clip(np.outer(k, np.asarray(renk[:3]) / 255.0), 0, 1)
    pc = Poly3DCollection(mesh.vertices[mesh.faces], facecolors=np.c_[c, np.full(len(c), alfa)], linewidths=0)
    ax.add_collection3d(pc)


def eksen(ax, lo, hi):
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()


def montaj():
    sahne = trimesh.load(ROOT / "cad/montaj.glb")
    parcalar = []
    for ad, g in sahne.geometry.items():
        m = g.copy()
        m.apply_transform(sahne.graph.get(ad)[0] if ad in sahne.graph.nodes else np.eye(4))
        renk = m.visual.face_colors[0] if hasattr(m.visual, "face_colors") else (180, 180, 180, 255)
        parcalar.append((ad, m, renk))
    lo = np.min([m.bounds[0] for _, m, _ in parcalar], axis=0)
    hi = np.max([m.bounds[1] for _, m, _ in parcalar], axis=0)
    fig = plt.figure(figsize=(13, 5.2))
    for i, (baslik, elev, azim) in enumerate((("Montaj (önden-sağdan)", 22, -35), ("Önden", 0, 0), ("Yandan (ön sağda)", 0, -90))):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        ax.view_init(elev=elev, azim=azim)
        for ad, m, renk in parcalar:
            golgeli(ax, m, renk, 0.55 if ad.startswith("baski_kat") else 1.0)
        eksen(ax, lo, hi)
        ax.set_title(baslik, fontsize=10)
    fig.tight_layout()
    fig.savefig(IMG / "cad_montaj.png", dpi=120)
    plt.close(fig)


def parcalar():
    adlar = ["kat1", "kat2", "kat3", "motor_tutucu_sol", "v_yuva"]
    fig = plt.figure(figsize=(15, 3.6))
    for i, ad in enumerate(adlar):
        m = trimesh.load(ROOT / f"cad/stl/{ad}.stl")
        ax = fig.add_subplot(1, len(adlar), i + 1, projection="3d")
        ax.view_init(elev=35, azim=-60)
        golgeli(ax, m, (90, 150, 230))
        eksen(ax, m.bounds[0], m.bounds[1])
        ax.set_title(f"{ad}.stl (baskı yönü)", fontsize=9)
    fig.tight_layout()
    fig.savefig(IMG / "cad_parcalar.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    montaj()
    parcalar()
    print("cizildi")
