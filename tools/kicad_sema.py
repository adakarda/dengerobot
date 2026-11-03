"""Robotun KiCad semasini uretir ve denetler -> elektronik/
  cdtp_robot.kicad_sch  (KiCad 10 ile acilir; moduller cdtp.kicad_sym kutuphanesinde)
  cdtp_robot.pdf / .svg, erc.json, netlist.xml, sema_kontrol.md
Calistir: python tools/kicad_sema.py   (KiCad 10 kurulu olmali: kicad-cli)
Baglantilar etiketle yapilir: ayni adli etiketler ayni hattir. Denetim: ERC + netlistteki her ESP32 pini
firmware/robot/src/pins.h ile ve her kablo ucu robot_src.html tablolariyla karsilastirilir."""
import copy
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "elektronik"
KICAD = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/KiCad/10.0"
CLI = KICAD / "bin/kicad-cli.exe"
STDLIB = KICAD / "share/kicad/symbols"
PROJE = "cdtp_robot"
NS = uuid.UUID("6e400001-cd7b-4e3a-9a40-2026cd7b0001")


def uid(*a):
    return str(uuid.uuid5(NS, "/".join(map(str, a))))


# ---------------- S-ifadesi ----------------
class S(str):
    """Tirnakli dize."""


def ayristir(metin):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', metin)
    yigin = [[]]
    for t in tok:
        if t == "(":
            yigin.append([])
        elif t == ")":
            son = yigin.pop()
            yigin[-1].append(son)
        elif t.startswith('"'):
            yigin[-1].append(S(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            yigin[-1].append(t)
    return yigin[0][0]


def yaz(n, girinti=0):
    if isinstance(n, list):
        if all(not isinstance(c, list) for c in n):
            return "(" + " ".join(yaz(c) for c in n) + ")"
        ic = "\n".join("\t" * (girinti + 1) + yaz(c, girinti + 1) for c in n[1:])
        return "(" + yaz(n[0]) + "\n" + ic + "\n" + "\t" * girinti + ")"
    if isinstance(n, S):
        return '"' + n.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(n, float):
        return f"{n:.4f}".rstrip("0").rstrip(".")
    return str(n)


def bul(n, bas):
    return [c for c in n if isinstance(c, list) and c and c[0] == bas]


# ---------------- sembol kutuphaneleri ----------------
_lib_cache = {}


def std_sembol(lib_id):
    lib, ad = lib_id.split(":")
    if lib not in _lib_cache:
        _lib_cache[lib] = ayristir((STDLIB / f"{lib}.kicad_sym").read_text(encoding="utf-8"))
    for s in bul(_lib_cache[lib], "symbol"):
        if s[1] == ad:
            if bul(s, "extends"):
                raise ValueError(f"{lib_id} turetilmis sembol; desteklenmiyor")
            s = copy.deepcopy(s)
            s[1] = S(lib_id)
            return s
    raise KeyError(lib_id)


def pinler(sym):
    """[(numara, ad, x, y, aci)] (kutuphane koordinati, y yukari; (x,y) elektrik ucu)."""
    out = []

    def gez(n):
        for c in n:
            if isinstance(c, list) and c:
                if c[0] == "pin":
                    at = bul(c, "at")[0]
                    out.append((str(bul(c, "number")[0][1]), str(bul(c, "name")[0][1]), float(at[1]), float(at[2]), float(at[3])))
                else:
                    gez(c)
    gez(sym)
    return out


def ozel_modul(ad, sol, sag, gen=20.32, aciklama="", ust=None):
    """Dikdortgen modul sembolu. sol/sag: [(numara, ad)]. Pin araligi 2,54 mm."""
    n = max(len(sol), len(sag))
    h = (n + 1) * 2.54 / 2
    h = round(h / 1.27) * 1.27
    w = gen / 2
    govde = [["rectangle", ["start", -w, h], ["end", w, -h], ["stroke", ["width", 0.254], ["type", "default"]],
              ["fill", ["type", "background"]]]]
    if ust:
        govde.append(["text", S(ust), ["at", 0, 0, 0], ["effects", ["font", ["size", 1.27, 1.27]]]])
    pins = []
    for taraf, liste in ((-1, sol), (1, sag)):
        for i, (num, pad) in enumerate(liste):
            y = h - 2.54 * (i + 1)
            pins.append(["pin", "passive", "line", ["at", taraf * (w + 2.54), round(y, 2), 0 if taraf < 0 else 180],
                         ["length", 2.54], ["name", S(pad), ["effects", ["font", ["size", 1.27, 1.27]]]],
                         ["number", S(num), ["effects", ["font", ["size", 1.27, 1.27]]]]])

    def prop(k, v, y, gizli=False):
        p = ["property", S(k), S(v), ["at", 0, y, 0], ["effects", ["font", ["size", 1.27, 1.27]]]]
        if gizli:
            p.insert(4, ["hide", "yes"])
        return p
    return ["symbol", S(f"cdtp:{ad}"), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"],
            prop("Reference", "A", h + 1.27), prop("Value", ad, -h - 1.27), prop("Footprint", "", 0, True),
            prop("Datasheet", "", 0, True), prop("Description", aciklama, 0, True),
            ["symbol", S(f"{ad}_0_1")] + govde, ["symbol", S(f"{ad}_1_1")] + pins]


def numarali(adlar, bas=1):
    return [(str(bas + i), a) for i, a in enumerate(adlar)]


OZEL = {
    "cdtp:ESP32_DevKitC_38": ozel_modul(
        "ESP32_DevKitC_38",
        numarali(["3V3", "EN", "GPIO36_VP", "GPIO39_VN", "GPIO34", "GPIO35", "GPIO32", "GPIO33", "GPIO25", "GPIO26",
                  "GPIO27", "GPIO14", "GPIO12", "GND", "GPIO13", "SD2", "SD3", "CMD", "5V"]),
        numarali(["GND", "GPIO23", "GPIO22", "TX_GPIO1", "RX_GPIO3", "GPIO21", "GND", "GPIO19", "GPIO18", "GPIO5",
                  "GPIO17", "GPIO16", "GPIO4", "GPIO0", "GPIO2", "GPIO15", "SD1", "SD0", "CLK"], 20),
        gen=30.48, aciklama="ESP32-WROOM-32D DevKitC 38 pin, ustten (USB asagida). Sol 1-19, sag 20-38 ustten asagi."),
    "cdtp:BTS7960_Modul": ozel_modul(
        "BTS7960_Modul", numarali(["RPWM", "LPWM", "R_EN", "L_EN", "R_IS", "L_IS", "VCC", "GND"]),
        numarali(["B+", "B-", "M+", "M-"], 9), gen=17.78, aciklama="IBT-2 BTS7960 43 A H-kopru modulu"),
    "cdtp:GY521_MPU6050": ozel_modul(
        "GY521_MPU6050", numarali(["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"]), [], gen=15.24,
        aciklama="GY-521 MPU6050 modulu (kart uzerinde 3,3 V LDO ve 4,7k pull-up)"),
    "cdtp:LM2596_Modul": ozel_modul("LM2596_Modul", [("1", "IN+"), ("2", "IN-")], [("3", "OUT+"), ("4", "OUT-")],
                                    gen=15.24, aciklama="LM2596 3 A dusurucu, cikis 5,0 V'a ayarli"),
    "cdtp:Motor_JGB37_Enkoder": ozel_modul(
        "Motor_JGB37_Enkoder", [("1", "M1"), ("6", "M2")], [("2", "GND"), ("3", "C1"), ("4", "C2"), ("5", "VCC")],
        gen=15.24, aciklama="JGB37-520 12 V 530 RPM, Hall enkoder (11 darbe/tur x 19 = 836 sayim/tur, 4x)"),
    "cdtp:IR_Alici_VS1838B": ozel_modul("IR_Alici_VS1838B", [("1", "OUT"), ("2", "GND"), ("3", "VCC")], [], gen=12.7,
                                        aciklama="38 kHz IR alici modulu, VS1838B (3,3 V'ta calisir)"),
    "cdtp:BMS_3S_HX3S01": ozel_modul("BMS_3S_HX3S01", numarali(["B-", "B1", "B2", "B+"]), [("5", "P-")], gen=12.7,
                                     aciklama="HX-3S-01 3S 10 A koruma karti; P+ = B+"),
    "cdtp:XT60": ozel_modul("XT60", [("1", "+"), ("2", "-")], [], gen=7.62, aciklama="XT60 konnektor"),
    "cdtp:WAGO_221_415": ozel_modul("WAGO_221_415", numarali(["", "", "", "", ""]), [], gen=7.62,
                                    aciklama="WAGO 221-415, 5 uc ic tarafta kisa devre"),
    "cdtp:AcilStop_NC": ozel_modul("AcilStop_NC", [("1", "NC1")], [("2", "NC2")], gen=10.16,
                                   aciklama="Chint NP2-BE102 mantar buton, 1 NC kontak, 10 A"),
    "cdtp:Pogo_Pim": ozel_modul("Pogo_Pim", [("1", "")], [], gen=5.08, aciklama="V-yuvadaki 5 mm pogo pim"),
}


def sembol(lib_id):
    return OZEL[lib_id] if lib_id in OZEL else std_sembol(lib_id)


# ---------------- devre ----------------
NC = None
# (ref, lib_id, deger, {pin numarasi: hat}, aci)
GRUPLAR = [
    ("PIL VE BMS", [
        ("BT1", "Device:Battery_Cell", "18650 hucre 1", {"1": "B1", "2": "B-"}, 90),
        ("BT2", "Device:Battery_Cell", "18650 hucre 2", {"1": "B2", "2": "B1"}, 90),
        ("BT3", "Device:Battery_Cell", "18650 hucre 3", {"1": "PACK+", "2": "B2"}, 90),
        ("U2", "cdtp:BMS_3S_HX3S01", "HX-3S-01", {"1": "B-", "2": "B1", "3": "B2", "4": "PACK+", "5": "PACK-"}, 0),
        ("J11", "cdtp:XT60", "XT60 disi (pil)", {"1": "PACK+", "2": "PACK-"}, 0),
        ("J12", "cdtp:XT60", "XT60 erkek (robot)", {"1": "BAT+", "2": "GND"}, 0),
    ]),
    ("12 V DAGITIM", [
        ("F1", "Device:Fuse", "5 A bicak", {"1": "BAT+", "2": "+12V"}, 90),
        ("X1", "cdtp:WAGO_221_415", "WAGO-12V", {str(i): "+12V" for i in range(1, 6)}, 0),
        ("S1", "cdtp:AcilStop_NC", "NP2-BE102 NC", {"1": "+12V", "2": "+12V_MOT"}, 0),
        ("C5", "Device:C_Polarized", "1000uF 25V", {"1": "+12V_MOT", "2": "GND"}, 270),
        ("X2", "cdtp:WAGO_221_415", "WAGO-GND (yildiz)", {str(i): "GND" for i in range(1, 6)}, 0),
        ("U3", "cdtp:LM2596_Modul", "LM2596 5,0 V", {"1": "+12V", "2": "GND", "3": "+5V", "4": "GND"}, 0),
    ]),
    ("ANA KART: ESP32 VE BESLEME", [
        ("U1", "cdtp:ESP32_DevKitC_38", "ESP32-WROOM-32D DevKitC", {
            "1": "+3V3", "2": NC, "3": "IR_L", "4": "IR_R", "5": "VCHG_ADC", "6": "VBAT_ADC", "7": "ENC_L_A",
            "8": "ENC_L_B", "9": "ENC_R_A", "10": "ENC_R_B", "11": "L_RPWM", "12": "L_LPWM", "13": NC, "14": "GND",
            "15": NC, "16": NC, "17": NC, "18": NC, "19": "+5V_ESP",
            "20": "GND", "21": "MOTOR_SENSE", "22": "I2C_SCL", "23": NC, "24": NC, "25": "I2C_SDA", "26": "GND",
            "27": "IMU_INT", "28": NC, "29": NC, "30": "R_LPWM", "31": "R_RPWM", "32": "MOTOR_EN", "33": NC, "34": NC,
            "35": NC, "36": NC, "37": NC, "38": NC}, 0),
        ("J1", "Connector_Generic:Conn_01x02", "5 V klemens", {"1": "+5V", "2": "GND"}, 0),
        ("C1", "Device:C_Polarized", "100uF 16V", {"1": "+5V", "2": "GND"}, 270),
        ("JP1", "Jumper:Jumper_2_Open", "USB'de cikar", {"1": "+5V", "2": "+5V_ESP"}, 0),
        ("R5", "Device:R", "10k", {"1": "MOTOR_EN", "2": "GND"}, 90),
    ]),
    ("ANA KART: KONNEKTOR, OLCUM", [
        ("J2", "Connector_Generic:Conn_01x05", "IMU", {"1": "+3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "IMU_INT"}, 0),
        ("J3", "Connector_Generic:Conn_01x05", "BTS sol", {"1": "L_RPWM", "2": "L_LPWM", "3": "MOTOR_EN", "4": "+3V3", "5": "GND"}, 0),
        ("J8", "Connector_Generic:Conn_01x05", "BTS sag", {"1": "R_RPWM", "2": "R_LPWM", "3": "MOTOR_EN", "4": "+3V3", "5": "GND"}, 0),
        ("J4", "Connector_Generic:Conn_01x04", "Enkoder sol", {"1": "+3V3", "2": "GND", "3": "ENC_L_A", "4": "ENC_L_B"}, 0),
        ("J5", "Connector_Generic:Conn_01x04", "Enkoder sag", {"1": "+3V3", "2": "GND", "3": "ENC_R_A", "4": "ENC_R_B"}, 0),
        ("J6", "Connector_Generic:Conn_01x03", "GENISLEME: IR goz sol (bos)", {"1": "+3V3", "2": "GND", "3": "IR_L"}, 0),
        ("J7", "Connector_Generic:Conn_01x03", "GENISLEME: IR goz sag (bos)", {"1": "+3V3", "2": "GND", "3": "IR_R"}, 0),
        ("J9", "Connector_Generic:Conn_01x02", "GENISLEME: sarj girisi (bos)", {"1": "+12V", "2": "CHG+"}, 0),
        ("J13", "Connector_Generic:Conn_01x04", "GENISLEME: I2C (ekran, 2. sensor)", {"1": "+3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA"}, 0),
        ("J10", "Connector_Generic:Conn_01x02", "Motor hatti klemens", {"1": "+12V_MOT", "2": NC}, 0),
        ("R1", "Device:R", "100k", {"1": "+12V", "2": "VBAT_ADC"}, 90),
        ("R2", "Device:R", "27k", {"1": "VBAT_ADC", "2": "GND"}, 90),
        ("C2", "Device:C", "100nF", {"1": "VBAT_ADC", "2": "GND"}, 90),
        ("R3", "Device:R", "100k", {"1": "CHG+", "2": "VCHG_ADC"}, 90),
        ("R4", "Device:R", "27k", {"1": "VCHG_ADC", "2": "GND"}, 90),
        ("C3", "Device:C", "100nF", {"1": "VCHG_ADC", "2": "GND"}, 90),
        ("R6", "Device:R", "100k", {"1": "+12V_MOT", "2": "MOTOR_SENSE"}, 90),
        ("R7", "Device:R", "33k", {"1": "MOTOR_SENSE", "2": "GND"}, 90),
        ("C4", "Device:C", "100nF", {"1": "MOTOR_SENSE", "2": "GND"}, 90),
    ]),
    ("MODULLER VE MOTORLAR", [
        ("A1", "cdtp:GY521_MPU6050", "GY-521", {"1": "+3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": NC,
                                                "6": NC, "7": "GND", "8": "IMU_INT"}, 0),
        ("A2", "cdtp:BTS7960_Modul", "BTS7960 sol", {"1": "L_RPWM", "2": "L_LPWM", "3": "MOTOR_EN", "4": "MOTOR_EN",
                                                     "5": NC, "6": NC, "7": "+3V3", "8": "GND", "9": "+12V_MOT",
                                                     "10": "GND", "11": "MOT_L+", "12": "MOT_L-"}, 0),
        ("A3", "cdtp:BTS7960_Modul", "BTS7960 sag", {"1": "R_RPWM", "2": "R_LPWM", "3": "MOTOR_EN", "4": "MOTOR_EN",
                                                     "5": NC, "6": NC, "7": "+3V3", "8": "GND", "9": "+12V_MOT",
                                                     "10": "GND", "11": "MOT_R+", "12": "MOT_R-"}, 0),
        ("M1", "cdtp:Motor_JGB37_Enkoder", "JGB37-520 sol", {"1": "MOT_L+", "6": "MOT_L-", "2": "GND", "3": "ENC_L_A",
                                                            "4": "ENC_L_B", "5": "+3V3"}, 0),
        ("M2", "cdtp:Motor_JGB37_Enkoder", "JGB37-520 sag", {"1": "MOT_R+", "6": "MOT_R-", "2": "GND", "3": "ENC_R_A",
                                                            "4": "ENC_R_B", "5": "+3V3"}, 0),
    ]),
]

NOTLAR = [
    "CDTP denge robotu - robot elektronigi (tek sayfa). Ayni adli etiketler ayni hattir.",
    "Guc: pil -> BMS -> XT60 -> F1 5 A -> WAGO-12V. Acil stop (NC) yalniz motor hattini keser; ESP32 acik kalir.",
    "KAPSAM: yalniz dengede kalan, pilli robot. GENISLEME konnektorleri (J6, J7, J9, J13) bos birakildi; sarj, IR goz, ekran sonradan buraya takilir.",
    "Sarj eklentisi (sonra): pogo + -> SR5100 anot, katot -> BAT+ (sigortadan once), pogo + ayrica J9-2. R3/R4 GPIO34'u 0 V'ta tutar.",
    "JP1: kod yuklerken (USB takiliyken) cikarin; LM2596 ile USB 5 V'u cakismasin.",
    "BTS7960 VCC = 3,3 V (ESP32 seviyesi). R_EN ve L_EN iki kartta GPIO4'e; R5 10k ile acilista motorlar kapali.",
    "MPU6050 AD0 -> GND (adres 0x68). GPIO36/39 yalniz giris (IR, PCNT 12,8 us suzgec).",
    "Bolucu: R1/R2 ve R3/R4 100k/27k (12,6 V -> 2,68 V); R6/R7 100k/33k (12,6 V -> 3,13 V).",
    "Kablo numaralari (W1-W44) ve pin sirasi: docs/robot.html bolum 04, 06, 07.",
]


# ---------------- yerlesim ----------------
def don(px, py, aci):
    a = round(aci) % 360
    return {0: (px, py), 90: (-py, px), 180: (-px, -py), 270: (py, -px)}[a]


def uc_noktalar(lib_id, aci):
    """{numara: (ex, ey, dx, dy)} ekran koordinati (y asagi), (dx,dy) disa dogru birim yon."""
    out = {}
    for num, ad, px, py, pa in pinler(sembol(lib_id)):
        rx, ry = don(px, py, aci)
        ic = (round(pa) + 180 + round(aci)) % 360  # disa bakan yon (kutuphane acisi)
        dx, dy = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}[ic]
        out[num] = (rx, -ry, dx, dy)
    return out


def kutu_olcu(lib_id, aci, baglar):
    xs, ys = [0.0], [0.0]
    for num, (ex, ey, dx, dy) in uc_noktalar(lib_id, aci).items():
        hat = baglar.get(num)
        uz = 2.54 + (len(hat) * 1.1 + 2 if hat else 1)
        xs += [ex, ex + dx * uz]
        ys += [ey, ey + dy * uz]
    return min(xs), max(xs), min(ys) - 3, max(ys) + 3


def izgara(v, g=1.27):
    return round(v / g) * g


def yerlestir(kagit_h):
    yer = []
    x = 20.0
    for baslik, ogeler in GRUPLAR:
        y0 = 40.0
        y = y0
        col_w = 0.0
        basliklar = [(baslik, x, 32.0)]
        for ref, lib, deger, bag, aci in ogeler:
            x0, x1, ys0, ys1 = kutu_olcu(lib, aci, bag)
            h = ys1 - ys0
            if y + h > kagit_h - 20 - 3.2 * len(NOTLAR) - 8 and y > y0:
                x += col_w + 8
                y = y0
                col_w = 0.0
            px, py = izgara(x - x0), izgara(y - ys0, 2.54)
            yer.append((ref, lib, deger, bag, aci, px, py))
            y += h + 6.5
            col_w = max(col_w, x1 - x0)
        yer_basliklar.extend(basliklar)
        x = max(x + col_w + 14, basliklar[0][1] + len(baslik) * 2.2 + 6)
    return yer, x


yer_basliklar = []


# ---------------- dosya ----------------
def efekt(justify=None, boy=1.27, kalin=False):
    f = ["font", ["size", boy, boy]]
    if kalin:
        f.append(["bold", "yes"])
    e = ["effects", f]
    if justify:
        e.append(["justify"] + justify)
    return e


def sema_yaz():
    for kagit in (("A3", 420.0, 297.0), ("A2", 594.0, 420.0), ("A1", 841.0, 594.0)):
        yer_basliklar.clear()
        yer, gen = yerlestir(kagit[2])
        if gen < kagit[1] - 10:
            break
    kok = uid("kok")
    libs = {}
    for _, lib, *_ in yer:
        libs[lib] = sembol(lib)
    govde = [["version", 20250610], ["generator", S("eeschema")], ["generator_version", S("10.0")],
             ["uuid", S(kok)], ["paper", S(kagit[0])],
             ["title_block", ["title", S("CDTP denge robotu - robot elektronigi")], ["date", S("2026-10-29")],
              ["rev", S("v1.3")], ["company", S("YTU EEF CDTP")],
              ["comment", 1, S("Uretici: tools/kicad_sema.py (elle duzenlemeyin; betigi degistirip yeniden uretin)")]],
             ["lib_symbols"] + list(libs.values())]
    ogeler = []
    for b, bx, by in yer_basliklar:
        ogeler.append(["text", S(b), ["exclude_from_sim", "no"], ["at", izgara(bx), izgara(by), 0],
                       efekt(["left", "bottom"], 2.54, True), ["uuid", S(uid("baslik", b))]])
    ny = kagit[2] - 12 - 3.2 * len(NOTLAR)
    for i, t in enumerate(NOTLAR):
        ogeler.append(["text", S(t), ["exclude_from_sim", "no"], ["at", 20.32, izgara(ny + 3.2 * i), 0],
                       efekt(["left", "bottom"], 1.6), ["uuid", S(uid("not", i))]])
    for ref, lib, deger, bag, aci, px, py in yer:
        sym = sembol(lib)
        pins = pinler(sym)
        props = []
        for k, v, dy, gizli in (("Reference", ref, -1, False), ("Value", deger, 1, False), ("Footprint", "", 0, True),
                                ("Datasheet", "", 0, True), ("Description", "", 0, True)):
            p = ["property", S(k), S(v), ["at", px, py, 0]]
            if gizli:
                p.append(["hide", "yes"])
            p.append(efekt())
            props.append(p)
        # referans/deger konumu: kutunun ustu ve alti
        x0, x1, ys0, ys1 = kutu_olcu(lib, aci, bag)
        fa = aci % 180
        uy = [e[1] for e in uc_noktalar(lib, aci).values()]
        props[0][3] = ["at", px, izgara(py + min(uy) - 4.0, 0.635), fa]
        props[1][3] = ["at", px, izgara(py + max(uy) + 4.0, 0.635), fa]
        s = ["symbol", ["lib_id", S(lib)], ["at", px, py, aci], ["unit", 1], ["exclude_from_sim", "no"],
             ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", S(uid("sym", ref))]] + props
        for num, *_ in pins:
            s.append(["pin", S(num), ["uuid", S(uid("pin", ref, num))]])
        s.append(["instances", ["project", S(PROJE), ["path", S("/" + kok), ["reference", S(ref)], ["unit", 1]]]])
        ogeler.append(s)
        for num, (ex, ey, dx, dy) in uc_noktalar(lib, aci).items():
            ax, ay = px + ex, py + ey
            hat = bag.get(num, "YOK")
            if hat == "YOK":
                raise ValueError(f"{ref} pin {num} tanimsiz")
            if hat is None:
                ogeler.append(["no_connect", ["at", ax, ay], ["uuid", S(uid("nc", ref, num))]])
                continue
            bx, by = ax + 2.54 * dx, ay + 2.54 * dy
            ogeler.append(["wire", ["pts", ["xy", ax, ay], ["xy", bx, by]], ["stroke", ["width", 0], ["type", "default"]],
                           ["uuid", S(uid("w", ref, num))]])
            la = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            js = ["left", "bottom"] if la in (0, 90) else ["right", "bottom"]
            ogeler.append(["label", S(hat), ["at", bx, by, la], efekt(js), ["uuid", S(uid("l", ref, num))]])
    govde += ogeler
    govde += [["sheet_instances", ["path", S("/"), ["page", S("1")]]], ["embedded_fonts", "no"]]
    OUT.mkdir(exist_ok=True)
    (OUT / f"{PROJE}.kicad_sch").write_text(yaz(["kicad_sch"] + govde) + "\n", encoding="utf-8")
    # proje dosyalari ve ozel kutuphane
    (OUT / f"{PROJE}.kicad_pro").write_text(json.dumps({"meta": {"filename": f"{PROJE}.kicad_pro", "version": 3}}, indent=2),
                                            encoding="utf-8")
    kut = ["kicad_symbol_lib", ["version", 20251024], ["generator", S("cdtp_kicad_sema")], ["generator_version", S("10.0")]]
    for k, v in OZEL.items():
        v = copy.deepcopy(v)
        v[1] = S(k.split(":")[1])
        kut.append(v)
    (OUT / "cdtp.kicad_sym").write_text(yaz(kut) + "\n", encoding="utf-8")
    satir = ['\t(lib (name "cdtp")(type "KiCad")(uri "${KIPRJMOD}/cdtp.kicad_sym")(options "")(descr "CDTP robot modulleri"))']
    for lib in sorted({k.split(":")[0] for k in libs if not k.startswith("cdtp:")}):
        satir.append(f'\t(lib (name "{lib}")(type "KiCad")(uri "${{KICAD10_SYMBOL_DIR}}/{lib}.kicad_sym")(options "")(descr ""))')
    (OUT / "sym-lib-table").write_text("(sym_lib_table\n\t(version 7)\n" + "\n".join(satir) + "\n)\n", encoding="utf-8")
    return kagit, len(yer)


# ---------------- denetim ----------------
def cli(*a):
    r = subprocess.run([str(CLI), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def netlist_oku():
    t = ET.parse(OUT / "netlist.xml").getroot()
    nets = {}
    for n in t.iter("net"):
        nets[n.get("name").lstrip("/")] = {(nd.get("ref"), nd.get("pin")) for nd in n.iter("node")}
    pin_ad = {}
    for c in t.iter("comp"):
        pass
    for lp in t.iter("libpart"):
        for p in lp.iter("pin"):
            pin_ad[(lp.get("lib") + ":" + lp.get("part"), p.get("num"))] = p.get("name")
    return nets


def denetle():
    sonuc = []

    def ekle(ad, ok, detay):
        sonuc.append((ad, "GECTI" if ok else "KALDI", detay))

    kod, cikti = cli("sch", "erc", "--format", "json", "--severity-all", "-o", str(OUT / "erc.json"), str(OUT / f"{PROJE}.kicad_sch"))
    erc = json.loads((OUT / "erc.json").read_text(encoding="utf-8"))
    ihlal = [v for s in erc.get("sheets", []) for v in s.get("violations", [])]
    hata = [v for v in ihlal if v.get("severity") == "error"]
    uyari = [v for v in ihlal if v.get("severity") == "warning"]
    ekle("KiCad ERC", not hata and not uyari,
         f"{len(hata)} hata, {len(uyari)} uyari" + ("" if not ihlal else ": " + "; ".join(
             f"{v['type']}: {v['description']}" for v in ihlal[:8])))
    cli("sch", "export", "netlist", "--format", "kicadxml", "-o", str(OUT / "netlist.xml"), str(OUT / f"{PROJE}.kicad_sch"))
    nets = netlist_oku()
    hat_of = {}
    for n, uclar in nets.items():
        for u in uclar:
            hat_of[u] = n

    # 1) ESP32 pinleri pins.h ile
    pins_h = (ROOT / "firmware/robot/src/pins.h").read_text(encoding="utf-8")
    sabit = {k: int(v) for k, v in re.findall(r"constexpr int (PIN_\w+) = (\d+);", pins_h)}
    esp_pin = {}
    for num, ad, *_ in pinler(OZEL["cdtp:ESP32_DevKitC_38"]):
        m = re.match(r"(?:\w+_)?GPIO(\d+)", ad)
        if m:
            esp_pin[int(m.group(1))] = num
    beklenen = {  # pins.h sabiti -> (hat, ulasmasi gereken uclar)
        "PIN_SDA": ("I2C_SDA", [("A1", "4"), ("J2", "4")]), "PIN_SCL": ("I2C_SCL", [("A1", "3"), ("J2", "3")]),
        "PIN_IMU_INT": ("IMU_INT", [("A1", "8"), ("J2", "5")]),
        "PIN_L_RPWM": ("L_RPWM", [("A2", "1"), ("J3", "1")]), "PIN_L_LPWM": ("L_LPWM", [("A2", "2"), ("J3", "2")]),
        "PIN_R_RPWM": ("R_RPWM", [("A3", "1"), ("J8", "1")]), "PIN_R_LPWM": ("R_LPWM", [("A3", "2"), ("J8", "2")]),
        "PIN_MOTOR_EN": ("MOTOR_EN", [("A2", "3"), ("A2", "4"), ("A3", "3"), ("A3", "4"), ("J3", "3"), ("J8", "3"), ("R5", "1")]),
        "PIN_ENC_L_A": ("ENC_L_A", [("M1", "3"), ("J4", "3")]), "PIN_ENC_L_B": ("ENC_L_B", [("M1", "4"), ("J4", "4")]),
        "PIN_ENC_R_A": ("ENC_R_A", [("M2", "3"), ("J5", "3")]), "PIN_ENC_R_B": ("ENC_R_B", [("M2", "4"), ("J5", "4")]),
        "PIN_IR_L": ("IR_L", [("J6", "3")]), "PIN_IR_R": ("IR_R", [("J7", "3")]),
        "PIN_VBAT": ("VBAT_ADC", [("R1", "2"), ("R2", "1"), ("C2", "1")]),
        "PIN_VCHG": ("VCHG_ADC", [("R3", "2"), ("R4", "1"), ("C3", "1")]),
        "PIN_MOTOR_SENSE": ("MOTOR_SENSE", [("R6", "2"), ("R7", "1"), ("C4", "1")]),
    }
    eksik = []
    for k, gpio in sabit.items():
        if k == "PIN_LED":
            continue
        if k not in beklenen:
            eksik.append(f"{k} semada yok")
            continue
        net, uclar = beklenen[k]
        u = ("U1", esp_pin[gpio])
        if hat_of.get(u) != net:
            eksik.append(f"{k}=GPIO{gpio}: ESP32 pini {u[1]} hatti {hat_of.get(u)} (beklenen {net})")
        for uc in uclar:
            if hat_of.get(uc) != net:
                eksik.append(f"{k}: {uc[0]}.{uc[1]} hatti {hat_of.get(uc)}")
    ekle("ESP32 pinleri = firmware/robot/src/pins.h", not eksik,
         f"{len(sabit) - 1} pin sabiti, her biri ESP32 + ana kart konnektoru + modul ucunda dogru" if not eksik else "; ".join(eksik))

    # 2) guc ve kablo listesi (robot_src.html bolum 03/06)
    guc = {
        "W1 hucre1- -> BMS B-": [("BT1", "2"), ("U2", "1")], "W2 B1": [("BT1", "1"), ("BT2", "2"), ("U2", "2")],
        "W3 B2": [("BT2", "1"), ("BT3", "2"), ("U2", "3")], "W4/W5 B+ -> XT60 disi +": [("BT3", "1"), ("U2", "4"), ("J11", "1")],
        "W6 P- -> XT60 disi -": [("U2", "5"), ("J11", "2")],
        "W7/W21 XT60 erkek + -> sigorta, diyot katot": [("J12", "1"), ("F1", "1")],
        "W8/W9/W12/W19 sigortali 12 V": [("F1", "2"), ("S1", "1"), ("U3", "1"), ("J9", "1"), ("R1", "1"), ("X1", "1")],
        "W10/W11/W41/W43 acil stop sonrasi": [("S1", "2"), ("A2", "9"), ("A3", "9"), ("C5", "1"), ("J10", "1"), ("R6", "1")],
        "W13-W15/W22/W42 GND": [("J12", "2"), ("A2", "10"), ("A3", "10"), ("U3", "2"), ("C5", "2"), ("X2", "1"),
                                 ("U3", "4"), ("J1", "2"), ("U1", "14"), ("U1", "20"), ("U1", "26"), ("A1", "7")],
        "W16 sol motor": [("A2", "11"), ("M1", "1")], "W16 sol motor -": [("A2", "12"), ("M1", "6")],
        "W17 sag motor": [("A3", "11"), ("M2", "1")], "W17 sag motor -": [("A3", "12"), ("M2", "6")],
        "W18 LM2596 -> J1 5 V -> JP1": [("U3", "3"), ("J1", "1"), ("C1", "1"), ("JP1", "1")],
        "JP1 -> ESP32 5V": [("JP1", "2"), ("U1", "19")],
        "W20/W23 sarj girisi (bos) J9-2 -> R3": [("J9", "2"), ("R3", "1")],
        "3V3 hatti (IMU, BTS VCC, enkoder, genisleme)": [("U1", "1"), ("A1", "1"), ("A2", "7"), ("A3", "7"), ("M1", "5"), ("M2", "5"),
                                                  ("J13", "1"), ("J2", "1"), ("J3", "4"), ("J8", "4"),
                                                  ("J4", "1"), ("J5", "1"), ("J6", "1"), ("J7", "1")],
    }
    hata2 = []
    for ad, uclar in guc.items():
        h = {hat_of.get(u) for u in uclar}
        if len(h) != 1 or None in h:
            hata2.append(f"{ad}: {sorted(map(str, h))}")
    # birbirinden ayri kalmasi gerekenler
    ayri = [("PACK+", "BAT+"), ("+12V", "+12V_MOT"), ("+5V", "+5V_ESP"), ("CHG+", "BAT+"), ("+12V", "+3V3")]
    for a, b in ayri:
        if a not in nets or b not in nets:
            hata2.append(f"{a}/{b} hatti yok")
    ekle("Guc ve kablo listesi (W1-W44)", not hata2, f"{len(guc)} baglanti grubu dogru; acil stop, JP1 ve XT60 hatlari ayri"
         if not hata2 else "; ".join(hata2))

    # 3) bolucu oranlari (pins.h DIVIDER ile)
    deg = {}
    sch = (OUT / f"{PROJE}.kicad_sch").read_text(encoding="utf-8")
    for ref, _, d, *_ in [o for _, g in GRUPLAR for o in g]:
        deg[ref] = d

    def ohm(v):
        return float(v.lower().replace("k", "")) * 1000
    oran = (ohm(deg["R1"]) + ohm(deg["R2"])) / ohm(deg["R2"])
    m = re.search(r"DIVIDER = \(([\d.]+)f \+ ([\d.]+)f\) / ([\d.]+)f", pins_h)
    fw = (float(m.group(1)) + float(m.group(2))) / float(m.group(3))
    v_ms = 12.6 * ohm(deg["R7"]) / (ohm(deg["R6"]) + ohm(deg["R7"]))
    ekle("Bolucu degerleri", abs(oran - fw) < 1e-6 and v_ms < 3.3 and 12.6 / oran < 3.1,
         f"R1/R2 orani {oran:.3f} = firmware DIVIDER {fw:.3f}; 12,6 V -> {12.6/oran:.2f} V (ADC 11 dB); R6/R7 -> {v_ms:.2f} V < 3,3 V")

    # 4) her hat en az iki uca gidiyor, bos pinler isaretli
    tek = [n for n, u in nets.items() if len(u) < 2 and not n.startswith("unconnected")]
    ekle("Tek uclu hat yok", not tek, f"{len(nets)} hat" if not tek else ", ".join(tek))
    return sonuc


def main():
    if not CLI.exists():
        print("KiCad 10 bulunamadi:", CLI)
        return 2
    kagit, n = sema_yaz()
    sonuc = denetle()
    cli("sch", "export", "pdf", "-o", str(OUT / f"{PROJE}.pdf"), str(OUT / f"{PROJE}.kicad_sch"))
    cli("sch", "export", "svg", "-o", str(OUT), str(OUT / f"{PROJE}.kicad_sch"))
    svg = (OUT / f"{PROJE}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg, count=1)  # web yayini DTD'siz SVG ister
    (ROOT / "docs/img/sema_kicad.svg").write_text(svg, encoding="utf-8")
    ok = all(s == "GECTI" for _, s, _ in sonuc)
    with open(OUT / "sema_kontrol.md", "w", encoding="utf-8") as f:
        f.write(f"# KiCad sema denetimi\n\n`python tools/kicad_sema.py` uretir. Kagit {kagit[0]}, {n} sembol.\n\n"
                "| Kontrol | Sonuc | Ayrinti |\n|---|---|---|\n")
        for a, s, d in sonuc:
            f.write(f"| {a} | {s} | {d} |\n")
    print(f"kagit {kagit[0]}, {n} sembol")
    for a, s, d in sonuc:
        print(f"{s:6s} {a}: {d}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
