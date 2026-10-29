"""Denge robotu 3B baski parcalari ve montaj kontrolu.
Calistir: python cad/robot_cad.py
Uretir: cad/stl/*.stl (baski yonunde), cad/montaj.glb, cad/kontrol.md, docs/img/cad_*.png
Olculer cad/olcu.py'de. Kontrol: parcalar ve moduller birbirine girmiyor mu, zemin, direk, pim yukseklikleri."""
import itertools
import json
import math
import pathlib
import sys

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import olcu as o  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "cad"
SEG = 48


# ---------------- temel cisimler ----------------
def kutu(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def kutu_m(cx, cy, sx, sy, z0, z1):
    return kutu(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0, z1)


def sil_z(cx, cy, r, z0, z1, seg=SEG):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate([cx, cy, z0])


def sil_y(cx, cz, r, y0, y1, seg=SEG):
    return Manifold.cylinder(y1 - y0, r, r, seg).rotate([-90, 0, 0]).translate([cx, y0, cz])


def sil_x(cy, cz, r, x0, x1, seg=SEG):
    return Manifold.cylinder(x1 - x0, r, r, seg).rotate([0, 90, 0]).translate([x0, cy, cz])


def ccw(pts):
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


def prizma_z(pts_xy, z0, z1):
    return CrossSection([ccw(pts_xy)]).extrude(z1 - z0).translate([0, 0, z0])


def prizma_x(pts_yz, x0, x1):
    """(y, z) cokgeni X boyunca uzat."""
    m = CrossSection([ccw(pts_yz)]).extrude(x1 - x0)
    return m.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])


def prizma_y(pts_xz, y0, y1):
    """(x, z) cokgeni Y boyunca uzat."""
    m = CrossSection([ccw(pts_xz)]).extrude(y1 - y0)
    return m.rotate([90, 0, 0]).translate([0, y1, 0])  # (a, b, c) -> (a, -c, b)


def birlesim(parcalar):
    parcalar = [p for p in parcalar if p is not None]
    return Manifold.batch_boolean(parcalar, __import__("manifold3d").OpType.Add) if parcalar else Manifold()


def altigen_z(cx, cy, aa, z0, z1):
    return sil_z(cx, cy, aa / math.sqrt(3), z0, z1, seg=6)


def yuvarlak_levha(sx, sy, r, z0, t):
    c = [CrossSection.circle(r, SEG).translate([sgx * (sx / 2 - r), sgy * (sy / 2 - r)])
         for sgx in (-1, 1) for sgy in (-1, 1)]
    return CrossSection.batch_hull(c).extrude(t).translate([0, 0, z0])


# ---------------- yuva (modul cebi) ----------------
def yuva(cx, cy, ix, iy, z0, h=3.0, kelepce="x", kose=7.0):
    """Ic olcusu ix*iy olan modul icin dort kose L duvari (kablolar kenarlardan rahat cikar) ve
    kablo bagi delikleri. kelepce='x': bag X yonunde sarar (delikler -x/+x tarafinda)."""
    d = o.DUVAR
    ex, ey = ix / 2, iy / 2
    ekle = []
    for sx, sy in itertools.product((-1, 1), (-1, 1)):
        x_out, y_out = cx + sx * (ex + d / 2), cy + sy * (ey + d / 2)
        kx = min(kose, ix / 2)
        ky = min(kose, iy / 2)
        ekle.append(kutu_m(x_out, cy + sy * (ey + d - ky / 2 - d / 2), d, ky + d, z0, z0 + h))
        ekle.append(kutu_m(cx + sx * (ex + d - kx / 2 - d / 2), y_out, kx + d, d, z0, z0 + h))
    kl, kg = o.KELEPCE
    cik = []
    if kelepce == "x":
        for sx in (-1, 1):
            cik.append(kutu_m(cx + sx * (ex + d + 1.5 + kg / 2), cy, kg, kl, z0 - 20, z0 + 1))
    elif kelepce == "y":
        for sy in (-1, 1):
            cik.append(kutu_m(cx, cy + sy * (ey + d + 1.5 + kg / 2), kl, kg, z0 - 20, z0 + 1))
    return ekle, cik


