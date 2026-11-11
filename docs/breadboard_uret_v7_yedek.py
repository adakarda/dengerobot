"""Breadboard sema sayfasi uretici (TEK tam boy breadboard, tum parcalar kart uzerinde) -> docs/breadboard_sema.html
Calistir: python docs/breadboard_uret.py
Raylar: ust dis +3,3 V, ust ic GND, alt ic GND, alt dis +12 V. GND'ler 6 numarali kablo ile birlesir.
Varsayimlar (sayfada da yazili): TB6612 pin sirasi Pololu tipi, ESP32 38 pin pin satirlari b ve i (22,9 mm),
TB6612 satirlari d ve h, LM2596 mini pedleri 8 delik aralikli (c ve i satiri) ve 16 sutun arayla,
tam boy breadboard 830 delik (63 sutun x 10 satir + 4 ray x 50)."""
import html
import pathlib

P, X0 = 14, 64                                   # delik araligi (2,54 mm), 1. sutunun x'i
ROWS = {"a": 60, "b": 74, "c": 88, "d": 102, "e": 116, "f": 158, "g": 172, "h": 186, "i": 200, "j": 214}
RAILS = {"T+": 14, "T-": 28, "B-": 246, "B+": 260}          # ust dis, ust ic, alt ic, alt dis
STRIPE = {"T+": -8, "T-": 8, "B-": -8, "B+": 8}             # renkli serit: raya gore dis/ic yon
RNAME = {"T+": "+3,3 V", "T-": "GND", "B-": "GND", "B+": "+12 V"}
BH, BW, W = 276, 958, 1000
RCOLS = [3 + g * 6 + k for g in range(10) for k in range(5)]   # 10 grup x 5 = 50 delik / ray

# --- parcalarin sutunlari (cizim ve dogrulama ayni sabitleri kullanir) ---
C_ESP, C_TB, C_MPU = 44, 33, 4
K_P, K_M = 1, 3                  # klemens + ve - (h satiri)
F_A, F_B = 4, 6                  # sigorta bacaklari
SW_1, SW_C, SW_2 = 8, 10, 12     # anahtar bacaklari (orta = ortak)
LM_L, LM_R = 15, 31              # LM2596 ped sutunlari
CAP_P, CAP_M = 41, 43            # kondansator bacaklari (g satiri)
EXTRA_PINS = {(K_P, "h"): "K.+", (K_M, "h"): "K.-", (F_A, "h"): "F.A", (F_B, "h"): "F.B",
              (SW_1, "h"): "SW.1", (SW_C, "h"): "SW.C", (SW_2, "h"): "SW.2",
              (LM_L, "c"): "LM.IN-", (LM_R, "c"): "LM.OUT-", (LM_L, "i"): "LM.IN+", (LM_R, "i"): "LM.OUT+",
              (CAP_P, "g"): "CAP.+", (CAP_M, "g"): "CAP.-"}

ENDS = []   # (kablo no, sutun, satir) dogrulama icin kayit


def cx(c):
    return X0 + (c - 1) * P


def snap(c):
    return min(RCOLS, key=lambda r: (abs(r - c), r))


