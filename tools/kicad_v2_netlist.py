"""TB6612 surumu ana kart (v2) icin netlist uretir -> elektronik/pcb_v2/netlist.xml
Calistir: python tools/kicad_v2_netlist.py
Baglantilar docs/breadboard_uret.py ile ayni tek breadboard tasarimidir (docs/breadboard_dogrula.py ile dogrulandi).
Burada ek olarak her ESP32 pini firmware/robot/src/pins.h sabitleriyle karsilastirilir."""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "elektronik" / "pcb_v2"

# ESP32 DevKitC 38 pin: sol sira 1-19, sag sira 20-38 (ustten gorunum; tools/kicad_sema.py ile ayni numaralama)
ESP_L = ["3V3", "EN", "GPIO36", "GPIO39", "GPIO34", "GPIO35", "GPIO32", "GPIO33", "GPIO25", "GPIO26", "GPIO27", "GPIO14",
         "GPIO12", "GND", "GPIO13", "SD2", "SD3", "CMD", "5V"]
ESP_R = ["GND", "GPIO23", "GPIO22", "TX", "RX", "GPIO21", "GND", "GPIO19", "GPIO18", "GPIO5", "GPIO17", "GPIO16", "GPIO4",
         "GPIO0", "GPIO2", "GPIO15", "SD1", "SD0", "CLK"]
ESP_NET = {  # pin adi -> hat
    "3V3": "+3V3", "GND": "GND", "5V": "+5V_ESP",
    "GPIO36": "IR_L", "GPIO39": "IR_R", "GPIO32": "ENC_L_A", "GPIO33": "ENC_L_B", "GPIO25": "ENC_R_A", "GPIO26": "ENC_R_B",
    "GPIO27": "L_RPWM", "GPIO14": "L_LPWM", "GPIO16": "R_RPWM", "GPIO17": "R_LPWM", "GPIO4": "MOTOR_EN",
    "GPIO22": "I2C_SCL", "GPIO21": "I2C_SDA", "GPIO19": "IMU_INT",
}
u1 = {}
for i, n in enumerate(ESP_L + ESP_R, 1):
    if n in ESP_NET:
        u1[str(i)] = ESP_NET[n]

TB_T = ["PWMA", "AIN2", "AIN1", "STBY", "BIN1", "BIN2", "PWMB", "GND"]
TB_B = ["VM", "VCC", "GND", "AO1", "AO2", "BO2", "BO1", "GND"]
TB_NET = {"PWMA": "+3V3", "PWMB": "+3V3", "VCC": "+3V3", "VM": "+12V", "GND": "GND", "AIN1": "L_RPWM", "AIN2": "L_LPWM",
          "BIN1": "R_RPWM", "BIN2": "R_LPWM", "STBY": "MOTOR_EN", "AO1": "MOT_L+", "AO2": "MOT_L-", "BO1": "MOT_R+",
          "BO2": "MOT_R-"}
a2 = {str(i): TB_NET[n] for i, n in enumerate(TB_T + TB_B, 1)}

MPU = ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"]
MPU_NET = {"VCC": "+3V3", "GND": "GND", "SCL": "I2C_SCL", "SDA": "I2C_SDA", "AD0": "GND", "INT": "IMU_INT"}
a1 = {str(i): MPU_NET[n] for i, n in enumerate(MPU, 1) if n in MPU_NET}