# ---------------- yerlesim ----------------
K1, K2, K3 = o.KAT1_Z, o.KAT2_Z, o.KAT3_Z
K1U, K2U, K3U = K1 + o.KAT_T, K2 + o.KAT_T, K3 + o.KAT_T
B = o.BOSLUK
Z_PIM_UST = o.PIM_UST_ZEMIN + o.ZEMIN
Z_PIM_ALT = o.PIM_ALT_ZEMIN + o.ZEMIN
Z_MIKNATIS = (sum(o.SERIT_ZEMIN) / 2) + o.ZEMIN
Z_GOZ = o.GOZ_ZEMIN + o.ZEMIN
SX = o.V_SERIT_ON_X          # serit on yuzu
SB = SX - 4.0                # serit arka yuzu = kat on kenari
KAT_ON = o.KAT_X / 2

YER = dict(
    bts=(-21.0, 38.0),
    lm=(18.4, 43.4), wago12=(42.75, 41.0), sigorta=(18.4, -43.4), wagogn=(42.75, -41.0),
    c5=(21.0, 0.0), mpu=(0.0, 0.0),
    anakart=(-28.0, 0.0), bms=(18.9, -32.8), xt60=(18.0, 22.0),
    pil=(-23.0, 0.0), acil=(28.0, -46.0), kutu=(16.0, o.KUTU_Y),
    goz=(39.0, o.GOZ_Y),
)
KAT1_PENCERE = (-48, -28, -13, 13)
KAT2_PENCERE = (30, 38, -58, -30)
ANAKART_DISTANS = 10.0   # ana kart kat 2'nin altina asili (M3 naylon distans), ESP32 asagi bakar
MOTOR_TAB_DELIK = [(-5.0, 70.0), (9.0, 70.0)]
V_ALT_VIDA = [(47.0, 14.0), (47.0, -14.0)]
V_UST_VIDA = [(44.0, 0.0), (51.0, 0.0)]


def kat_temel(z0):
    p = yuvarlak_levha(o.KAT_X, o.KAT_Y, o.KAT_KOSE_R, z0, o.KAT_T)
    delik = [sil_z(sx * o.DISTANS_XY[0], sy * o.DISTANS_XY[1], o.VIDA_D / 2, z0 - 1, z0 + o.KAT_T + 1)
             for sx in (-1, 1) for sy in (-1, 1)]
    return p, delik


def kat1():
    p, cik = kat_temel(K1)
    ekle = []
    x0, x1, y0, y1 = KAT1_PENCERE
    cik.append(kutu(x0, x1, y0, y1, K1 - 1, K1U + 1))
    for sy in (1, -1):
        for x, y in MOTOR_TAB_DELIK:
            cik.append(sil_z(x, sy * y, o.VIDA_D / 2, K1 - 1, K1U + 1))
        # BTS7960: 4 ayak + pilot delik + kose duvarlari
        bx, by = YER["bts"][0], sy * YER["bts"][1]
        h = o.BTS_DELIK / 2
        for dx, dy in itertools.product((-h, h), (-h, h)):
            ekle.append(sil_z(bx + dx, by + dy, 4.0, K1U, K1U + o.BTS_AYAK))
            cik.append(sil_z(bx + dx, by + dy, o.KILAVUZ_D / 2, K1U - 2, K1U + o.BTS_AYAK + 1))
        e, c = yuva(bx, by, o.BTS[0] + 2 * B, o.BTS[1] + 2 * B, K1U, h=o.BTS_AYAK + 3, kelepce=None)
        ekle += e
    # on bant
    for ad, (ix, iy), kel in (("lm", (o.LM2596[1], o.LM2596[0]), "x"), ("wago12", (o.WAGO[1], o.WAGO[0]), "x"),
                              ("sigorta", (o.SIGORTA[1], o.SIGORTA[0]), "x"), ("wagogn", (o.WAGO[1], o.WAGO[0]), "x")):
        cx, cy = YER[ad]
        e, c = yuva(cx, cy, ix + 2 * B, iy + 2 * B, K1U, h=3.0, kelepce=kel)
        ekle += e
        cik += c
    # MPU6050: kose duvarlari, kopuk bantla yapisir; eksenleri robotla hizali tutar
    e, c = yuva(*YER["mpu"], o.MPU[0] + 2 * B, o.MPU[1] + 2 * B, K1U, h=2.5, kelepce="y", kose=5)
    ekle += e
    cik += c
    # C5 beşik
    cx, _ = YER["c5"]
    eks = K1U + o.C5[0] / 2 + 0.5
    for sy in (-1, 1):
        ekle.append(kutu_m(cx, sy * 8.0, 15.0, 4.0, K1U, eks))
    cik.append(sil_y(cx, eks, o.C5[0] / 2 + B, -20, 20))
    for sx in (-1, 1):
        cik.append(kutu_m(cx + sx * 9.5, 0, o.KELEPCE[1], o.KELEPCE[0], K1 - 1, K1U + 1))
    for x, y in V_ALT_VIDA:
        cik.append(sil_z(x, y, o.VIDA_D / 2, K1 - 1, K1U + 1))
    return (p + birlesim(ekle)) - birlesim(cik)


