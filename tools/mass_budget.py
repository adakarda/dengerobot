"""Robot govdesinin kutle butcesi: kutle merkezi yuksekligi ve ataleti (teker ekseni z=0).
Parca agirliklari tahmindir (OLC): parca gelince terazide tartip guncelleyin."""
# (ad, kutle kg, z m (eksenden yukseklik), x m (one +), boyut z m (atalet icin))
PARTS = [
    ("2x JGB37-520 motor + braket", 0.380, 0.000, 0.0, 0.037),
    ("Kat 1 pleksi 150x110x3",      0.060, 0.024, 0.0, 0.003),
    ("2x BTS7960",                  0.130, 0.045, 0.0, 0.035),
    ("LM2596 + sigorta + 2 WAGO",   0.060, 0.035, 0.0, 0.020),
    ("MPU6050 (kat 1 ustu, ortada)", 0.005, 0.030, 0.0, 0.003),
    ("Kat 2 pleksi",                0.060, 0.104, 0.0, 0.003),
    ("3x18650 + yuva + BMS",        0.190, 0.120, 0.0, 0.022),
    ("Ana kart + ESP32",            0.045, 0.115, 0.0, 0.015),
    ("IR gozleri + V-yuva + pimler", 0.035, 0.090, 0.05, 0.060),
    ("Kat 3 pleksi",                0.060, 0.184, 0.0, 0.003),
    ("Acil stop",                   0.070, 0.205, 0.0, 0.040),
    ("Kutu yuvasi",                 0.030, 0.195, 0.0, 0.020),
    ("16x distans + vida + kablo",  0.120, 0.100, 0.0, 0.160),
]
BOX = ("Ilac kutusu", 0.060, 0.215)
m = sum(p[1] for p in PARTS)
l = sum(p[1] * p[2] for p in PARTS) / m
I = sum(p[1] * ((p[2] - l) ** 2 + (p[4] ** 2 + 0.11 ** 2) / 12) for p in PARTS)
if __name__ == "__main__":
    for p in PARTS:
        print(f"{p[0]:32s} {p[1]*1000:5.0f} g  z={p[2]*1000:4.0f} mm")
    print(f"govde (kutusuz): {m:.3f} kg, KM eksenin {l*1000:.0f} mm ustunde, I={I:.4f} kg m^2")
    mt = m + BOX[1]; lt = (m * l + BOX[1] * BOX[2]) / mt
    print(f"kutulu: {mt:.3f} kg, KM {lt*1000:.0f} mm")
