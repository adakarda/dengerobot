"""Pololu 3272 (70x25 mm, 608 rulman yuvali) kaykay tekerlegi icin 3B baski surucu gobek, JGB37-520 6 mm D mil.
Calistir: python cad/teker_gobek.py   ->  cad/stl/teker_gobek_A.stl, teker_kapak_B.stl, teker_olcu_testi.stl
Iki parca: A (motor tarafi: mil deligi + yuvaya giren tapa + iç kenardan gecen burun) ve B (disaridan kapak).
Uc M3 vida B'den girer, A'daki somunlara sikilir; tekerlegin ic kenari iki tapa arasinda sikisir.
DEGERLER TAHMINDIR (608 standardi: yuva 22 mm, 7 mm derin). Once teker_olcu_testi.stl'yi basip tekerlege deneyin,
sonra asagidaki SEAT_D, SEAT_DEPTH, LIP_D'yi kumpas olcusune gore degistirin."""
import math
import pathlib

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold

OUT = pathlib.Path(__file__).resolve().parent / "stl"
SEG = 96

# ---- tekerlek (OLC: kumpasla dogrulayin) ----
WHEEL_W = 25.0          # teker genisligi
SEAT_D = 22.0           # 608 yuvasi ic capi
SEAT_DEPTH = 7.0        # yuva derinligi (608 rulman genisligi)
LIP_D = 16.0            # iki yuva arasindaki ic kenarin orta deligi (TAHMIN)
FIT = 0.2               # tapa ile yuva arasi bosluk (cap farki)
# ---- mil: JGB37-520 ----
SHAFT_D, SHAFT_FLAT, SHAFT_L = 6.0, 5.5, 15.0
BORE_CL = 0.15
# ---- gobek ----
BOSS_D, BOSS_L = 16.0, 6.5       # motor yuzu ile tekerlek ic yuzu arasi 7.5 mm; 1 mm bosluk kalir
PCD = 11.0                       # vida dairesi capi (3 x M3)
M3_CL, NUT_AF, NUT_T = 3.4, 5.7 + 0.25, 2.4 + 0.2
HEAD_D, HEAD_H = 6.4, 3.4        # M3 yuvarlak bas vida yuva


def cyl(r, z0, z1):
    return Manifold.cylinder(z1 - z0, r, r, SEG).translate([0, 0, z0])


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def hex_prism_z(af, z0, z1, cx=0.0, cy=0.0, rot=0.0):
    r = af / math.sqrt(3)
    pts = [(cx + r * math.cos(math.radians(rot + 60 * i)), cy + r * math.sin(math.radians(rot + 60 * i))) for i in range(6)]
    return CrossSection([pts]).extrude(z1 - z0).translate([0, 0, z0])


def d_bore(z0, z1):
    r = SHAFT_D / 2 + BORE_CL
    flat = SHAFT_FLAT + BORE_CL
    disk = CrossSection.circle(r, SEG)
    half = CrossSection.square([2 * r, 2 * r]).translate([-r, -r - (r - (flat - r)) * 0])  # yer tutucu
    # duz yuz +X tarafinda: x <= flat - r
    cut = CrossSection.square([4 * r, 4 * r]).translate([flat - r, -2 * r])
    return (disk - cut).extrude(z1 - z0).translate([0, 0, z0])


def screw_pts():
    return [(PCD / 2 * math.cos(math.radians(a)), PCD / 2 * math.sin(math.radians(a))) for a in (90, 210, 330)]