class Svg:
    def __init__(self, y0, bot, label):
        self.y0, self.h = y0, y0 + BH + bot
        self.o = [f'<svg viewBox="0 0 {W} {self.h}" role="img" aria-label="{label}" xmlns="http://www.w3.org/2000/svg">']

    def add(self, s):
        self.o.append(s)

    def hy(self, row):
        return self.y0 + (RAILS[row] if row in RAILS else ROWS[row])

    def board(self):
        y0 = self.y0
        self.add(f'<rect class="bb" x="4" y="{y0}" width="{BW}" height="{BH}" rx="12"/>')
        self.add(f'<rect class="gap" x="{X0-22}" y="{y0+ROWS["e"]+10}" width="{BW-70}" height="{ROWS["f"]-ROWS["e"]-20}" rx="3"/>')
        for rk in ("T+", "T-", "B-", "B+"):
            y = y0 + RAILS[rk]
            ys = y + STRIPE[rk]
            cls = "stp" if rk.endswith("+") else "stm"
            self.add(f'<line class="{cls}" x1="{cx(3)-10}" x2="{cx(61)+10}" y1="{ys}" y2="{ys}"/>')
            for c in RCOLS:
                self.add(f'<circle class="hole" cx="{cx(c)}" cy="{y}" r="2.3"/>')
            self.add(f'<text class="rlab" x="10" y="{y+3.5}">{RNAME[rk]}</text>')
        for r, ry in ROWS.items():
            for c in range(1, 64):
                self.add(f'<circle class="hole" cx="{cx(c)}" cy="{y0+ry}" r="2.3"/>')
            self.add(f'<text class="rowl" x="42" y="{y0+ry+3.5}" text-anchor="end">{r}</text>')
        for c in (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 63):
            self.add(f'<text class="coll" x="{cx(c)}" y="{y0+ROWS["e"]+30}" text-anchor="middle">{c}</text>')

    def tag(self, x, y, n, cat):
        self.add(f'<g class="tg t-{cat}"><circle cx="{x}" cy="{y}" r="8.5"/><text x="{x}" y="{y+3.6}" text-anchor="middle">{n}</text></g>')

    def line(self, x1, y1, x2, y2, cat, thick=False):
        self.add(f'<line class="w w-{cat}{" thick" if thick else ""}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')

    def dot(self, x, y, cat):
        self.add(f'<circle class="pl c-{cat}" cx="{x}" cy="{y}" r="3.4"/>')

    def stub(self, col, row, d, ln, n, cat, thick=False, text=None):
        """Delikten disari cikan kisa kablo + numarali etiket. d: up/down/left."""
        ENDS.append((n, col, row))
        x, y = cx(col), self.hy(row)
        if d == "up":
            x2, y2 = x, y - ln
        elif d == "down":
            x2, y2 = x, y + ln
        else:
            x2, y2 = x - ln, y
        self.line(x, y, x2, y2, cat, thick)
        self.dot(x, y, cat)
        self.tag(x2, y2, n, cat)
        if text:
            tx, ty, an = (x2 + 13, y2 + 4, "start") if d != "left" else (x2 - 13, y2 + 4, "end")
            self.add(f'<text class="note" x="{tx}" y="{ty}" text-anchor="{an}">{text}</text>')

    def rail(self, col, row, rail, n, cat, rcol=None, thick=False, tagpos=0.5):
        """Delikten raya kisa kablo."""
        rc = snap(col) if rcol is None else rcol
        ENDS.append((n, col, row)); ENDS.append((n, rc, rail))
        x1, y1, x2, y2 = cx(col), self.hy(row), cx(rc), self.hy(rail)
        self.line(x1, y1, x2, y2, cat, thick)
        self.dot(x1, y1, cat)
        self.dot(x2, y2, cat)
        self.tag(x1 + (x2 - x1) * tagpos, y1 + (y2 - y1) * tagpos, n, cat)

    def hwire(self, c1, c2, row, n, cat, thick=False):
        """Ayni satirda iki sutun arasi yatay kablo."""
        ENDS.append((n, c1, row)); ENDS.append((n, c2, row))
        x1, x2, y = cx(c1), cx(c2), self.hy(row)
        self.line(x1, y, x2, y, cat, thick)
        self.dot(x1, y, cat); self.dot(x2, y, cat)
        self.tag((x1 + x2) / 2, y, n, cat)

    def on_rail(self, rcol, rail, n, cat):
        ENDS.append((n, rcol, rail))
        x, y = cx(rcol), self.hy(rail)
        self.dot(x, y, cat)
        self.tag(x, y, n, cat)

    def pins(self, c0, names, row, inward, cls):
        """Modul pin etiketleri (dikey yazi, govdenin icine dogru)."""
        for i, nm in enumerate(names):
            x, y = cx(c0 + i), self.hy(row)
            self.add(f'<rect class="pin" x="{x-3.5}" y="{y-3.5}" width="7" height="7"/>')
            if inward > 0:
                self.add(f'<text class="pn {cls}" transform="translate({x+3.5},{y+9}) rotate(90)">{nm}</text>')
            else:
                self.add(f'<text class="pn {cls}" transform="translate({x+3.5},{y-9}) rotate(-90)">{nm}</text>')

    def pin(self, col, row):
        x, y = cx(col), self.hy(row)
        self.add(f'<rect class="pin" x="{x-3.5}" y="{y-3.5}" width="7" height="7"/>')

    def done(self):
        self.o.append("</svg>")
        return "\n".join(self.o)


