"""Breadboard baglanti simulasyonu (kural denetimi).
Calistir: python docs/breadboard_dogrula.py
Cizimdeki her kablo ucunu ve modul pinini breadboard seritlerine koyar, aglari (net) birlestirir,
sonra beklenen aglarla karsilastirir: kisa devre, kopuk hat, cakisan delik, yanlis ray.
Bu bir fizik simulasyonu DEGIL: devrenin elektrik olarak dogru baglandigini kanitlar."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import breadboard_uret as B

B.svg_main()                                   # ENDS dolar

# ---- serit modeli ----
def strip(col, row):
    if row in ("T+", "T-", "B+", "B-"):
        return row                              # ray bastan sona tek ag (kopuk degil varsayimi)
    return (col, "top" if row in "abcde" else "bot")


# ---- modul pinleri: (sutun, satir) -> ad ----
GPIO = {"VP": "GPIO36", "VN": "GPIO39"}
pins = {}
def esp_name(n):
    return "ESP." + (GPIO.get(n) or ("GPIO" + n if n.isdigit() else n))
for i, n in enumerate(B.ESP_T):
    pins[(B.ecol(i), "a")] = esp_name(n)
for i, n in enumerate(B.ESP_B):
    pins[(B.ecol(i), "i")] = esp_name(n)
for i, n in enumerate(B.TB_T):
    pins[(B.tcol(i), "d")] = "TB." + n
for i, n in enumerate(B.TB_B):
    pins[(B.tcol(i), "h")] = "TB." + n
for i, n in enumerate(B.MPU):
    pins[(B.mcol(i), "c")] = "MPU." + n
pins.update(B.EXTRA_PINS)

# kart disi uclar: kablo no -> terminal
OFF = {20: "MOTL.M1", 21: "MOTL.M2", 22: "MOTR.M1", 23: "MOTR.M2",
       24: "ENCL.GND", 25: "ENCL.VCC", 26: "ENCL.A", 27: "ENCL.B",
       28: "ENCR.GND", 29: "ENCR.VCC", 30: "ENCR.A", 31: "ENCR.B",
       38: "IRL.VCC", 39: "IRL.GND", 40: "IRL.OUT", 41: "IRR.VCC", 42: "IRR.GND", 43: "IRR.OUT"}

# ---- birlestirme (union-find) ----
par = {}
def find(x):
    par.setdefault(x, x)
    while par[x] != x:
        par[x] = par[par[x]]
        x = par[x]
    return x
def union(a, b):
    par[find(a)] = find(b)

terms = {}                                     # terminal -> serit
for (c, r), name in pins.items():
    terms[name + f"@{c}{r}"] = strip(c, r)
    find(strip(c, r))
by_wire = {}
for n, c, r in B.ENDS:
    by_wire.setdefault(n, []).append(strip(c, r))
for n, ss in by_wire.items():
    for s in ss[1:]:
        union(ss[0], s)
    if n in OFF:
        terms[OFF[n]] = ss[0]
# modul ici baglar
def tie(names):
    ss = [s for k, s in terms.items() if k.split("@")[0] in names]
    for s in ss[1:]:
        union(ss[0], s)
# adaptor kablolari klemense vidalanir
terms["ADP.+"] = strip(B.K_P, "h"); terms["ADP.-"] = strip(B.K_M, "h")
tie({"TB.GND"})
tie({"ESP.GND"})

nets = {}
for t, s in terms.items():
    nets.setdefault(find(s), []).append(t.split("@")[0])

# ---- beklenen aglar ----
EXP = {
    "V12": ["ADP.+", "K.+", "TB.VM", "LM.IN+"],
    "GND": ["ADP.-", "K.-", "TB.GND", "ESP.GND", "MPU.GND", "MPU.AD0", "ENCL.GND", "ENCR.GND", "IRL.GND", "IRR.GND", "LM.IN-", "LM.OUT-"],
    "V33": ["ESP.3V3", "TB.PWMA", "TB.PWMB", "TB.VCC", "MPU.VCC", "ENCL.VCC", "ENCR.VCC", "IRL.VCC", "IRR.VCC"],
    "V5": ["LM.OUT+", "ESP.5V"],
    "STBY": ["TB.STBY", "ESP.GPIO4"], "AIN1": ["TB.AIN1", "ESP.GPIO27"], "AIN2": ["TB.AIN2", "ESP.GPIO14"],
    "BIN1": ["TB.BIN1", "ESP.GPIO16"], "BIN2": ["TB.BIN2", "ESP.GPIO17"],
    "AO1": ["TB.AO1", "MOTL.M1"], "AO2": ["TB.AO2", "MOTL.M2"], "BO1": ["TB.BO1", "MOTR.M1"], "BO2": ["TB.BO2", "MOTR.M2"],
    "ENCL.A": ["ENCL.A", "ESP.GPIO32"], "ENCL.B": ["ENCL.B", "ESP.GPIO33"],
    "ENCR.A": ["ENCR.A", "ESP.GPIO25"], "ENCR.B": ["ENCR.B", "ESP.GPIO26"],
    "SCL": ["MPU.SCL", "ESP.GPIO22"], "SDA": ["MPU.SDA", "ESP.GPIO21"], "INT": ["MPU.INT", "ESP.GPIO19"],
    "IRL": ["IRL.OUT", "ESP.GPIO36"], "IRR": ["IRR.OUT", "ESP.GPIO39"],
}
owner = {}
for k, lst in EXP.items():
    for t in lst:
        owner[t] = k

fail, ok = [], 0
root_of = {}
for tk, s in terms.items():
    root_of.setdefault(tk.split("@")[0], set()).add(find(s))
# 1) her beklenen ag tek parca mi (kopuk yok) ve icinde yabanci terminal yok mu (kisa devre yok)
for k, lst in EXP.items():
    roots = set()
    for tname in lst:
        roots |= root_of[tname]
    if len(roots) != 1:
        fail.append(f"KOPUK: {k} birden fazla parcada")
        continue
    r = next(iter(roots))
    stray = sorted({tname for tname in nets[r] if owner.get(tname) != k})
    if stray:
        fail.append(f"KISA DEVRE: {k} agina yabanci terminal girmis: {stray}")
    else:
        ok += 1
# 2) kullanilmayan ESP/TB pinleri baska aga girmis mi
for r, lst in nets.items():
    ks = {owner[t] for t in lst if t in owner}
    if len(ks) > 1:
        fail.append(f"KARISMA: tek agda birden fazla hat: {sorted(ks)} -> {sorted(lst)}")
# 3) cakisan delikler
seen = {}
for n, c, r in B.ENDS:
    if r in ("T+", "T-", "B+", "B-"):
        key = (c, r)
    else:
        key = (c, r)
    seen.setdefault(key, set()).add(n)
for key, ns in seen.items():
    if len(ns) > 1:
        fail.append(f"AYNI DELIK: {key} icin kablolar {sorted(ns)}")
    if key in pins:
        fail.append(f"PIN DELIGI: {key} zaten {pins[key]} pini")
# 4) 10 kohm: STBY seridi (24,b) ve ust GND pini seridi (28,b)
rs = [strip(B.tcol(3), "b"), strip(B.tcol(7), "b")]
if find(rs[0]) == find(terms[f"TB.STBY@{B.tcol(3)}d"]) and find(rs[1]) == find(terms[f"TB.GND@{B.tcol(7)}d"]):
    ok += 1
else:
    fail.append("DIRENC: 10 kohm STBY ve GND serilerine oturmuyor")
# 5) ray carpisma: 12 V rayi ile 3,3 V rayi ayni agda mi
if find("B+") == find("T+"):
    fail.append("KISA DEVRE: 12 V rayi ile 3,3 V rayi bagli")
if find("T-") != find("B-"):
    fail.append("KOPUK: ust GND ile alt GND bagli degil")

print(f"Kontrol edilen ag: {len(EXP)} + direnc; kablo ucu: {len(B.ENDS)}")
print(f"Gecen: {ok}")
if fail:
    print("SORUN:")
    for f in fail:
        print(" -", f)
    sys.exit(1)
print("Sorun yok: kisa devre yok, kopuk hat yok, cakisan delik yok.")