# (ref, deger, {pin: hat})
COMPS = [
    ("U1", "ESP32-WROOM-32D DevKitC 38 pin", u1),
    ("A1", "GY-521 MPU6050 (1x8 soket)", a1),
    ("A2", "TB6612FNG modul (2x8 soket)", a2),
    ("U3", "LM2596 mini 5,0 V (4 ped)", {"1": "+12V", "2": "GND", "3": "+5V", "4": "GND"}),
    ("J1", "12V ADAPTOR GIRIS klemens", {"1": "ADP+", "2": "GND"}),
    ("F1", "PTC sigorta 3 A", {"1": "ADP+", "2": "FUSED"}),
    ("J2", "ANAHTAR klemens", {"1": "FUSED", "2": "+12V"}),
    ("C1", "1000uF 25V", {"1": "+12V", "2": "GND"}),
    ("R1", "10k", {"1": "MOTOR_EN", "2": "GND"}),
    ("JP1", "USB'de cikar", {"1": "+5V", "2": "+5V_ESP"}),
    ("J3", "SOL MOTOR 6 pin", {"1": "MOT_L+", "2": "GND", "3": "ENC_L_A", "4": "ENC_L_B", "5": "+3V3", "6": "MOT_L-"}),
    ("J4", "SAG MOTOR 6 pin", {"1": "MOT_R+", "2": "GND", "3": "ENC_R_A", "4": "ENC_R_B", "5": "+3V3", "6": "MOT_R-"}),
    ("J5", "IR SOL", {"1": "+3V3", "2": "GND", "3": "IR_L"}),
    ("J6", "IR SAG", {"1": "+3V3", "2": "GND", "3": "IR_R"}),
]


def yaz():
    nets = {}
    for ref, _, pins in COMPS:
        for p, n in pins.items():
            nets.setdefault(n, []).append((ref, p))
    root = ET.Element("export", version="E")
    comps = ET.SubElement(root, "components")
    for ref, val, _ in COMPS:
        c = ET.SubElement(comps, "comp", ref=ref)
        ET.SubElement(c, "value").text = val
    ne = ET.SubElement(root, "nets")
    for code, name in enumerate(sorted(nets), 1):
        n = ET.SubElement(ne, "net", code=str(code), name="/" + name)
        for ref, p in nets[name]:
            ET.SubElement(n, "node", ref=ref, pin=p)
    OUT.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(OUT / "netlist.xml", encoding="utf-8", xml_declaration=True)
    return nets


def denetle(nets):
    sorun = []
    pins_h = (ROOT / "firmware/robot/src/pins.h").read_text(encoding="utf-8")
    sabit = {k: int(v) for k, v in re.findall(r"constexpr int (PIN_\w+) = (\d+);", pins_h)}
    beklenen = {"PIN_SDA": "I2C_SDA", "PIN_SCL": "I2C_SCL", "PIN_IMU_INT": "IMU_INT", "PIN_L_RPWM": "L_RPWM",
                "PIN_L_LPWM": "L_LPWM", "PIN_R_RPWM": "R_RPWM", "PIN_R_LPWM": "R_LPWM", "PIN_MOTOR_EN": "MOTOR_EN",
                "PIN_ENC_L_A": "ENC_L_A", "PIN_ENC_L_B": "ENC_L_B", "PIN_ENC_R_A": "ENC_R_A", "PIN_ENC_R_B": "ENC_R_B",
                "PIN_IR_L": "IR_L", "PIN_IR_R": "IR_R"}
    esp = {n: str(i) for i, n in enumerate(ESP_L + ESP_R, 1)}
    hat_of = {}
    for n, uclar in nets.items():
        for u in uclar:
            hat_of[u] = n
    for k, hat in beklenen.items():
        if k not in sabit:
            sorun.append(f"{k} pins.h'te yok")
            continue
        pin = esp.get(f"GPIO{sabit[k]}")
        if hat_of.get(("U1", pin)) != hat:
            sorun.append(f"{k}=GPIO{sabit[k]}: kart hatti {hat_of.get(('U1', pin))}, beklenen {hat}")
    for n, uclar in nets.items():
        if len(uclar) < 2:
            sorun.append(f"tek uclu hat: {n}")
    ayri = [("+12V", "+3V3"), ("+12V", "+5V"), ("+5V", "+3V3"), ("ADP+", "FUSED"), ("FUSED", "+12V"), ("+5V", "+5V_ESP")]
    for a, b in ayri:
        if a not in nets or b not in nets:
            sorun.append(f"{a}/{b} hatti yok")
    return sorun


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    nets = yaz()
    s = denetle(nets)
    print(f"{len(COMPS)} parca, {len(nets)} hat -> {OUT / 'netlist.xml'}")
    print("GECTI: ESP32 pinleri = pins.h, tek uclu hat yok, guc hatlari ayri" if not s else "KALDI: " + "; ".join(s))
    sys.exit(1 if s else 0)