def goz_tutucu(sag):
    """Tek IR goz tutucu (yerel: x ileri, pencere x=0..TUP_L; arka cep x<0)."""
    w, h = o.GOZ_PENCERE
    zc = Z_GOZ
    d = o.DUVAR
    tup = kutu(0, o.GOZ_TUP_L, -w / 2 - d, w / 2 + d, K2U, zc + h / 2 + d) - kutu(-1, o.GOZ_TUP_L + 1, -w / 2, w / 2, zc - h / 2, zc + h / 2)
    cep_ic = (8.4, 16.0)
    arka = kutu(-cep_ic[0] - d, 0, -cep_ic[1] / 2 - d, cep_ic[1] / 2 + d, K2U, K2U + 14) - \
        kutu(-cep_ic[0], 0.01, -cep_ic[1] / 2, cep_ic[1] / 2, K2U + 0.8, K2U + 20)
    # bag deligi (arka duvardan, modul kartini sarar)
    arka = arka - kutu(-cep_ic[0] - d - 1, -cep_ic[0] + 1, -2, 2, K2U + 6, K2U + 8.2)
    g = tup + arka
    a = -o.GOZ_ACI if sag else o.GOZ_ACI
    x, y = YER["goz"]
    return g.rotate([0, 0, a]).translate([x, -y if sag else y, 0])


def kat2():
    p, cik = kat_temel(K2)
    ekle = []
    x0, x1, y0, y1 = KAT2_PENCERE
    cik.append(kutu(x0, x1, y0, y1, K2 - 1, K2U + 1))
    # ana kart altta asili: 4 distans deligi
    ax, ay = YER["anakart"]
    for dx, dy in itertools.product((-1, 1), (-1, 1)):
        x, y = ax + dx * o.ANAKART_DELIK[1] / 2, ay + dy * o.ANAKART_DELIK[0] / 2
        cik.append(sil_z(x, y, o.VIDA_D / 2, K2 - 1, K2U + 1))
    # 3x18650 yuvasi ustte: kose duvarlari + orta hatta iki vida kanali (yuvanin taban deligi icin, somun altta)
    px, py = YER["pil"]
    e, c = yuva(px, py, o.PIL[1] + 2 * B, o.PIL[0] + 2 * B, K2U, h=4.0, kelepce=None, kose=10)
    ekle += e
    for sy in (-1, 1):
        cik.append(kutu(px - o.VIDA_D / 2, px + o.VIDA_D / 2, *sorted((sy * 8, sy * 32)), K2 - 1, K2U + 1))
    e, c = yuva(*YER["bms"], o.BMS[1] + 2 * B, o.BMS[0] + 2 * B, K2U, h=3.0, kelepce="x")
    ekle += e
    cik += c
    e, c = yuva(*YER["xt60"], o.XT60[0] + 2 * B, o.XT60[1] + 2 * B, K2U, h=4.0, kelepce="x", kose=5)
    ekle += e
    cik += c
    for x, y in V_UST_VIDA:
        cik.append(sil_z(x, y, o.VIDA_D / 2, K2 - 1, K2U + 1))
    p = (p + birlesim(ekle)) - birlesim(cik)
    return p + goz_tutucu(False) + goz_tutucu(True)


def kat3():
    p, cik = kat_temel(K3)
    ax, ay = YER["acil"]
    r = o.ACIL_DELIK / 2
    cik.append(sil_z(ax, ay, r, K3 - 1, K3U + 1, seg=72))
    cik.append(kutu(ax + r - 1, ax + r + 2.0, ay - 1.6, ay + 1.6, K3 - 1, K3U + 1))   # donme kilidi
    cik.append(sil_z(ax - 25, ay, 5.0, K3 - 1, K3U + 1))                              # acil stop kablolari
    kx, ky = YER["kutu"]
    ix, iy = o.KUTU[0] + 2 * o.KUTU_PAY, o.KUTU[1] + 2 * o.KUTU_PAY
    t, h = o.KUTU_DUVAR
    cep = kutu_m(kx, ky, ix + 2 * t, iy + 2 * t, K3U, K3U + h) - kutu_m(kx, ky, ix, iy, K3U, K3U + h + 1)
    for sx in (-1, 1):  # parmak oyuklari
        cep = cep - kutu_m(kx + sx * (ix / 2 + t / 2), ky, t + 2, 22, K3U + h - 12, K3U + h + 1)
    return (p + cep) - birlesim(cik)