def parca_A():
    plug_r = (SEAT_D - FIT) / 2
    nose_r = (LIP_D - 0.4) / 2
    z_boss, z_plug = BOSS_L, BOSS_L + SEAT_DEPTH
    web = WHEEL_W - 2 * SEAT_DEPTH
    z_nose = z_plug + web
    a = cyl(BOSS_D / 2, 0, z_boss) + cyl(plug_r, z_boss, z_plug) + cyl(nose_r, z_plug, z_nose)
    # mil deligi (kor, 14 mm; mil 15 mm, duz kisim 12 mm)
    a = a - d_bore(-1, 14.0)
    # sabitleme vidasi (M3 set vida) +X yonunde duz yuze; somun cebi disaridan
    zc = BOSS_L / 2
    a = a - Manifold.cylinder(BOSS_D, 1.5, 1.5, 32).rotate([0, 90, 0]).translate([0, 0, zc])
    nut = hex_prism_z(NUT_AF, 0, 4.0).rotate([0, 90, 0]).translate([5.0, 0, zc])  # eksen X, 5..9 mm
    a = a - nut
    # vida kanallari: burun ucundan somuna kadar M3 gecis; somun cebi radyal yuvalar tapada
    for i, (x, y) in enumerate(screw_pts()):
        a = a - cyl_at(x, y, M3_CL / 2, z_plug - 5.0, z_nose + 1)
        zn0 = z_boss + 1.2
        ang = math.degrees(math.atan2(y, x))
        slot = box(0, plug_r + 1, -NUT_AF / 2, NUT_AF / 2, zn0, zn0 + NUT_T).translate([0, 0, 0])
        slot = slot.rotate([0, 0, ang]).translate([0, 0, 0])
        # yuva: somunun vida eksenine (x,y) ortalanmasi icin kaydir
        slot = box(PCD / 2 - NUT_AF / 2, plug_r + 1, -NUT_AF / 2, NUT_AF / 2, zn0, zn0 + NUT_T).rotate([0, 0, ang])
        a = a - slot
    return a, z_nose


def cyl_at(x, y, r, z0, z1):
    return Manifold.cylinder(z1 - z0, r, r, 48).translate([x, y, z0])


def parca_B():
    plug_r = (SEAT_D - FIT) / 2
    b = cyl(plug_r, 0, SEAT_DEPTH)
    for x, y in screw_pts():
        b = b - cyl_at(x, y, M3_CL / 2, -1, SEAT_DEPTH + 1)
        b = b - cyl_at(x, y, HEAD_D / 2, SEAT_DEPTH - HEAD_H, SEAT_DEPTH + 1)
    return b


def olcu_testi():
    """Tapa ve burun icin deneme diskleri: yuvaya ve ic kenar deligine sigan en buyuk olani secin."""
    parcalar = []
    for i, d in enumerate((21.6, 21.8, 22.0, 22.2)):
        parcalar.append(cyl(d / 2, 0, 4).translate([i * 26, 0, 0]))
    for i, d in enumerate((14.0, 15.0, 15.6, 16.0)):
        parcalar.append(cyl(d / 2, 0, 4).translate([i * 20, 28, 0]))
    m = parcalar[0]
    for p in parcalar[1:]:
        m = m + p
    return m


def kaydet(m, ad):
    me = m.to_mesh()
    t = trimesh.Trimesh(vertices=np.array(me.vert_properties)[:, :3], faces=np.array(me.tri_verts))
    t.export(OUT / ad)
    return t


def main():
    a, z_nose = parca_A()
    b = parca_B()
    ta, tb, tt = kaydet(a, "teker_gobek_A.stl"), kaydet(b, "teker_kapak_B.stl"), kaydet(olcu_testi(), "teker_olcu_testi.stl")
    # montaj denetimi: B, A'nin burun ucunda; ikisi ust uste binmemeli
    bm = b.translate([0, 0, z_nose])
    ov = (a ^ bm).volume()
    ok = a.volume() > 0 and b.volume() > 0 and ov < 1e-6
    for n, t in (("A", ta), ("B", tb)):
        print(f"{n}: watertight={t.is_watertight} hacim={t.volume/1000:.2f} cm3 olcu={np.round(t.extents, 1)} mm")
    print(f"A ve B ust uste binmiyor: {ov:.3f} mm3; toplam boy {z_nose + SEAT_DEPTH:.1f} mm (boss {BOSS_L} + teker {WHEEL_W})")
    print("TAMAM" if ok and ta.is_watertight and tb.is_watertight else "KONTROL ET")


if __name__ == "__main__":
    main()