TB_T = ["PWMA", "AIN2", "AIN1", "STBY", "BIN1", "BIN2", "PWMB", "GND"]
TB_B = ["VM", "VCC", "GND", "AO1", "AO2", "BO2", "BO1", "GND"]
MPU = ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"]
ESP_T = ["GND", "23", "22", "TX", "RX", "21", "GND", "19", "18", "5", "17", "16", "4", "0", "2", "15", "D1", "D0", "CLK"]
ESP_B = ["3V3", "EN", "VP", "VN", "34", "35", "32", "33", "25", "26", "27", "14", "12", "GND", "13", "D2", "D3", "CMD", "5V"]

# (no, kategori, nereden, nereye, not, kalin)
W_ = [
    (1, "v12", "Anahtar çıkış bacağı (12. sütun, j satırı)", "Alt dış ray (+12 V)", "Anahtar açıkken 12 V buradan raya gider", True),
    (2, "gnd", "Klemens − (3. sütun, j satırı)", "Alt iç ray (GND)", "Adaptör eksi hattı", True),
    (3, "v12", "LM2596 IN+ (15. sütun, j satırı)", "Alt dış ray (+12 V)", "Buck girişi", False),
    (4, "gnd", "LM2596 IN− (15. sütun, a satırı)", "Üst iç ray (GND)", "Buck girişi", False),
    (5, "v12", "TB6612 VM (33. sütun, j satırı)", "Alt dış ray (+12 V)", "Motor gücü. Kısa tut", True),
    (6, "gnd", "Üst iç ray (GND)", "Alt iç ray (GND)", "İki GND hattını birleştirir. 13. sütunda", True),
    (7, "v5", "LM2596 OUT+ (31. sütun, j satırı)", "ESP32 5V pini (62. sütun, j satırı)", "Önce multimetre ile 5,0 V ayarla, sonra bağla. Uzun jumper", False),
    (8, "gnd", "LM2596 OUT− (31. sütun, a satırı)", "Üst iç ray (GND)", "", False),
    (9, "v33", "ESP32 3V3 pini (44. sütun, j satırı)", "Üst dış ray (+3,3 V)", "3,3 V kaynağı. Kablo ESP32'nin yanından geçer: uzun jumper kullan", False),
    (10, "gnd", "ESP32 GND pini (57. sütun, j satırı)", "Alt iç ray (GND)", "", False),
    (11, "v33", "TB6612 PWMA", "Üst dış ray (+3,3 V)", "Sürekli yüksek", False),
    (12, "v33", "TB6612 PWMB", "Üst dış ray (+3,3 V)", "Sürekli yüksek", False),
    (13, "v33", "TB6612 VCC (34. sütun, j satırı)", "Üst dış ray (+3,3 V)", "Sürücü mantık gerilimi. Uzun jumper: TB6612'nin yanından geçer", False),
    (14, "gnd", "TB6612 GND (35. sütun, j satırı)", "Alt iç ray (GND)", "", False),
    (15, "sig", "TB6612 STBY", "ESP32 GPIO4", "Motor aç/kapa. 10 kΩ STBY ile üst GND pini arasında", False),
    (16, "sig", "TB6612 AIN1", "ESP32 GPIO27", "Sol motor ileri PWM", False),
    (17, "sig", "TB6612 AIN2", "ESP32 GPIO14", "Sol motor geri PWM", False),
    (18, "sig", "TB6612 BIN1", "ESP32 GPIO16", "Sağ motor ileri PWM", False),
    (19, "sig", "TB6612 BIN2", "ESP32 GPIO17", "Sağ motor geri PWM", False),
    (20, "mot", "Sol motor M1 teli", "TB6612 AO1 deliği (36. sütun, j)", "Yön ters çıkarsa M1 ile M2 yer değiştirir", True),
    (21, "mot", "Sol motor M2 teli", "TB6612 AO2 deliği (37. sütun, j)", "", True),
    (22, "mot", "Sağ motor M1 teli", "TB6612 BO1 deliği (39. sütun, j)", "", True),
    (23, "mot", "Sağ motor M2 teli", "TB6612 BO2 deliği (38. sütun, j)", "", True),
    (24, "gnd", "Sol enkoder GND teli", "Alt iç ray (GND)", "", False),
    (25, "v33", "Sol enkoder VCC teli", "Üst dış ray (+3,3 V)", "5 V verme", False),
    (26, "enc", "Sol enkoder A teli", "ESP32 GPIO32", "", False),
    (27, "enc", "Sol enkoder B teli", "ESP32 GPIO33", "", False),
    (28, "gnd", "Sağ enkoder GND teli", "Alt iç ray (GND)", "", False),
    (29, "v33", "Sağ enkoder VCC teli", "Üst dış ray (+3,3 V)", "", False),
    (30, "enc", "Sağ enkoder A teli", "ESP32 GPIO25", "", False),
    (31, "enc", "Sağ enkoder B teli", "ESP32 GPIO26", "", False),
    (32, "v33", "MPU6050 VCC", "Üst dış ray (+3,3 V)", "", False),
    (33, "gnd", "MPU6050 GND", "Üst iç ray (GND)", "", False),
    (34, "i2c", "MPU6050 SCL", "ESP32 GPIO22", "", False),
    (35, "i2c", "MPU6050 SDA", "ESP32 GPIO21", "", False),
    (36, "gnd", "MPU6050 AD0", "Üst iç ray (GND)", "Adres 0x68 için AD0 GND'de", False),
    (37, "i2c", "MPU6050 INT", "ESP32 GPIO19", "", False),
    (38, "v33", "Sol ön köşe IR alıcı VCC", "Üst dış ray (+3,3 V)", "Modül 3,3 V kabul ediyorsa. 5 V verirsen OUT 5 V olur", False),
    (39, "gnd", "Sol ön köşe IR alıcı GND", "Alt iç ray (GND)", "", False),
    (40, "enc", "Sol ön köşe IR alıcı OUT", "ESP32 GPIO36 (VP)", "", False),
    (41, "v33", "Sağ ön köşe IR alıcı VCC", "Üst dış ray (+3,3 V)", "", False),
    (42, "gnd", "Sağ ön köşe IR alıcı GND", "Alt iç ray (GND)", "", False),
    (43, "enc", "Sağ ön köşe IR alıcı OUT", "ESP32 GPIO39 (VN)", "", False),
    (44, "v12", "1000 µF kondansatör + bacağı (41. sütun, j satırı)", "Alt dış ray (+12 V)", "Uzun bacak +", False),
    (45, "gnd", "1000 µF kondansatör − bacağı (43. sütun, j satırı)", "Alt iç ray (GND)", "Şeritli bacak −", False),
    (46, "v12", "Klemens + (1. sütun, i satırı)", "Sigorta giriş bacağı (4. sütun, i satırı)", "Adaptör artı hattı", True),
    (47, "v12", "Sigorta çıkış bacağı (6. sütun, j satırı)", "Anahtar orta bacağı (10. sütun, j satırı)", "Orta bacak ortaktır", True),
]
CAT = {"v12": "12 V hattı", "gnd": "GND (toprak)", "v5": "5 V", "v33": "3,3 V", "sig": "TB6612 sinyalleri",
       "mot": "Motor güç telleri", "enc": "Enkoder ve IR sinyalleri", "i2c": "I²C (MPU6050)"}


