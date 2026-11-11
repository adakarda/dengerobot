"""Breadboard sema sayfasi uretici (GERCEK KART DUZENI, v10) -> docs/breadboard_sema.html
Calistir: python docs/breadboard_uret.py
Duzen kullanicinin gercek kartindan: ESP32 21->3 (sol uc 21a), MPU6050 23-30, TB6612 39->32 (VM 39),
LM2596 41 (OUT) ve 57 (IN), 3 pinli klemens 60-62.
Raylar: ust dis +12 V, ust ic GND, alt ic GND, alt dis +3,3 V. GND'ler 6 numarali kablo ile (22. sutun) birlesir.
Sigorta, anahtar ve kondansator kartta YOK (sonradan eklenebilir)."""
import html
import pathlib

P, X0 = 14, 64                                   # delik araligi (2,54 mm), 1. sutunun x'i
ROWS = {"a": 60, "b": 74, "c": 88, "d": 102, "e": 116, "f": 158, "g": 172, "h": 186, "i": 200, "j": 214}
RAILS = {"T+": 14, "T-": 28, "B-": 246, "B+": 260}          # ust dis, ust ic, alt ic, alt dis
STRIPE = {"T+": -8, "T-": 8, "B-": -8, "B+": 8}             # renkli serit: raya gore dis/ic yon
RNAME = {"T+": "+12 V", "T-": "GND", "B-": "GND", "B+": "+3,3 V"}
BH, BW, W = 276, 958, 1000
RCOLS = [3 + g * 6 + k for g in range(10) for k in range(5)]   # 10 grup x 5 = 50 delik / ray

# --- parcalarin sutunlari (cizim ve dogrulama ayni sabitleri kullanir) ---
C_ESP = 21        # ESP32 sol pini (GND / 3V3) 21. sutunda, sutun numarasi azalarak 3'e kadar gider
C_MPU = 23        # MPU6050 VCC 23. sutunda, artarak 30'a kadar
C_TB = 39         # TB6612 PWMA / VM 39. sutunda, azalarak 32'ye kadar
K_P, K_M = 60, 62                # 3 pinli klemens: + ve - (ortadaki 61 bos)
LM_L, LM_R = 41, 57              # LM2596: OUT pedleri 41, IN pedleri 57 (+ pedler c satiri, - pedler i satiri)
EXTRA_PINS = {(K_P, "h"): "K.+", (K_M, "h"): "K.-",
              (LM_L, "c"): "LM.OUT+", (LM_L, "i"): "LM.OUT-", (LM_R, "c"): "LM.IN+", (LM_R, "i"): "LM.IN-"}


def ecol(i):
    return C_ESP - i


def tcol(i):
    return C_TB - i