def motor_tutucu(sol=True):
    y0 = o.MOTOR_YUZ_Y
    y1 = y0 + o.TUTUCU_T
    zm = -o.MOTOR_MIL_KACIK
    xa, xb = -14.0, 20.0
    plaka = sil_y(0, zm, 21.0, y0, y1) + kutu(xa, xb, y0, y1, zm, K1 - 5)
    tab = kutu(xa, xb, 52.0, y1, K1 - 5, K1)
    gus = [prizma_x([(y0, K1 - 5), (57.0, K1 - 5), (y0, K1 - 13)], x, x + 4) for x in (xa, xb - 4)]
    m = plaka + tab + birlesim(gus)
    cik = [sil_y(0, 0, o.MOTOR_BURC_D / 2, y0 - 1, y1 + 1)]
    for k in range(6):
        a = math.radians(o.MOTOR_DELIK_ACI0 + 60 * k)
        x, z = o.MOTOR_DELIK_PCD / 2 * math.cos(a), zm + o.MOTOR_DELIK_PCD / 2 * math.sin(a)
        cik.append(sil_y(x, z, o.VIDA_D / 2, y0 - 1, y1 + 1, seg=24))
        cik.append(sil_y(x, z, 3.25, y1 - 2.5, y1 + 1, seg=24))
    for x, y in MOTOR_TAB_DELIK:
        cik.append(sil_z(x, y, o.VIDA_D / 2, K1 - 6, K1 + 1, seg=24))
        cik.append(altigen_z(x, y, o.SOMUN_AA, K1 - 6, K1 - 5 + 2.6))
    m = m - birlesim(cik)
    return m if sol else m.mirror([0, 1, 0])


def v_yuva():
    s = kutu(SB, SX, -o.V_SERIT_Y / 2, o.V_SERIT_Y / 2, K1U, K2)
    kan = []
    c = math.cos(math.radians(45))
    L, t = o.V_KANAT_L, o.V_KANAT_T
    for sy in (1, -1):
        p0 = (SX, o.V_SERIT_Y / 2)
        p1 = (SX + L * c, o.V_SERIT_Y / 2 + L * c)
        p2 = (p1[0] - t * c, p1[1] + t * c)
        p3 = (p0[0] - t * c, p0[1] + t * c)
        pts = [p0, p1, p2, p3, (SB, p3[1]), (SB, p0[1])]
        pts = [(x, sy * y) for x, y in pts]
        kan.append(prizma_z(pts, K1U, K2))
    alt = kutu(SB - 14, SB, -o.V_SERIT_Y, o.V_SERIT_Y, K1U, K1U + 4)
    ust = prizma_y([(SB - 14, K2), (SB, K2), (SB, K2 - 18), (SB - 14, K2 - 4)], -o.V_SERIT_Y, o.V_SERIT_Y)
    pim_ayak = [sil_x(0, z, 5.0, SB - 8, SB) for z in (Z_PIM_UST, Z_PIM_ALT)]
    mik_ayak = sil_x(0, Z_MIKNATIS, 7.0, SX - 7.0, SB)
    m = s + birlesim(kan) + alt + ust + birlesim(pim_ayak) + mik_ayak
    cik = [sil_x(0, z, o.POGO_D / 2 + 0.1, SB - 10, SX + 1, seg=32) for z in (Z_PIM_UST, Z_PIM_ALT)]
    cik.append(sil_x(0, Z_MIKNATIS, o.MIKNATIS[0] / 2 + 0.15, SX - 7.0 - 1, SX - 0.8, seg=48))
    for x, y in V_ALT_VIDA:
        cik.append(sil_z(x, y, o.KILAVUZ_D / 2, K1U - 1, K1U + 3.5, seg=24))
    for x, y in V_UST_VIDA:
        cik.append(sil_z(x, y, o.KILAVUZ_D / 2, K2 - 12, K2 + 1, seg=24))
    return m - birlesim(cik)