def body(s, c1, c2, r1, r2, cls, title, sub=None, small=False, m=12):
    y0 = s.y0
    x1, x2 = cx(c1) - m, cx(c2) + m
    ya, yb_ = y0 + ROWS[r1] - (0 if small else 8), y0 + ROWS[r2] + 8
    s.add(f'<rect class="{cls}" x="{x1}" y="{ya}" width="{x2-x1}" height="{yb_-ya}" rx="4"/>')
    if small:
        s.add(f'<text class="pn" x="{(x1+x2)/2}" y="{ya+9}" text-anchor="middle">{title}</text>')
        return
    s.add(f'<text class="mt" x="{(x1+x2)/2}" y="{ya+13}" text-anchor="middle">{title}</text>')
    if sub:
        s.add(f'<text class="pn" x="{(x1+x2)/2}" y="{ya+26}" text-anchor="middle">{sub}</text>')


def svg_main():
    s = Svg(y0=112, bot=190, label="Tek tam boy breadboard: tüm parçalar kart üzerinde")
    y0 = s.y0
    s.board()
    # --- ESP32 (USB sağda) ---
    xa, xb = cx(C_ESP) - 9, cx(C_ESP + 18) + 9
    s.add(f'<rect class="usb" x="{xb-2}" y="{y0+ROWS["c"]+14}" width="34" height="{ROWS["i"]-ROWS["c"]-28}" rx="3"/>')
    s.add(f'<text class="bs w9" transform="translate({xb+19},{y0+ROWS["e"]+24}) rotate(90)" text-anchor="middle">USB</text>')
    s.add(f'<rect class="esp" x="{xa}" y="{y0+ROWS["a"]-8}" width="{xb-xa}" height="{ROWS["i"]-ROWS["a"]+16}" rx="4"/>')
    s.add(f'<text class="mt" x="{(xa+xb)/2}" y="{y0+ROWS["e"]+26}" text-anchor="middle">ESP32 DevKit 38 pin · USB sağda</text>')
    s.pins(C_ESP, ESP_T, "a", +1, "light")
    s.pins(C_ESP, ESP_B, "i", -1, "light")
    # --- TB6612 ---
    xa, xb = cx(C_TB) - 9, cx(C_TB + 7) + 9
    s.add(f'<rect class="tb" x="{xa}" y="{y0+ROWS["d"]-8}" width="{xb-xa}" height="{ROWS["h"]-ROWS["d"]+16}" rx="4"/>')
    s.add(f'<text class="mt" x="{(xa+xb)/2}" y="{y0+ROWS["e"]+26}" text-anchor="middle">TB6612FNG</text>')
    s.pins(C_TB, TB_T, "d", +1, "light")
    s.pins(C_TB, TB_B, "h", -1, "light")
    # --- MPU6050 (ust yari) ---
    xa, xb = cx(C_MPU) - 9, cx(C_MPU + 7) + 9
    s.add(f'<rect class="mpu" x="{xa}" y="{y0+ROWS["c"]-8}" width="{xb-xa}" height="{ROWS["f"]-ROWS["c"]-4}" rx="4"/>')
    s.add(f'<text class="mt" x="{(xa+xb)/2}" y="{y0+ROWS["e"]+26}" text-anchor="middle">MPU6050</text>')
    s.pins(C_MPU, MPU, "c", +1, "light")
    # --- LM2596 mini (oluga yatar: - pedler ust, + pedler alt) ---
    body(s, LM_L, LM_R, "c", "i", "lm", "LM2596 mini buck", "çıkışı 5,0 V yap")
    for (c, r), lab in ((((LM_L, "c")), "IN−"), ((LM_R, "c"), "OUT−"), ((LM_L, "i"), "IN+"), ((LM_R, "i"), "OUT+")):
        s.pin(c, r)
        s.add(f'<text class="pn" x="{cx(c)+(8 if c==LM_L else -8)}" y="{s.hy(r)+(14 if r=="c" else -7)}" text-anchor="{"start" if c==LM_L else "end"}">{lab}</text>')
    # --- klemens, sigorta, anahtar, kondansator (alt yari, h satiri; kondansator g satiri) ---
    body(s, K_P, K_M, "f", "h", "kl", "KLEM", small=True)
    s.pin(K_P, "h"); s.pin(K_M, "h")
    s.add(f'<text class="pn" x="{cx(K_P)}" y="{s.hy("h")-8}" text-anchor="middle">+</text><text class="pn" x="{cx(K_M)}" y="{s.hy("h")-8}" text-anchor="middle">−</text>')
    body(s, F_A, F_B, "f", "h", "fz", "SİGORTA", small=True)
    s.pin(F_A, "h"); s.pin(F_B, "h")
    body(s, SW_1, SW_2, "f", "h", "fz", "ANAHTAR", small=True)
    for c, lab in ((SW_1, "boş"), (SW_C, "ort"), (SW_2, "çık")):
        s.pin(c, "h")
        s.add(f'<text class="pn" x="{cx(c)}" y="{s.hy("h")-8}" text-anchor="middle">{lab}</text>')
    body(s, CAP_P, CAP_M, "f", "g", "cp", "1000 µF", small=True, m=5)
    s.pin(CAP_P, "g"); s.pin(CAP_M, "g")
    s.add(f'<text class="note" x="{cx(CAP_P)}" y="{s.hy("g")+15}" text-anchor="middle">+</text><text class="note" x="{cx(CAP_M)}" y="{s.hy("g")+15}" text-anchor="middle">−</text>')
    # --- 10 kOhm: STBY - ust GND pini, b satiri ---
    xr1, xr2, yr = cx(C_TB + 3), cx(C_TB + 7), y0 + ROWS["b"]
    s.add(f'<line class="lead" x1="{xr1}" y1="{yr}" x2="{xr2}" y2="{yr}"/>')
    s.add(f'<rect class="res" x="{xr1+9}" y="{yr-5}" width="{xr2-xr1-18}" height="10" rx="2"/>')
    s.add(f'<text class="note" x="{(xr1+xr2)/2}" y="{yr-9}" text-anchor="middle">10 kΩ</text>')
    s.dot(xr1, yr, "gnd"); s.dot(xr2, yr, "gnd")

    # === kablolar ===
    # ust raylara giden kisa kablolar (a satiri)
    s.rail(C_MPU, "a", "T+", 32, "v33", rcol=3)
    s.rail(C_MPU + 1, "a", "T-", 33, "gnd")
    s.rail(C_MPU + 6, "a", "T-", 36, "gnd", rcol=10)
    s.rail(C_TB, "a", "T+", 11, "v33", rcol=31)
    s.rail(C_TB + 6, "a", "T+", 12, "v33", rcol=41)
    s.rail(LM_L, "a", "T-", 4, "gnd", rcol=15)
    s.rail(LM_R, "a", "T-", 8, "gnd", rcol=31)
    # alt raylara giden kisa kablolar (j satiri)
    s.rail(K_M, "j", "B-", 2, "gnd", rcol=3, thick=True)
    s.rail(SW_2, "j", "B+", 1, "v12", rcol=11, thick=True)
    s.rail(LM_L, "j", "B+", 3, "v12", rcol=16)
    s.rail(C_TB, "j", "B+", 5, "v12", rcol=35, thick=True)
    s.rail(C_TB + 2, "j", "B-", 14, "gnd", rcol=35)
    s.rail(C_ESP + 13, "j", "B-", 10, "gnd", rcol=57)
    s.rail(CAP_P, "j", "B+", 44, "v12", rcol=40)
    s.rail(CAP_M, "j", "B-", 45, "gnd", rcol=43)
    # sigorta ve anahtar zinciri (yatay)
    s.hwire(K_P, F_A, "i", 46, "v12", True)
    s.hwire(F_B, SW_C, "j", 47, "v12", True)
    # GND koprusu (ust ic ray - alt ic ray)
    x = cx(13)
    s.line(x, s.hy("T-"), x, s.hy("B-"), "gnd", True)
    s.dot(x, s.hy("T-"), "gnd"); s.dot(x, s.hy("B-"), "gnd")
    s.tag(x, y0 + ROWS["d"] + 30, 6, "gnd")
    ENDS.append((6, 13, "T-")); ENDS.append((6, 13, "B-"))
    # ust sira etiketli kablolar (yukari)
    up = [(C_TB + 3, 66, 15, "sig"), (C_TB + 2, 88, 16, "sig"), (C_TB + 1, 66, 17, "sig"), (C_TB + 4, 88, 18, "sig"), (C_TB + 5, 66, 19, "sig"),
          (C_MPU + 2, 66, 34, "i2c"), (C_MPU + 3, 88, 35, "i2c"), (C_MPU + 7, 66, 37, "i2c"),
          (56, 88, 15, "sig"), (55, 110, 18, "sig"), (54, 88, 19, "sig"),
          (51, 88, 37, "i2c"), (49, 110, 35, "i2c"), (46, 88, 34, "i2c")]
    for col, ln, n, cat in up:
        s.stub(col, "b" if col >= C_ESP else "a", "up", ln, n, cat)
    # alt sira etiketli kablolar (asagi)
    dn = [(C_TB + 3, 68, 20, "mot", True), (C_TB + 4, 90, 21, "mot", True), (C_TB + 5, 68, 23, "mot", True), (C_TB + 6, 90, 22, "mot", True),
          (54, 66, 16, "sig", False), (55, 88, 17, "sig", False),
          (50, 66, 26, "enc", False), (51, 88, 27, "enc", False), (52, 66, 30, "enc", False), (53, 88, 31, "enc", False),
          (62, 66, 7, "v5", False), (LM_R, 66, 7, "v5", False), (46, 66, 40, "enc", False), (47, 88, 43, "enc", False),
          (44, 66, 9, "v33", False), (C_TB + 1, 66, 13, "v33", False)]
    for col, ln, n, cat, th in dn:
        s.stub(col, "j", "down", ln, n, cat, th)
    # 3,3 V ucu: ust dis rayda
    for rcol, n in ((45, 9), (39, 13), (15, 38), (21, 41), (53, 25), (59, 29)):
        s.on_rail(rcol, "T+", n, "v33")
    # GND uclari: alt ic rayda
    for rcol, n in ((17, 39), (19, 42), (21, 24), (25, 28)):
        s.on_rail(rcol, "B-", n, "gnd")

    # --- alt sira 1: motorlar ve IR alicilar ---
    yb = y0 + BH + 52
    for x0c, name, ids in ((29, "SOL MOTOR", ((20, "M1", "mot"), (21, "M2", "mot"), (24, "enk GND", "gnd"), (25, "enk VCC", "v33"), (26, "enk A", "enc"), (27, "enk B", "enc"))),
                           (38, "SAĞ MOTOR", ((22, "M1", "mot"), (23, "M2", "mot"), (28, "enk GND", "gnd"), (29, "enk VCC", "v33"), (30, "enk A", "enc"), (31, "enk B", "enc")))):
        xa = cx(x0c)
        s.add(f'<rect class="blk" x="{xa-8}" y="{yb}" width="{7*P+16}" height="62" rx="6"/>')
        s.add(f'<text class="bt" x="{xa-8+(7*P+16)/2}" y="{yb+16}" text-anchor="middle">{name} · 6 tel</text>')
        for i, (n, lab, cat) in enumerate(ids):
            xx = xa + 2 + i * 16.5
            s.add(f'<text class="pn3" x="{xx}" y="{yb+54}" text-anchor="middle">{lab.replace("enk ","")}</text>')
            s.tag(xx, yb + 34, n, cat)
    for x0c, name, ids in ((2, "SOL ÖN IR", ((38, "VCC", "v33"), (39, "GND", "gnd"), (40, "OUT", "enc"))),
                           (8, "SAĞ ÖN IR", ((41, "VCC", "v33"), (42, "GND", "gnd"), (43, "OUT", "enc")))):
        xa = cx(x0c)
        s.add(f'<rect class="blk" x="{xa-8}" y="{yb}" width="{3*16.5+14}" height="62" rx="6"/>')
        s.add(f'<text class="bt" x="{xa-8+(3*16.5+14)/2}" y="{yb+16}" text-anchor="middle">{name}</text>')
        for i, (n, lab, cat) in enumerate(ids):
            xx = xa + 4 + i * 16.5
            s.add(f'<text class="pn3" x="{xx}" y="{yb+54}" text-anchor="middle">{lab}</text>')
            s.tag(xx, yb + 34, n, cat)
    # adaptor (kart disi)
    s.add(f'<rect class="blk" x="450" y="{yb+4}" width="0" height="0"/>')
    ya = y0 + BH + 128
    s.add(f'<rect class="blk" x="{cx(1)-12}" y="{ya}" width="150" height="44" rx="6"/>')
    s.add(f'<text class="bt" x="{cx(1)-12+75}" y="{ya+19}" text-anchor="middle">Adaptör 12 V ≥3 A</text>')
    s.add(f'<text class="bs" x="{cx(1)-12+75}" y="{ya+35}" text-anchor="middle">kırmızı → klemens +, siyah → −</text>')
    s.add(f'<text class="note" x="{cx(1)+170}" y="{ya+27}">Adaptör sadece klemense bağlanır. Başka kablosu yok.</text>')
    return s.done()