def mcol(i):
    return C_MPU + i


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
        for c in range(1, 64):                       # sutun numaralari: her sutun, a satirinin hemen ustu
            cls = "coll" if c % 5 == 0 or c in (1, 3, 21, 22, 23, 30, 32, 39, 41, 57, 60, 62) else "coll dim"
            self.add(f'<text class="{cls}" x="{cx(c)}" y="{y0+ROWS["a"]-14}" text-anchor="middle">{c}</text>')

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

    def on_rail(self, rcol, rail, n, cat):
        ENDS.append((n, rcol, rail))
        x, y = cx(rcol), self.hy(rail)
        self.dot(x, y, cat)
        self.tag(x, y, n, cat)

    def pins(self, col_of, names, row, inward, cls):
        """Modul pin etiketleri (dikey yazi, govdenin icine dogru). col_of(i): i. pinin sutunu."""
        for i, nm in enumerate(names):
            x, y = cx(col_of(i)), self.hy(row)
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
    (1, "v12", "Klemens + (60. sütun, j satırı)", "Üst dış ray (+12 V)", "Adaptörün artı hattı. Klemensin üstündeki + işaretini kontrol et", True),
    (2, "gnd", "Klemens − (62. sütun, j satırı)", "Alt iç ray (GND)", "Adaptör eksi hattı", True),
    (3, "v12", "LM2596 IN+ (57. sütun, a satırı)", "Üst dış ray (+12 V)", "Buck girişi. Uzun jumper: pedden kartın altındaki raya", False),
    (4, "gnd", "LM2596 IN− (57. sütun, j satırı)", "Alt iç ray (GND)", "Buck girişi", False),
    (5, "v12", "TB6612 VM (39. sütun, j satırı)", "Üst dış ray (+12 V)", "Motor gücü. Kısa tut", True),
    (6, "gnd", "Üst iç ray (GND)", "Alt iç ray (GND)", "İki GND hattını birleştirir. 22. sütunda, ESP32 ile MPU6050 arasında", True),
    (7, "v5", "LM2596 OUT+ (41. sütun, a satırı)", "ESP32 5V pini (3. sütun, j satırı)", "Önce multimetre ile 5,0 V ayarla, sonra bağla. Uzun jumper", False),
    (8, "gnd", "LM2596 OUT− (41. sütun, j satırı)", "Alt iç ray (GND)", "", False),
    (9, "v33", "ESP32 3V3 pini (21. sütun, j satırı)", "Alt dış ray (+3,3 V)", "3,3 V kaynağı. Uzun jumper: ESP32 üstünden değil yanından geçir", False),
    (10, "gnd", "ESP32 GND pini (8. sütun, j satırı)", "Alt iç ray (GND)", "", False),
    (11, "v33", "TB6612 PWMA (39. sütun, a satırı)", "Alt dış ray (+3,3 V)", "Sürekli yüksek", False),
    (12, "v33", "TB6612 PWMB (33. sütun, a satırı)", "Alt dış ray (+3,3 V)", "Sürekli yüksek", False),
    (13, "v33", "TB6612 VCC (38. sütun, j satırı)", "Alt dış ray (+3,3 V)", "Sürücü mantık gerilimi. Uzun jumper: TB6612'nin yanından geçer", False),
    (14, "gnd", "TB6612 GND (37. sütun, j satırı)", "Alt iç ray (GND)", "", False),
    (15, "sig", "TB6612 STBY (36. sütun, a satırı)", "ESP32 GPIO4 (9. sütun, b satırı)", "Motor aç/kapa. 10 kΩ STBY ile üst GND pini arasında", False),
    (16, "sig", "TB6612 AIN1 (37. sütun, a satırı)", "ESP32 GPIO27 (11. sütun, j satırı)", "Sol motor ileri PWM", False),
    (17, "sig", "TB6612 AIN2 (38. sütun, a satırı)", "ESP32 GPIO14 (10. sütun, j satırı)", "Sol motor geri PWM", False),
    (18, "sig", "TB6612 BIN1 (35. sütun, a satırı)", "ESP32 GPIO16 (10. sütun, b satırı)", "Sağ motor ileri PWM", False),
    (19, "sig", "TB6612 BIN2 (34. sütun, a satırı)", "ESP32 GPIO17 (11. sütun, b satırı)", "Sağ motor geri PWM", False),
    (20, "mot", "Sol motor M1 teli", "TB6612 AO1 deliği (36. sütun, j)", "Yön ters çıkarsa M1 ile M2 yer değiştirir", True),
    (21, "mot", "Sol motor M2 teli", "TB6612 AO2 deliği (35. sütun, j)", "", True),
    (22, "mot", "Sağ motor M1 teli", "TB6612 BO1 deliği (33. sütun, j)", "", True),
    (23, "mot", "Sağ motor M2 teli", "TB6612 BO2 deliği (34. sütun, j)", "", True),
    (24, "gnd", "Sol enkoder GND teli", "Alt iç ray (GND)", "", False),
    (25, "v33", "Sol enkoder VCC teli", "Alt dış ray (+3,3 V)", "5 V verme", False),
    (26, "enc", "Sol enkoder A teli", "ESP32 GPIO32 (15. sütun, j satırı)", "", False),
    (27, "enc", "Sol enkoder B teli", "ESP32 GPIO33 (14. sütun, j satırı)", "", False),
    (28, "gnd", "Sağ enkoder GND teli", "Alt iç ray (GND)", "", False),
    (29, "v33", "Sağ enkoder VCC teli", "Alt dış ray (+3,3 V)", "", False),
    (30, "enc", "Sağ enkoder A teli", "ESP32 GPIO25 (13. sütun, j satırı)", "", False),
    (31, "enc", "Sağ enkoder B teli", "ESP32 GPIO26 (12. sütun, j satırı)", "", False),
    (32, "v33", "MPU6050 VCC (23. sütun, a satırı)", "Alt dış ray (+3,3 V)", "", False),
    (33, "gnd", "MPU6050 GND (24. sütun, a satırı)", "Üst iç ray (GND)", "", False),
    (34, "i2c", "MPU6050 SCL (25. sütun, a satırı)", "ESP32 GPIO22 (19. sütun, b satırı)", "", False),
    (35, "i2c", "MPU6050 SDA (26. sütun, a satırı)", "ESP32 GPIO21 (16. sütun, b satırı)", "", False),
    (36, "gnd", "MPU6050 AD0 (29. sütun, a satırı)", "Üst iç ray (GND)", "Adres 0x68 için AD0 GND'de", False),
    (37, "i2c", "MPU6050 INT (30. sütun, a satırı)", "ESP32 GPIO19 (14. sütun, b satırı)", "", False),
    (38, "v33", "Sol ön köşe IR alıcı VCC", "Alt dış ray (+3,3 V)", "Modül 3,3 V kabul ediyorsa. 5 V verirsen OUT 5 V olur", False),
    (39, "gnd", "Sol ön köşe IR alıcı GND", "Alt iç ray (GND)", "", False),
    (40, "enc", "Sol ön köşe IR alıcı OUT", "ESP32 GPIO36 (VP) (19. sütun, j satırı)", "", False),
    (41, "v33", "Sağ ön köşe IR alıcı VCC", "Alt dış ray (+3,3 V)", "", False),
    (42, "gnd", "Sağ ön köşe IR alıcı GND", "Alt iç ray (GND)", "", False),
    (43, "enc", "Sağ ön köşe IR alıcı OUT", "ESP32 GPIO39 (VN) (18. sütun, j satırı)", "", False),
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
    s = Svg(y0=112, bot=190, label="Gerçek kart düzeni: ESP32 21 ile 3. sütun arası, TB6612 39 ile 32, LM2596 41 ve 57")
    y0 = s.y0
    s.board()
    # --- ESP32 (USB solda, 21 -> 3) ---
    xa, xb = cx(3) - 9, cx(21) + 9
    s.add(f'<rect class="usb" x="{xa-32}" y="{y0+ROWS["c"]+14}" width="34" height="{ROWS["i"]-ROWS["c"]-28}" rx="3"/>')
    s.add(f'<text class="bs w9" transform="translate({xa-14},{y0+ROWS["e"]+24}) rotate(-90)" text-anchor="middle">USB</text>')
    s.add(f'<rect class="esp" x="{xa}" y="{y0+ROWS["a"]-8}" width="{xb-xa}" height="{ROWS["i"]-ROWS["a"]+16}" rx="4"/>')
    s.add(f'<text class="mt" x="{(xa+xb)/2}" y="{y0+ROWS["e"]+26}" text-anchor="middle">ESP32 DevKit 38 pin · USB solda · 21 → 3</text>')
    s.pins(ecol, ESP_T, "a", +1, "light")
    s.pins(ecol, ESP_B, "i", -1, "light")
    # --- TB6612 (39 -> 32) ---
    xa, xb = cx(32) - 9, cx(39) + 9
    s.add(f'<rect class="tb" x="{xa}" y="{y0+ROWS["d"]-8}" width="{xb-xa}" height="{ROWS["h"]-ROWS["d"]+16}" rx="4"/>')
    s.add(f'<text class="mt" x="{(xa+xb)/2}" y="{y0+ROWS["e"]+26}" text-anchor="middle">TB6612FNG</text>')
    s.pins(tcol, TB_T, "d", +1, "light")
    s.pins(tcol, TB_B, "h", -1, "light")
    # --- MPU6050 (23 -> 30, ust yari) ---
    xa, xb = cx(23) - 9, cx(30) + 9
    s.add(f'<rect class="mpu" x="{xa}" y="{y0+ROWS["c"]-8}" width="{xb-xa}" height="{ROWS["f"]-ROWS["c"]-4}" rx="4"/>')
    s.add(f'<text class="mt" x="{(xa+xb)/2}" y="{y0+ROWS["e"]+26}" text-anchor="middle">MPU6050</text>')
    s.pins(mcol, MPU, "c", +1, "light")
    # --- LM2596 mini (41 ve 57; + pedler c satiri, - pedler i satiri) ---
    body(s, LM_L, LM_R, "c", "i", "lm", "LM2596 mini buck", "çıkışı 5,0 V yap")
    for c, r, lab in ((LM_L, "c", "OUT+"), (LM_L, "i", "OUT−"), (LM_R, "c", "IN+"), (LM_R, "i", "IN−")):
        s.pin(c, r)
        s.add(f'<text class="pn" x="{cx(c)+(8 if c==LM_L else -8)}" y="{s.hy(r)+(14 if r=="c" else -7)}" text-anchor="{"start" if c==LM_L else "end"}">{lab}</text>')
    # --- 3 pinli klemens (60-62, h satiri; ortadaki bos) ---
    body(s, K_P, K_M, "f", "h", "kl", "KLEMENS", small=True)
    for c, lab in ((K_P, "+"), (K_P + 1, "boş"), (K_M, "−")):
        s.pin(c, "h")
        s.add(f'<text class="pn" x="{cx(c)}" y="{s.hy("h")-8}" text-anchor="middle">{lab}</text>')
    # --- 10 kOhm: STBY (36) - ust GND pini (32), b satiri ---
    xr1, xr2, yr = cx(tcol(7)), cx(tcol(3)), y0 + ROWS["b"]
    s.add(f'<line class="lead" x1="{xr1}" y1="{yr}" x2="{xr2}" y2="{yr}"/>')
    s.add(f'<rect class="res" x="{xr1+9}" y="{yr-5}" width="{xr2-xr1-18}" height="10" rx="2"/>')
    s.add(f'<text class="note" x="{(xr1+xr2)/2}" y="{yr-9}" text-anchor="middle">10 kΩ</text>')
    s.dot(xr1, yr, "gnd"); s.dot(xr2, yr, "gnd")

    # === kablolar ===
    # ust raylara giden kisa kablolar (a satiri)
    s.rail(mcol(1), "a", "T-", 33, "gnd", rcol=24)
    s.rail(mcol(6), "a", "T-", 36, "gnd", rcol=29)
    s.rail(LM_R, "a", "T+", 3, "v12", rcol=57)
    # alt raylara giden kisa kablolar (j satiri)
    s.rail(K_M, "j", "B-", 2, "gnd", rcol=61, thick=True)
    s.rail(LM_R, "j", "B-", 4, "gnd", rcol=57)
    s.rail(LM_L, "j", "B-", 8, "gnd", rcol=41)
    s.rail(tcol(1), "j", "B+", 13, "v33", rcol=37)
    s.rail(ecol(0), "j", "B+", 9, "v33", rcol=21)
    s.rail(tcol(2), "j", "B-", 14, "gnd", rcol=37)
    s.rail(ecol(13), "j", "B-", 10, "gnd", rcol=9)
    # GND koprusu (ust ic ray - alt ic ray), 22. sutun
    x = cx(22)
    s.line(x, s.hy("T-"), x, s.hy("B-"), "gnd", True)
    s.dot(x, s.hy("T-"), "gnd"); s.dot(x, s.hy("B-"), "gnd")
    s.tag(x, y0 + ROWS["e"] + 14 + 20, 6, "gnd")
    ENDS.append((6, 22, "T-")); ENDS.append((6, 22, "B-"))
    # ust sira etiketli kablolar (yukari): TB6612, MPU6050 (a satiri), ESP32 ust pinleri (b satiri)
    up = [(tcol(3), "a", 66, 15, "sig"), (tcol(2), "a", 88, 16, "sig"), (tcol(1), "a", 66, 17, "sig"), (tcol(4), "a", 88, 18, "sig"), (tcol(5), "a", 66, 19, "sig"),
          (mcol(2), "a", 66, 34, "i2c"), (mcol(3), "a", 88, 35, "i2c"), (mcol(7), "a", 66, 37, "i2c"),
          (LM_L, "a", 66, 7, "v5"), (mcol(0), "a", 66, 32, "v33"), (tcol(0), "a", 66, 11, "v33"), (tcol(6), "a", 66, 12, "v33"),
          (ecol(2), "b", 66, 34, "i2c"), (ecol(5), "b", 88, 35, "i2c"), (ecol(7), "b", 66, 37, "i2c"),
          (ecol(10), "b", 66, 19, "sig"), (ecol(11), "b", 88, 18, "sig"), (ecol(12), "b", 66, 15, "sig")]
    for col, row, ln, n, cat in up:
        s.stub(col, row, "up", ln, n, cat)
    # alt sira etiketli kablolar (asagi): TB6612 (j satiri), ESP32 alt pinleri (j satiri)
    dn = [(tcol(3), 68, 20, "mot", True), (tcol(4), 90, 21, "mot", True), (tcol(5), 68, 23, "mot", True), (tcol(6), 90, 22, "mot", True),
          (K_P, 66, 1, "v12", True), (tcol(0), 66, 5, "v12", True),
          (ecol(2), 66, 40, "enc", False), (ecol(3), 88, 43, "enc", False),
          (ecol(6), 66, 26, "enc", False), (ecol(7), 88, 27, "enc", False), (ecol(8), 66, 30, "enc", False), (ecol(9), 88, 31, "enc", False),
          (ecol(10), 66, 16, "sig", False), (ecol(11), 88, 17, "sig", False), (ecol(18), 66, 7, "v5", False)]
    for col, ln, n, cat, th in dn:
        s.stub(col, "j", "down", ln, n, cat, th)
    # 3,3 V ucu: alt dis rayda
    for rcol, n in ((23, 32), (39, 11), (33, 12), (3, 38), (9, 41), (51, 25), (57, 29)):
        s.on_rail(rcol, "B+", n, "v33")
    # 12 V ucu: ust dis rayda (klemens + ve TB6612 VM)
    for rcol, n in ((59, 1), (39, 5)):
        s.on_rail(rcol, "T+", n, "v12")
    # GND uclari: alt ic rayda
    for rcol, n in ((45, 39), (49, 42), (27, 24), (31, 28)):
        s.on_rail(rcol, "B-", n, "gnd")

    # --- alt sira 1: motorlar ve IR alicilar ---
    yb = y0 + BH + 52
    for x0c, name, ids in ((24, "SOL MOTOR", ((20, "M1", "mot"), (21, "M2", "mot"), (24, "enk GND", "gnd"), (25, "enk VCC", "v33"), (26, "enk A", "enc"), (27, "enk B", "enc"))),
                           (33, "SAĞ MOTOR", ((22, "M1", "mot"), (23, "M2", "mot"), (28, "enk GND", "gnd"), (29, "enk VCC", "v33"), (30, "enk A", "enc"), (31, "enk B", "enc")))):
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
    # adaptor (kart disi), klemensin altinda
    ya = y0 + BH + 128
    xl = cx(63) - 150
    s.add(f'<rect class="blk" x="{xl}" y="{ya}" width="150" height="44" rx="6"/>')
    s.add(f'<text class="bt" x="{xl+75}" y="{ya+19}" text-anchor="middle">Adaptör 12 V ≥3 A</text>')
    s.add(f'<text class="bs" x="{xl+75}" y="{ya+35}" text-anchor="middle">kırmızı → klemens +, siyah → −</text>')
    s.add(f'<text class="note" x="{xl-10}" y="{ya+27}" text-anchor="end">Adaptör sadece klemense bağlanır.</text>')
    return s.done()