# ---------------- satin alinan parcalar (zarf) ----------------
def bilesenler():
    b = {}
    for sy, ad in ((1, "sol"), (-1, "sag")):
        y = o.MOTOR_YUZ_Y
        zm = -o.MOTOR_MIL_KACIK
        mot = sil_y(0, zm, o.MOTOR_SANZ_D / 2, y - o.MOTOR_SANZ_L, y) + \
            sil_y(0, zm, o.MOTOR_GOVDE_D / 2, y - o.MOTOR_SANZ_L - o.MOTOR_GOVDE_L, y - o.MOTOR_SANZ_L) + \
            sil_y(0, 0, o.MOTOR_MIL_D / 2, y, y + o.TUTUCU_T + 2) + sil_y(0, 0, 6.0, y, y + 3)
        tek = sil_y(0, 0, o.R_TEKER, o.IZ / 2 - o.TEKER_EN / 2, o.IZ / 2 + o.TEKER_EN / 2, seg=72)
        if sy < 0:
            mot, tek = mot.mirror([0, 1, 0]), tek.mirror([0, 1, 0])
        b[f"motor {ad}"] = mot
        b[f"teker {ad}"] = tek
        bx, by = YER["bts"][0], sy * YER["bts"][1]
        b[f"BTS7960 {ad}"] = kutu_m(bx, by, o.BTS[0], o.BTS[1], K1U + o.BTS_AYAK, K1U + o.BTS_AYAK + o.BTS[2])
    b["MPU6050"] = kutu_m(*YER["mpu"], o.MPU[0], o.MPU[1], K1U + 1, K1U + 1 + o.MPU[2])
    b["LM2596"] = kutu_m(*YER["lm"], o.LM2596[1], o.LM2596[0], K1U, K1U + o.LM2596[2])
    b["sigorta"] = kutu_m(*YER["sigorta"], o.SIGORTA[1], o.SIGORTA[0], K1U, K1U + o.SIGORTA[2])
    b["WAGO-12V"] = kutu_m(*YER["wago12"], o.WAGO[1], o.WAGO[0], K1U, K1U + o.WAGO[2])
    b["WAGO-GND"] = kutu_m(*YER["wagogn"], o.WAGO[1], o.WAGO[0], K1U, K1U + o.WAGO[2])
    b["C5 1000uF"] = sil_y(YER["c5"][0], K1U + o.C5[0] / 2 + 0.5, o.C5[0] / 2, -o.C5[1] / 2, o.C5[1] / 2)
    for z, ad in ((Z_PIM_UST, "+"), (Z_PIM_ALT, "-")):
        b[f"pogo {ad}"] = sil_x(0, z, o.POGO_D / 2, SX + o.POGO_CIKIS - o.POGO_L, SX + o.POGO_CIKIS, seg=32)
    b["miknatis x2"] = sil_x(0, Z_MIKNATIS, o.MIKNATIS[0] / 2, SX - 0.8 - 2 * o.MIKNATIS[1], SX - 0.8)
    px, py = YER["pil"]
    b["3x18650 yuva"] = kutu_m(px, py, o.PIL[1], o.PIL[0], K2U, K2U + o.PIL[2])
    ax, ay = YER["anakart"]
    za = K2 - ANAKART_DISTANS
    b["ana kart"] = kutu_m(ax, ay, o.ANAKART[1], o.ANAKART[0], za - o.ANAKART[2], za)
    b["ESP32 (soketli)"] = kutu_m(ax, ay, 28.0, 52.0, za - o.ANAKART[2] - o.ANAKART_YUK, za - o.ANAKART[2])
    for dx, dy in itertools.product((-1, 1), (-1, 1)):
        b[f"ana kart distansi {dx:+d}{dy:+d}"] = altigen_z(ax + dx * o.ANAKART_DELIK[1] / 2, ay + dy * o.ANAKART_DELIK[0] / 2, o.DISTANS_AA, za, K2)
    b["BMS"] = kutu_m(*YER["bms"], o.BMS[1], o.BMS[0], K2U, K2U + o.BMS[2])
    b["XT60"] = kutu_m(*YER["xt60"], o.XT60[0], o.XT60[1], K2U, K2U + o.XT60[2])
    for sag in (False, True):
        a = math.radians(-o.GOZ_ACI if sag else o.GOZ_ACI)
        gx, gy = YER["goz"][0], (-1 if sag else 1) * YER["goz"][1]
        bas = kutu(-5.6, -0.05, -3.2, 3.2, Z_GOZ - 3.7, Z_GOZ + 3.5).rotate([0, 0, math.degrees(a)]).translate([gx, gy, 0])
        b[f"IR goz {'sag' if sag else 'sol'}"] = bas
    cx, cy = YER["acil"]
    b["acil stop"] = sil_z(cx, cy, 15.0, K3U, K3U + 8) + sil_z(cx, cy, o.ACIL_MANTAR[0] / 2, K3U + 8, K3U + o.ACIL_MANTAR[1]) + \
        kutu_m(cx, cy, o.ACIL_GOVDE[0], o.ACIL_GOVDE[1], K3 - o.ACIL_GOVDE[2], K3)
    kx, ky = YER["kutu"]
    b["ilac kutusu"] = kutu_m(kx, ky, o.KUTU[0], o.KUTU[1], K3U, K3U + o.KUTU[2])
    for sx, sy in itertools.product((-1, 1), (-1, 1)):
        x, y = sx * o.DISTANS_XY[0], sy * o.DISTANS_XY[1]
        b[f"distans {'+' if sx > 0 else '-'}{'+' if sy > 0 else '-'}"] = \
            altigen_z(x, y, o.DISTANS_AA, K1U, K2) + altigen_z(x, y, o.DISTANS_AA, K2U, K3)
    return b


