"""Cizilen/yazilan belgeler ile kodun tutarlilik denetimi.

Karsilastirir:
  1. firmware/robot/src/pins.h  <->  takim sitesinin pin semasi (tools/ref/site_wiring.js)
  2. pins.h                     <->  docs/robot_src.html pin tablosu ve ana kart header siralari
  3. cdtp_config.h / gains.h    <->  belgelerde yazan sayilar
  4. links.h BLE UUID'leri      <->  docs/BLE_PROTOKOL.md
  5. bolucu oranlari            <->  pins.h DIVIDER ve belge
Cikti: docs/tutarlilik.md (+ ekrana ozet). Hata varsa cikis kodu 1.
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[1]
rd = lambda p: (ROOT / p).read_text(encoding="utf-8")

rows = []  # (konu, beklenen, bulunan, durum)


def check(topic, expected, found, ok=None):
    if ok is None:
        ok = str(expected) == str(found)
    rows.append((topic, str(expected), str(found), "uygun" if ok else "UYUMSUZ"))


pins_h = rd("firmware/robot/src/pins.h")
pins = {m[0]: int(m[1]) for m in re.findall(r"constexpr int (PIN_\w+) = (\d+);", pins_h)}

# ---- 1. site pin semasi ----
site = rd("tools/ref/site_wiring.js")
robot_block = site[site.index("export const ROBOT_PINS"):site.index("export const GLOVE_PINS")]
site_map = {}
for name, gpio in re.findall(r"\['([^']+)', 'GPIO(\d+)", robot_block):
    site_map.setdefault(name, []).append(int(gpio))
expect_site = {
    "SDA": ("PIN_SDA",), "SCL": ("PIN_SCL",), "INT": ("PIN_IMU_INT",),
    "OUT": ("PIN_IR_L", "PIN_IR_R"),
    "RPWM": ("PIN_L_RPWM", "PIN_R_RPWM"), "LPWM": ("PIN_L_LPWM", "PIN_R_LPWM"),
    "R_EN + L_EN": ("PIN_MOTOR_EN", "PIN_MOTOR_EN"),
    "C1 (A)": ("PIN_ENC_L_A", "PIN_ENC_R_A"), "C2 (B)": ("PIN_ENC_L_B", "PIN_ENC_R_B"),
}
for sig, names in expect_site.items():
    got = site_map.get(sig, [])
    want = [pins[n] for n in names]
    check(f"Site semasi: {sig}", want, got, sorted(want) == sorted(got))
meas = dict(re.findall(r"t: '(Pil gerilimi|Şarj algılama)'.*?'GPIO(\d+)'", robot_block))
check("Site semasi: pil olcumu", pins["PIN_VBAT"], meas.get("Pil gerilimi"))
check("Site semasi: sarj algilama", pins["PIN_VCHG"], meas.get("Şarj algılama"))

# ---- 2. robot_src.html pin tablosu ve header siralari ----
doc = rd("docs/robot_src.html")
sig_sec = doc[doc.index('id="sinyal"'):doc.index('id="anakart"')]
tbl = {}
for pinsTxt, task in re.findall(r'<td class="num">([\d ,/]+)</td><td>([^<]+)</td>', sig_sec):
    tbl[task.strip()] = [int(x) for x in re.findall(r"\d+", pinsTxt)]
doc_expect = {
    "MPU6050 INT": [pins["PIN_IMU_INT"]],
    "I2C SDA / SCL": [pins["PIN_SDA"], pins["PIN_SCL"]],
    "Sol / sağ RPWM, LPWM": [pins["PIN_L_RPWM"], pins["PIN_L_LPWM"], pins["PIN_R_RPWM"], pins["PIN_R_LPWM"]],
    "EN (iki kart)": [pins["PIN_MOTOR_EN"]],
    "Enkoder A, B": [pins["PIN_ENC_L_A"], pins["PIN_ENC_L_B"], pins["PIN_ENC_R_A"], pins["PIN_ENC_R_B"]],
    "IR göz sol / sağ": [pins["PIN_IR_L"], pins["PIN_IR_R"]],
    "Pil / şarj pimi gerilimi": [pins["PIN_VBAT"], pins["PIN_VCHG"]],
    "Acil stop sonrası motor hattı": [pins["PIN_MOTOR_SENSE"]],
    "Karttaki LED": [pins["PIN_LED"]],
}
for task, want in doc_expect.items():
    check(f"Belge pin tablosu: {task}", want, tbl.get(task))

hdr_sec = doc[doc.index('id="anakart"'):doc.index('id="kablo"')]
headers = dict(re.findall(r'<td class="num">(J\d+)</td><td>([^<]+)</td>', hdr_sec))
hdr_expect = {
    "J2": f"3V3, GND, G{pins['PIN_SCL']}, G{pins['PIN_SDA']}, G{pins['PIN_IMU_INT']}",
    "J3": f"G{pins['PIN_L_RPWM']}, G{pins['PIN_L_LPWM']}, G{pins['PIN_MOTOR_EN']}, 3V3, GND",
    "J8": f"G{pins['PIN_R_RPWM']}, G{pins['PIN_R_LPWM']}, G{pins['PIN_MOTOR_EN']}, 3V3, GND",
    "J4": f"3V3, GND, G{pins['PIN_ENC_L_A']}, G{pins['PIN_ENC_L_B']}",
    "J5": f"3V3, GND, G{pins['PIN_ENC_R_A']}, G{pins['PIN_ENC_R_B']}",
}
for j, want in hdr_expect.items():
    check(f"Ana kart {j} pin sirasi", want, headers.get(j, "").strip())
ir = re.search(r'<td class="num">J6 / J7</td><td>3V3, GND, G(\d+) / G(\d+)</td>', hdr_sec)
check("Ana kart J6/J7", [pins["PIN_IR_L"], pins["PIN_IR_R"]], [int(ir[1]), int(ir[2])] if ir else None)

# ---- 3. sayilar ----
cfg = rd("common/cdtp_core/src/cdtp_config.h")
num = lambda name: float(re.search(rf"{name}\s*=\s*([\d.]+)f", cfg)[1])
gains = rd("common/cdtp_core/src/gains.h")
g = {k: float(v) for k, v in re.findall(r"constexpr float (\w+) = (-?[\d.]+)f;", gains)}
plan = rd("docs/plan.html")
check("Iz genisligi (kod <-> belge 190 mm)", 190, round(num("TRACK_WIDTH_M") * 1000), "iz 190" in doc and num("TRACK_WIDTH_M") == 0.19)
check("Enkoder sayim/tur (kod <-> belge 836)", 836, int(num("ENC_COUNTS_PER_REV")), "836" in doc)
check("Dusme acisi 40 deg", 40, int(num("FALL_ANGLE_DEG")), "40°" in doc)
check("Dengeye girme +-3 deg, 0,5 s", "3 / 0.5", f"{num('ARM_ANGLE_DEG'):g} / {num('ARM_HOLD_S'):g}", "±3° içinde 0,5 s" in doc)
check("Eldiven zaman asimi 0,3 s", 0.3, num("GLOVE_TIMEOUT_S"), num("GLOVE_TIMEOUT_S") == 0.3 and "0,3 s paket" in doc)
check("Adim 0,5 m / 90 deg", "0.5 / 90", f"{num('STEP_DIST_M'):g} / {num('TURN_ANGLE_DEG'):g}", "0,5 m" in doc and "90°" in doc)
check("Sarj algilama esigi 9 V", 9, num("CHARGE_DETECT_V"), "9 V" in doc)
check("Butunlesik gorevde bos bekleme 6 s", 6, num("DOCK_IDLE_S"), "6 s" in plan)
fmt = lambda v: f"{abs(v):.1f}".replace(".", ",")
plan_gain = f"u = {fmt(g['K_X'])}·x + {fmt(g['K_V'])}·v + {fmt(g['K_TH'])}·θ + {fmt(g['K_OM'])}·ω"
check("LQR kazanclari (gains.h <-> plan sayfasi)", plan_gain, "plan sayfasinda var" if plan_gain in plan else "YOK", plan_gain in plan)

# ---- 4. BLE ----
links = rd("firmware/robot/src/links.h")
ble_doc = rd("docs/BLE_PROTOKOL.md")
for name in ("CDTP_SVC_UUID", "CDTP_TELEM_UUID", "CDTP_CMD_UUID"):
    u = re.search(rf'#define {name} "([0-9a-f-]+)"', links)[1]
    check(f"BLE {name}", u, "belgede var" if u in ble_doc else "YOK", u in ble_doc)

# ---- 5. bolucu ----
div = re.search(r"DIVIDER = \(([\d.]+)f \+ ([\d.]+)f\) / ([\d.]+)f", pins_h)
check("Pil boluculeri 100k/27k", "100/27", f"{float(div[1]):g}/{float(div[2]):g}", "100k/27k" in doc)
v_top = 12.6 * float(div[2]) / (float(div[1]) + float(div[2]))
check("12,6 V -> ADC gerilimi < 3,1 V", "< 3.1", f"{v_top:.2f}", v_top < 3.1)
v_ms = 12.6 * 33 / 133
check("Motor hatti bolucu 100k/33k -> < 3,3 V", "< 3.3", f"{v_ms:.2f}", v_ms < 3.3 and "100k/33k" in doc)

# ---- rapor ----
bad = [r for r in rows if r[3] != "uygun"]
lines = ["# Belge ve kod tutarlilik denetimi", "", f"{len(rows)} kontrol, {len(bad)} uyumsuz.", "",
         "| Konu | Beklenen | Bulunan | Durum |", "|---|---|---|---|"]
lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
(ROOT / "docs/tutarlilik.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
for r in rows:
    print(f"[{r[3]:7s}] {r[0]}: beklenen {r[1]} / bulunan {r[2]}")
print(f"\n{len(rows)} kontrol, {len(bad)} uyumsuz")
sys.exit(1 if bad else 0)