def overview():
    def ox(c):
        return 36 + (c - 1) * 928 / 62

    def box(cls, c1, c2, y, h, title, sub=None, ty=None):
        x1, x2 = ox(c1) - 6, ox(c2) + 6
        t = f'<rect class="{cls}" x="{x1:.0f}" y="{y}" width="{x2-x1:.0f}" height="{h}" rx="5"/>'
        t += f'<text class="mt" x="{(x1+x2)/2:.0f}" y="{ty or y+h/2+4:.0f}" text-anchor="middle">{title}</text>'
        if sub:
            t += f'<text class="pn" x="{(x1+x2)/2:.0f}" y="{(ty or y+h/2+4)+15:.0f}" text-anchor="middle">{sub}</text>'
        return t

    o = ['<svg viewBox="0 0 1000 310" role="img" aria-label="Büyük resim" xmlns="http://www.w3.org/2000/svg">',
         '<rect class="bb" x="20" y="20" width="960" height="228" rx="10"/>',
         '<text class="bt" x="36" y="42">Gerçek kart: soldan sağa ESP32, MPU6050, TB6612, LM2596, klemens</text>',
         '<rect class="c-v12" x="36" y="52" width="928" height="14" rx="7"/><text class="pn" x="52" y="62.5">üst dış ray · +12 V</text>',
         '<rect class="c-gnd" x="36" y="70" width="928" height="14" rx="7"/><text class="pn" x="52" y="80.5" style="fill:var(--bg)">üst iç ray · GND</text>',
         '<rect class="c-gnd" x="36" y="202" width="928" height="14" rx="7"/><text class="pn" x="52" y="212.5" style="fill:var(--bg)">alt iç ray · GND</text>',
         '<rect class="c-v33" x="36" y="220" width="928" height="14" rx="7"/><text class="pn" x="52" y="230.5">alt dış ray · +3,3 V</text>']
    o.append(f'<rect class="blk" x="{ox(3)-38:.0f}" y="124" width="34" height="42" rx="4"/><text class="bs" x="{ox(3)-21:.0f}" y="148" text-anchor="middle">USB</text>')
    o.append(box("esp", 3, 21, 98, 94, "ESP32 DevKit", "sütun 21 → 3"))
    o.append(box("mpu", 23, 30, 98, 94, "MPU6050", "23–30"))
    o.append(box("tb", 32, 39, 98, 94, "TB6612", "39 → 32"))
    o.append(box("lm", 41, 57, 98, 94, "LM2596 mini buck", "OUT 41 · IN 57 · 12 V → 5,0 V"))
    o.append(box("kl", 60, 62, 98, 94, "KLEM", "+ · − "))
    o.append('<text class="note" x="500" y="268" text-anchor="middle">Kart dışında sadece: adaptör, 2 motor (6 telli), 2 IR alıcı</text>')
    o.append('<rect class="blk" x="780" y="262" width="200" height="38" rx="6"/><text class="bs" x="880" y="285" text-anchor="middle">Adaptör 12 V → klemense</text>')
    o.append('<text class="note" x="500" y="288" text-anchor="middle">Akış: klemens → üst dış ray (12 V) → buck → ESP32 5V → 3V3 → alt dış ray</text>')
    o.append('</svg>')
    return "\n".join(o)


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
    out = (tpl.replace("{{OVERVIEW}}", overview()).replace("{{SVG}}", svg_main()).replace("{{TABLE}}", table())
           .replace("{{COUNT}}", str(len(W_))))
    (here / "breadboard_sema.html").write_text(out, encoding="utf-8")
    print("ok", len(out), "bayt;", len(W_), "kablo")