# ---------------- kontroller ----------------
def tepe(m):
    mesh = m.to_mesh()
    return np.asarray(mesh.vert_properties)[:, :3]


def kontrol(basili, bil):
    satir = []
    ok_hepsi = True

    def ekle(ad, ok, detay):
        nonlocal ok_hepsi
        ok_hepsi &= ok
        satir.append((ad, "GECTI" if ok else "KALDI", detay))

    hepsi = {**{f"[baski] {k}": v for k, v in basili.items()}, **bil}
    adlar = list(hepsi)
    cakis = []
    for a, b_ in itertools.combinations(adlar, 2):
        if (a.startswith("motor") and b_.startswith("teker")) or (b_.startswith("motor") and a.startswith("teker")):
            continue  # mil teker gobegine girer
        v = (hepsi[a] ^ hepsi[b_]).volume()
        if v > 0.5:
            cakis.append((a, b_, v))
    ekle("Carpisma (tum parcalar ikili)", not cakis,
         f"{len(adlar)} parca, {len(adlar)*(len(adlar)-1)//2} cift; " +
         ("hic biri birbirine girmiyor" if not cakis else "; ".join(f"{a} x {b_}: {v:.0f} mm3" for a, b_, v in cakis)))

    # zemin: teker disindaki her nokta +-30 derece egimde zeminden en az 3 mm yukarida
    en_dusuk = 1e9
    hangi = ""
    for ad, m in hepsi.items():
        if ad.startswith("teker"):
            continue
        v = tepe(m)
        for th in np.radians(np.arange(-30, 31, 2)):
            z = v[:, 2] * math.cos(th) + v[:, 0] * math.sin(th)
            if z.min() < en_dusuk:
                en_dusuk, hangi = z.min(), ad
    ekle("Zemin payi (+-30 derece egim)", en_dusuk - o.ZEMIN >= 3.0,
         f"en alcak nokta zeminden {en_dusuk - o.ZEMIN:.1f} mm ({hangi})")

    # direk: yanasmis konumda direk seride degiyor, pimler 3 mm basiliyor, baska hicbir sey degmiyor
    direk = sil_z(SX + o.DIREK_D / 2, 0, o.DIREK_D / 2, o.ZEMIN, o.ZEMIN + 200, seg=96)
    deg = []
    for ad, m in hepsi.items():
        v = (m ^ direk).volume()
        if v > 0.05 and not ad.startswith("pogo"):
            deg.append(f"{ad} {v:.1f} mm3")
    pim = [(bil[f"pogo {s}"] ^ direk).volume() for s in "+-"]
    ekle("Direk yanasmasi (O40, seride temas)", not deg and all(p > 1 for p in pim),
         ("yalniz pogo pimler direge giriyor (yay payi " + f"{o.POGO_CIKIS:.0f} mm)") if not deg else "; ".join(deg))

    # kanat ile direk arasi en kucuk bosluk
    kan_bosluk = []
    c = math.cos(math.radians(45))
    for sy in (1, -1):
        p0 = np.array([SX, sy * o.V_SERIT_Y / 2])
        d = np.array([c, sy * c])
        q = np.array([SX + o.DIREK_D / 2, 0.0]) - p0
        kan_bosluk.append(abs(q[0] * d[1] - q[1] * d[0]) - o.DIREK_D / 2)
    ekle("V kanatlari direge degmiyor", min(kan_bosluk) > 0.5, f"kanat ic yuzu ile direk arasi {min(kan_bosluk):.1f} mm")

    # yukseklikler
    zp = [Z_PIM_UST - o.ZEMIN, Z_PIM_ALT - o.ZEMIN, Z_GOZ - o.ZEMIN, Z_MIKNATIS - o.ZEMIN]
    ekle("Pim, miknatis ve goz yukseklikleri", abs(zp[0] - 102) < 0.1 and abs(zp[1] - 77) < 0.1 and abs(zp[2] - 147) < 0.1,
         f"+ pim {zp[0]:.1f}, - pim {zp[1]:.1f}, miknatis {zp[3]:.1f} (celik serit 85-94), IR goz {zp[2]:.1f} mm (zeminden)")

    # IR gozleri direge bakiyor mu (30 cm onde), gorus hatti engelsiz mi
    engel = []
    for sag in (False, True):
        a = math.radians(-o.GOZ_ACI if sag else o.GOZ_ACI)
        gx, gy = YER["goz"][0], (-1 if sag else 1) * YER["goz"][1]
        for dx in np.linspace(0, 250, 60)[1:]:
            p = (gx + dx * math.cos(a), gy + dx * math.sin(a), Z_GOZ)
            for ad, m in hepsi.items():
                if ad.startswith("IR goz") or ad.startswith("[baski] kat2"):
                    continue
                bb = m.bounding_box()
                if bb[0] <= p[0] <= bb[3] and bb[1] <= p[1] <= bb[4] and bb[2] <= p[2] <= bb[5]:
                    if (m ^ kutu_m(p[0], p[1], 0.5, 0.5, p[2] - 0.25, p[2] + 0.25)).volume() > 0:
                        engel.append(ad)
    ekle("IR gorus hatti", not engel, "iki gozun onu 25 cm acik" if not engel else ", ".join(sorted(set(engel))))

    # MPU merkezde mi
    mx, my = YER["mpu"]
    ekle("MPU6050 teker ekseni ustunde, ortada", abs(mx) < 1 and abs(my) < 1, f"x={mx:.0f}, y={my:.0f} mm, z={K1U+1:.0f} mm")

    # kutle butcesi (tools/mass_budget.py) parca konumlari 3B modelle ayni mi (LQR ve ikiz bunu kullanir)
    sys.path.insert(0, str(ROOT / "tools"))
    import mass_budget as mb
    esle = {"2x BTS7960": ["BTS7960 sol"], "3x18650 + yuva + BMS": ["3x18650 yuva"], "Kat 3 baski": None,
            "Ana kart + ESP32": ["ana kart", "ESP32 (soketli)"], "MPU6050 (kat 1 ustu, ortada)": ["MPU6050"]}
    fark = []
    for ad, z, x in ((p[0], p[2], p[3]) for p in mb.PARTS):
        if ad not in esle or esle[ad] is None:
            continue
        ms = [bil[k] for k in esle[ad]]
        hac = sum(m.volume() for m in ms)
        cz = sum(tri(m).center_mass[2] * m.volume() for m in ms) / hac
        cx = sum(tri(m).center_mass[0] * m.volume() for m in ms) / hac
        fark.append((ad, cz - z * 1000, cx - x * 1000))
    kz = (K3 + K3U) / 2
    fark.append(("Kat 3 baski", kz - [p[2] for p in mb.PARTS if p[0] == "Kat 3 baski"][0] * 1000, 0.0))
    fark.append(("Ilac kutusu", tri(bil["ilac kutusu"]).center_mass[2] - mb.BOX[2] * 1000, 0.0))
    for ad, yx in (("Acil stop", YER["acil"][0]), ("Kutu yuvasi", YER["kutu"][0])):
        fark.append((ad, 0.0, yx - [p[3] for p in mb.PARTS if p[0] == ad][0] * 1000))
    en = max(max(abs(a_), abs(b_)) for _, a_, b_ in fark)
    ekle("Kutle butcesi 3B modelle uyumlu", en < 10.0,
         f"en buyuk fark {en:.1f} mm (" + ", ".join(f"{a_}: dz {z_:+.0f}" for a_, z_, _ in fark) + ")")

    xkm = sum(p[1] * p[3] for p in mb.PARTS) + mb.BOX[1] * YER["kutu"][0] / 1000
    mt = sum(p[1] for p in mb.PARTS) + mb.BOX[1]
    ekle("Kutle merkezi teker ekseni ustunde (x)", abs(xkm / mt * 1000) < 1.0,
         f"x = {xkm / mt * 1000:+.1f} mm (one +); robot dik dururken dengede")

    # baski hacmi
    buyuk = []
    for ad, m in basili.items():
        bb = m.bounding_box()
        s = sorted([bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]])
        if s[2] > 180 or s[1] > 180:
            buyuk.append(ad)
    ekle("Baski tablasina sigma (180x180)", not buyuk, "hepsi sigiyor" if not buyuk else ", ".join(buyuk))
    return ok_hepsi, satir