def overview():
    return '''<svg viewBox="0 0 1000 310" role="img" aria-label="Büyük resim" xmlns="http://www.w3.org/2000/svg">
<rect class="bb" x="20" y="20" width="960" height="228" rx="10"/>
<text class="bt" x="36" y="42">Tek tam boy breadboard: her şey kartın üstünde</text>
<rect class="c-v33" x="36" y="52" width="928" height="14" rx="7"/><text class="pn" x="52" y="62.5">üst dış ray · +3,3 V</text>
<rect class="c-gnd" x="36" y="70" width="928" height="14" rx="7"/><text class="pn" x="52" y="80.5" style="fill:var(--bg)">üst iç ray · GND</text>
<rect class="c-gnd" x="36" y="202" width="928" height="14" rx="7"/><text class="pn" x="52" y="212.5" style="fill:var(--bg)">alt iç ray · GND</text>
<rect class="c-v12" x="36" y="220" width="928" height="14" rx="7"/><text class="pn" x="52" y="230.5">alt dış ray · +12 V</text>
<rect class="mpu" x="82" y="98" width="118" height="44" rx="5"/><text class="mt" x="141" y="124" text-anchor="middle">MPU6050</text>
<rect class="kl" x="36" y="148" width="50" height="44" rx="5"/><text class="mt" x="61" y="167" text-anchor="middle">KLEM</text><text class="pn" x="61" y="181" text-anchor="middle">+ −</text>
<rect class="fz" x="92" y="148" width="40" height="44" rx="5"/><text class="mt" x="112" y="167" text-anchor="middle">3 A</text><text class="pn" x="112" y="181" text-anchor="middle">sigorta</text>
<rect class="fz" x="138" y="148" width="60" height="44" rx="5"/><text class="mt" x="168" y="167" text-anchor="middle">ANAHTAR</text>
<rect class="lm" x="230" y="104" width="256" height="88" rx="5"/><text class="mt" x="358" y="144" text-anchor="middle">LM2596 mini buck</text><text class="pn" x="358" y="160" text-anchor="middle">12 V → 5,0 V</text>
<rect class="tb" x="507" y="98" width="116" height="94" rx="5"/><text class="mt" x="565" y="150" text-anchor="middle">TB6612</text>
<rect class="cp" x="636" y="148" width="46" height="44" rx="5"/><text class="mt" x="659" y="167" text-anchor="middle">1000</text><text class="pn" x="659" y="181" text-anchor="middle">µF</text>
<rect class="esp" x="670" y="98" width="260" height="94" rx="5"/><text class="mt" x="800" y="150" text-anchor="middle">ESP32 DevKit 38 pin</text>
<rect class="blk" x="934" y="118" width="40" height="52" rx="5"/><text class="bs" x="954" y="148" text-anchor="middle">USB</text>
<text class="note" x="500" y="268" text-anchor="middle">Kart dışında sadece: adaptör, 2 motor (6 telli), 2 IR alıcı</text>
<rect class="blk" x="20" y="262" width="200" height="38" rx="6"/><text class="bs" x="120" y="285" text-anchor="middle">Adaptör 12 V → klemense</text>
<text class="note" x="500" y="288" text-anchor="middle">Akış: klemens → sigorta → anahtar → alt dış ray (12 V) → buck → ESP32 5V → 3V3 → üst dış ray</text>
</svg>'''


def table():
    r = []
    for cat, ad in CAT.items():
        r.append(f'<tr class="grp"><th colspan="4"><span class="sw t-{cat}"></span>{ad}</th></tr>')
        for no, c, a, b, note, kal in W_:
            if c == cat:
                k = ' <b class="kal">kalın</b>' if kal else ""
                r.append(f'<tr><td class="num"><span class="no t-{cat}">{no}</span></td><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(note)}{k}</td></tr>')
    return "\n".join(r)


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    tpl = (here / "breadboard_sablon.html").read_text(encoding="utf-8")
    out = tpl.replace("{{OVERVIEW}}", overview()).replace("{{SVG}}", svg_main()).replace("{{TABLE}}", table())
    (here / "breadboard_sema.html").write_text(out, encoding="utf-8")
    print("ok", len(out), "bayt;", len(W_), "kablo")
