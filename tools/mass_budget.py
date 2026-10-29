"""Robot govdesinin kutle butcesi: kutle merkezi yuksekligi ve ataleti (teker ekseni z=0).
Parca agirliklari tahmindir (OLC): parca gelince terazide tartip guncelleyin."""
# (ad, kutle kg, z m (eksenden yukseklik), x m (one +), boyut z m (atalet icin))
# Konumlar 3B modelden (cad/robot_cad.py YER ve kat yukseklikleri). Pil kat 2'nin ustunde, ana kart kat 2'nin altinda asili.
PARTS = [
    ("2x JGB37-520 motor + tutucu", 0.380, -0.006, 0.0, 0.037),
    ("Kat 1 baski 150x110x4",       0.060, 0.024, 0.0, 0.004),
    ("2x BTS7960",                  0.130, 0.0485, -0.021, 0.035),
    ("LM2596 + sigorta + 2 WAGO",   0.060, 0.033, 0.03, 0.020),
    ("MPU6050 (kat 1 ustu, ortada)", 0.005, 0.0285, 0.0, 0.003),
    ("Kat 2 baski",                 0.060, 0.108, 0.0, 0.004),
    ("3x18650 + yuva + BMS",        0.190, 0.1205, -0.017, 0.022),
    ("Ana kart + ESP32",            0.045, 0.087, -0.028, 0.015),
    ("IR gozleri + V-yuva + pimler", 0.035, 0.070, 0.055, 0.080),
    ("Kat 3 baski",                 0.060, 0.192, 0.0, 0.004),
    ("Acil stop",                   0.070, 0.195, 0.028, 0.060),
    ("Kutu yuvasi",                 0.030, 0.205, 0.016, 0.025),
    ("16x distans + vida + kablo",  0.120, 0.106, 0.0, 0.160),
]
BOX = ("Ilac kutusu", 0.060, 0.2065)  # cep merkezi x=+16 mm, y=+27 mm (cad/robot_cad.py)
m = sum(p[1] for p in PARTS)
l = sum(p[1] * p[2] for p in PARTS) / m
I = sum(p[1] * ((p[2] - l) ** 2 + (p[4] ** 2 + 0.11 ** 2) / 12) for p in PARTS)
if __name__ == "__main__":
    for p in PARTS:
        print(f"{p[0]:32s} {p[1]*1000:5.0f} g  z={p[2]*1000:4.0f} mm")
    print(f"govde (kutusuz): {m:.3f} kg, KM eksenin {l*1000:.0f} mm ustunde, I={I:.4f} kg m^2")
    mt = m + BOX[1]; lt = (m * l + BOX[1] * BOX[2]) / mt
    print(f"kutulu: {mt:.3f} kg, KM {lt*1000:.0f} mm")