# ---------------- disari aktarma ----------------
BASKI_YONU = {
    "kat1": lambda m: m,
    "kat2": lambda m: m,
    "kat3": lambda m: m,
    "motor_tutucu_sol": lambda m: m.rotate([-90, 0, 0]),     # dis yuz (teker tarafi) tablada
    "motor_tutucu_sag": lambda m: m.rotate([90, 0, 0]),
    "v_yuva": lambda m: m,
}


def tri(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def main():
    (OUT / "stl").mkdir(parents=True, exist_ok=True)
    basili = {
        "kat1": kat1(), "kat2": kat2(), "kat3": kat3(),
        "motor_tutucu_sol": motor_tutucu(True), "motor_tutucu_sag": motor_tutucu(False),
        "v_yuva": v_yuva(),
    }
    bil = bilesenler()
    bilgi = {}
    for ad, m in basili.items():
        assert m.status().name == "NoError", (ad, m.status())
        p = BASKI_YONU[ad](m)
        bb = p.bounding_box()
        p = p.translate([-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]])
        t = tri(p)
        assert t.is_watertight, ad
        t.export(OUT / "stl" / f"{ad}.stl")
        bb = p.bounding_box()
        hacim = m.volume() / 1000.0
        bilgi[ad] = dict(hacim_cm3=round(hacim, 1), kutle_g=round(hacim * 1.24 * 0.6, 0),
                         boyut_mm=[round(bb[3] - bb[0], 1), round(bb[4] - bb[1], 1), round(bb[5] - bb[2], 1)])
    ok, satir = kontrol(basili, bil)

    # montaj GLB (renkli)
    sahne = trimesh.Scene()
    renk_b = {"kat1": (230, 230, 235), "kat2": (230, 230, 235), "kat3": (230, 230, 235),
              "motor_tutucu_sol": (255, 160, 60), "motor_tutucu_sag": (255, 160, 60), "v_yuva": (60, 110, 230)}
    for ad, m in basili.items():
        t = tri(m)
        t.visual.face_colors = (*renk_b[ad], 255)
        sahne.add_geometry(t, node_name=f"baski_{ad}", geom_name=f"baski_{ad}")
    for ad, m in bil.items():
        t = tri(m)
        c = (60, 60, 60) if ad.startswith(("teker", "motor")) else (40, 140, 70) if ad.startswith(("BTS", "ana", "ESP", "MPU", "LM", "BMS", "IR")) \
            else (200, 40, 40) if ad.startswith(("acil", "ilac")) else (180, 150, 60) if ad.startswith(("pogo", "distans", "miknatis")) else (120, 120, 140)
        t.visual.face_colors = (*c, 255)
        sahne.add_geometry(t, node_name=ad, geom_name=ad)
    sahne.export(OUT / "montaj.glb")

    # kutle merkezi icin basili parcalarin katkisi
    km = {ad: [round(float(x), 1) for x in tri(m).center_mass] for ad, m in basili.items()}
    (OUT / "parcalar.json").write_text(json.dumps(dict(parca=bilgi, km_mm=km), indent=1), encoding="utf-8")

    with open(OUT / "kontrol.md", "w", encoding="utf-8") as f:
        f.write("# 3B montaj kontrolu\n\n`python cad/robot_cad.py` uretir.\n\n| Kontrol | Sonuc | Ayrinti |\n|---|---|---|\n")
        for a, s, d in satir:
            f.write(f"| {a} | {s} | {d} |\n")
        f.write("\n| Parca | Boyut (mm, baski yonu) | Hacim cm3 | Kutle g (%60 dolu PLA) |\n|---|---|---|---|\n")
        for ad, i in bilgi.items():
            f.write(f"| {ad} | {' x '.join(str(v) for v in i['boyut_mm'])} | {i['hacim_cm3']} | {i['kutle_g']:.0f} |\n")
    for a, s, d in satir:
        print(f"{s:6s} {a}: {d}")
    for ad, i in bilgi.items():
        print(f"{ad:18s} {i['boyut_mm']} {i['kutle_g']:.0f} g")
    print("TUMU GECTI" if ok else "KALAN VAR")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
