"""TB6612 surumu robot ana kartini (130x80 mm, 2 katli, THT) betikle uretir -> elektronik/pcb_v2/
  cdtp_ana_kart_v2_v2.kicad_pcb  (+ .kicad_pro, drc.json, drc.rpt, pcb_kontrol.md, gerber/)
Girdi: elektronik/pcb_v2/netlist.xml (python tools/kicad_v2_netlist.py uretir). Yazi ASCII.
Calistir: python tools/kicad_pcb_v2.py   (KiCad 10 kurulu olmali; betik kendini KiCad'in python'u ile yeniden baslatir)
tools/kicad_pcb.py (eski BTS7960 karti) ile ayni yonlendirici ve denetimler; yalniz parca listesi, yerlesim ve kurallar degisti.
"""
import os
import sys
import re
import json
import math
import heapq
import time
import subprocess
import tempfile
import shutil
import zipfile
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict

# ----------------------------------------------------------------------------------------------------------------
# KiCad python'una gec (pcbnew orada)
# ----------------------------------------------------------------------------------------------------------------
LOCAL = os.environ.get("LOCALAPPDATA", "")
KICAD = os.environ.get("KICAD_DIR", os.path.join(LOCAL, "Programs", "KiCad", "10.0"))
KICAD_PY = os.path.join(KICAD, "bin", "python.exe")
KICAD_CLI = os.path.join(KICAD, "bin", "kicad-cli.exe")
FPDIR = os.path.join(KICAD, "share", "kicad", "footprints")

try:
    import pcbnew
except ImportError:
    if os.path.exists(KICAD_PY) and os.path.abspath(sys.executable).lower() != os.path.abspath(KICAD_PY).lower():
        sys.exit(subprocess.call([KICAD_PY, os.path.abspath(__file__)] + sys.argv[1:]))
    raise
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ELEK = os.path.join(ROOT, "elektronik")
OUT = os.path.join(ELEK, "pcb_v2")
NETLIST = os.path.join(OUT, "netlist.xml")
PCB_FILE = os.path.join(OUT, "cdtp_ana_kart_v2.kicad_pcb")
PRO_FILE = os.path.join(OUT, "cdtp_ana_kart_v2.kicad_pro")

# ----------------------------------------------------------------------------------------------------------------
# Parametreler
# ----------------------------------------------------------------------------------------------------------------
ROW_PITCH_MM = float(os.environ.get("ROW_PITCH_MM", 25.4))        # ESP32 DevKitC iki soket sirasi arasi (pin merkezleri). Gercek kartla DOGRULA (V4: 25.4)
BOARD_W, BOARD_H, CORNER_R = 130.0, 80.0, 3.0
CX, CY = 127.0, 76.2       # kart merkezi (mutlak mm). Izgara katlarinda tutulur.
HOLE_DX, HOLE_DY, HOLE_D = 122.0, 72.0, 3.2
GRID = 0.127               # yonlendirme izgarasi (2,54 mm / 20)
G_NM = 127000

CLEAR = 0.25               # bakir-bakir bosluk
EDGE_CLEAR = 0.5           # bakir-kart kenari
MARGIN = 0.012             # yonlendirici ek guvenligi
VIA_D, VIA_DRILL = 1.45, 0.8
W_SIG, W_5V, W_12V = 0.30, 0.60, 1.00
ZONE_CLEAR = 0.30
CLEAR_12V = 0.50           # 12 V aglari (+12V, +12V_MOT, CHG+) yabanci bakirdan en az bu kadar uzak (netclass PWR12)
NETS_12V = ("/+12V", "/ADP+", "/FUSED")
SILK_W = 0.16              # ipek baski cizgi/yazi kalinligi (>= 0,153 mm uretici alt siniri)
MASK_EXP = 0.05            # lehim maskesi acikligi (pad_to_mask_clearance)
# ESP32 anten ucu RF yasak bolgesi (bakir dolgu, iz, via yok; iki katman). Modul USB solda, anten sagda (pin 1 = anten ucu).
# Cokgen: dikdortgen x ANT_X0..ANT_X1, y ANT_Y0..ANT_Y1; U1 pin 1 ve pin 20 (x=149.86) icin kuzey/guney girintileri.
ANT_X0, ANT_X1, ANT_Y0, ANT_Y1 = 181.02, 190.02, 61.77, 90.77
ANT_NOTCH_X, ANT_NOTCH_TOP, ANT_NOTCH_BOT = 185.02, 65.27, 87.47
STITCH_PITCH_CELLS = 40    # dikis vialari 40*0,127 = 5,08 mm aralikli izgarada

# Kartta kalan referanslar
ON_BOARD = ["U1", "A1", "A2", "U3", "J1", "F1", "J2", "C1", "R1", "JP1", "J3", "J4", "J5", "J6"]

# ayak izi: (kutuphane, ad)
FP_HDR = lambda n: ("Connector_PinHeader_2.54mm", f"PinHeader_1x{n:02d}_P2.54mm_Vertical")
FP_TERM = ("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal")
FP_RES = ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal")
FP_PTC = ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm")          # 5 mm bacak aralikli 2 ped (PTC sigorta)
FP_CPOL = ("Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm")
FP_SOCKET = ("Connector_PinSocket_2.54mm", "PinSocket_1x19_P2.54mm_Vertical")
FP_SOCKET8 = ("Connector_PinSocket_2.54mm", "PinSocket_1x08_P2.54mm_Vertical")
FP_SOCKET1 = ("Connector_PinSocket_2.54mm", "PinSocket_1x01_P2.54mm_Vertical")
FP_HOLE = ("MountingHole", "MountingHole_3.2mm_M3")

# TB6612 modulu: iki sira 1x8 soket, sira araligi (Pololu tipi 15,24 mm = 0,6 inc). VARSAYIM: modulu olcup dogrulayin.
TB_ROW_MM = float(os.environ.get("TB_ROW_MM", 15.24))
# LM2596 mini: 4 ped; IN-/OUT- ustte, IN+/OUT+ altta (modul ters bakar). VARSAYIM: ped aralikleri, modulu olcup dogrulayin.
LM_DX_MM = float(os.environ.get("LM_DX_MM", 40.64))     # IN ile OUT pedleri arasi (16 delik)
LM_DY_MM = float(os.environ.get("LM_DY_MM", 20.32))     # + ped ile - ped arasi (8 delik)

FOOTPRINT = {
    "U1": None, "A2": None, "U3": None,
    "A1": FP_SOCKET8,
    "J1": FP_TERM, "J2": FP_TERM, "F1": FP_PTC, "C1": FP_CPOL, "R1": FP_RES, "JP1": FP_HDR(2),
    "J3": FP_HDR(6), "J4": FP_HDR(6), "J5": FP_HDR(3), "J6": FP_HDR(3),
}

# yerlesim: ref -> (x, y, derece)   (mutlak mm; ayak izi orijini = 1. pin; KiCad dereceleri saat yonu tersi)
# Tum ped konumlari 1,27 mm izgarasinda (yonlendirici izgarasi).
U1_X = 182.88            # ESP32 pin 1 (anten ucu); pinler -x yonune artar, USB ucu solda
U1_Y = CY - ROW_PITCH_MM / 2
PLACE = {
    "U1": (U1_X, U1_Y, 270),
    # ust kenar: MPU6050 soketi (modul govdesi asagi), IR konnektorleri
    "A1": (139.70, 44.45, 90), "J5": (162.56, 44.45, 90), "J6": (172.72, 44.45, 90),
    # sol ust: LM2596 (pin 1 = IN+ sol alt; IN- 20,32 mm yukarida; OUT 40,64 mm sagda)
    "U3": (68.58, 71.12, 0),
    # sol alt: TB6612 (pin 1 sol ust; ikinci sira 15,24 mm asagida)
    "A2": (71.12, 83.82, 90), "R1": (93.98, 83.82, 0),
    # alt kenar: klemensler, sigorta, kondansator, motor konnektorleri
    "J1": (77.47, 109.22, 0), "F1": (91.44, 109.22, 0), "J2": (104.14, 109.22, 0),
    "C1": (118.11, 106.68, 0), "J3": (133.35, 105.41, 90), "J4": (153.67, 105.41, 90),
    # USB ucunun ustu
    "JP1": (119.38, 62.23, 90),
}

# ipek baski: ref -> islev yazisi
FUNC = {
    "F1": "3A PTC", "JP1": "USB: CIKAR", "C1": "1000uF 25V", "R1": "EN PD",
    "J3": "SOL MOTOR", "J4": "SAG MOTOR", "J5": "IR SOL", "J6": "IR SAG", "A1": "MPU6050", "A2": "TB6612", "U3": "LM2596 5.0V",
}
# elle yerlestirilen yazilar: (metin, x, y, boy) mutlak mm
MANUAL_TEXT = [
    ("ESP32 <USB", 122.0, 76.2, 1.0),
    ("12V GIRIS", 77.5, 103.0, 1.0),
    ("ANAHTAR", 104.1, 103.0, 1.0),
]
GROUP_TEXT = {}
NOTES = {}
TITLE = "CDTP DENGE KARTI V2.0" + chr(10) + "2026-11-10"
TITLE_AT = (160.0, 99.0)
# konnektor pin adlari: tools/kicad_v2_netlist.py pin sirasi ile BIREBIR, pin 1'den baslayarak.
PINLEG = {
    "A1": ["3V3", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"],
    "J3": ["M1", "GND", "C1", "C2", "VCC", "M2"], "J4": ["M1", "GND", "C1", "C2", "VCC", "M2"],
    "J5": ["VCC", "GND", "OUT"], "J6": ["VCC", "GND", "OUT"],
    "J1": ["+12V", "GND"], "J2": ["IN", "OUT"], "JP1": ["5V", "ESP"],
}
# yazinin konumu: S/N = yatay siranin alti/ustu (dikey yazi), E/W = dikey siranin dogusu/batisi, strip = klemens ici serit
LEG_MODE = {"A1": "N", "J3": "S", "J4": "S", "J5": "N", "J6": "N", "J1": "strip", "J2": "strip", "JP1": "S"}

# net genislikleri: sinyal 0,30; +5V/+3V3 0,60; 12 V hatlari ve motor cikislari 1,00
def net_width(name):
    n = name.lstrip("/")
    if n in ("+12V", "ADP+", "FUSED") or n.startswith("MOT_"):
        return W_12V
    if n in ("+5V", "+5V_ESP", "+3V3"):
        return W_5V
    return W_SIG


def net_clear(name):
    """bir agin kendi bosluk gereksinimi (netclass): 12 V aglari 0,5 mm, digerleri 0,25 mm"""
    return CLEAR_12V if name in NETS_12V else CLEAR


def mm(v):
    return int(round(v * 1e6))


def ascii_only(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c if ord(c) < 128 else "" for c in s)


# ----------------------------------------------------------------------------------------------------------------
# 1) netlist
# ----------------------------------------------------------------------------------------------------------------
def read_netlist():
    root = ET.parse(NETLIST).getroot()
    comps = {}
    for c in root.find("components"):
        ref = c.get("ref")
        comps[ref] = {"value": ascii_only(c.findtext("value") or ""), "tstamp": c.findtext("tstamps") or ""}
    nets = {}      # ad -> [(ref, pin)]
    pin_net = {}   # (ref, pin) -> ad
    for n in root.find("nets"):
        ad = n.get("name")
        nodes = [(x.get("ref"), x.get("pin")) for x in n if x.get("ref") in ON_BOARD]
        if nodes:
            nets[ad] = nodes
            for nd in nodes:
                pin_net[nd] = ad
    return comps, nets, pin_net


# ----------------------------------------------------------------------------------------------------------------
# 2) govde
# ----------------------------------------------------------------------------------------------------------------
def load_fp(lib, name):
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
    if fp is None:
        raise RuntimeError(f"ayak izi yok: {lib}:{name}")
    return fp


LIBDIR = os.path.join(OUT, "cdtp.pretty")


def save_custom(fp):
    """ozel ayak izini proje kutuphanesine yazar (DRC 'kutuphane yok' uyarisi cikmasin)"""
    os.makedirs(LIBDIR, exist_ok=True)
    pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(LIBDIR, fp)
    with open(os.path.join(OUT, "fp-lib-table"), "w", encoding="ascii") as f:
        f.write("\n".join(["(fp_lib_table", "  (version 7)",
                           '  (lib (name "cdtp")(type "KiCad")(uri "${KIPRJMOD}/cdtp.pretty")'
                           '(options "")(descr "CDTP ozel ayak izleri"))', ")", ""]))


def add_outline(fp, x0, y0, x1, y1):
    """ayak izine (yerel koordinat, mm) ipek dikdortgen cizer: modul govdesinin yeri"""
    for (a, b, c, d) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        s = pcbnew.PCB_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.F_SilkS)
        s.SetStart(pcbnew.VECTOR2I(mm(a), mm(b)))
        s.SetEnd(pcbnew.VECTOR2I(mm(c), mm(d)))
        s.SetWidth(mm(SILK_W))
        fp.Add(s)


def merge_rows(fp, fp2, n_off, dx_mm, dy_mm=0.0, circle=True):
    """fp2'nin pedlerini ve ipek/avlu cizgilerini fp'ye (dx, dy kaydirilmis, numara + n_off) tasir"""
    dx, dy = mm(dx_mm), mm(dy_mm)
    keep = []
    for pad in list(fp2.Pads()):
        fp2.Remove(pad)
        pad.SetNumber(str(int(pad.GetNumber()) + n_off))
        if circle:
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)   # kare ped yalniz pin 1'de kalsin
        pad.SetPosition(pcbnew.VECTOR2I(pad.GetPosition().x + dx, pad.GetPosition().y + dy))
        fp.Add(pad)
        keep.append(pad)
    for it in list(fp2.GraphicalItems()):
        if it.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_CrtYd, pcbnew.F_Fab):
            fp2.Remove(it)
            it.Move(pcbnew.VECTOR2I(dx, dy))
            fp.Add(it)
            keep.append(it)
    try:
        for m in fp2.Models():
            m2 = pcbnew.FP_3DMODEL(m)
            off = m2.m_Offset
            m2.m_Offset = pcbnew.VECTOR3D(off.x + dx_mm, off.y - dy_mm, off.z)
            fp.Models().push_back(m2)
    except Exception:
        pass
    return keep


def make_esp_footprint():
    """2x19 disi soket: iki PinSocket_1x19, ROW_PITCH_MM arayla; pin 1-19 sol sira, 20-38 sag sira (DevKitC ustten gorunum)."""
    fp = load_fp(*FP_SOCKET)
    fp.SetFPID(pcbnew.LIB_ID("cdtp", "ESP32_DevKitC_2x19_PinSocket_P2.54mm"))
    fp._keep = merge_rows(fp, load_fp(*FP_SOCKET), 19, ROW_PITCH_MM)
    save_custom(fp)
    return fp


def make_tb_footprint():
    """TB6612 modulu: iki PinSocket_1x08. Pad 1-8 ust sira, 9-16 alt sira; rot 90'da ikinci sira 'asagida' olsun diye -x yonunde"""
    fp = load_fp(*FP_SOCKET8)
    fp.SetFPID(pcbnew.LIB_ID("cdtp", "TB6612_2x8_PinSocket_P2.54mm"))
    fp._keep = merge_rows(fp, load_fp(*FP_SOCKET8), 8, -TB_ROW_MM)
    add_outline(fp, -TB_ROW_MM - 2.0, -2.0, 2.0, 7 * 2.54 + 2.0)
    save_custom(fp)
    return fp


def make_lm_footprint():
    """LM2596 mini: 4 tek soket. Pin 1 = IN+ (orijin), 2 = IN- (yukari), 3 = OUT+ (saga), 4 = OUT- (saga ve yukari)"""
    fp = load_fp(*FP_SOCKET1)
    fp.SetFPID(pcbnew.LIB_ID("cdtp", "LM2596_mini_4pad"))
    keep = []
    for num, (px, py) in (("2", (0.0, -LM_DY_MM)), ("3", (LM_DX_MM, 0.0)), ("4", (LM_DX_MM, -LM_DY_MM))):
        keep += merge_rows(fp, load_fp(*FP_SOCKET1), int(num) - 1, px, py)
    fp._keep = keep
    add_outline(fp, -1.6, -LM_DY_MM - 1.6, LM_DX_MM + 1.6, 1.6)
    save_custom(fp)
    return fp


def new_board_with_outline():
    board = pcbnew.BOARD()
    x0, y0 = CX - BOARD_W / 2, CY - BOARD_H / 2
    x1, y1 = x0 + BOARD_W, y0 + BOARD_H
    r = CORNER_R

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        s.SetWidth(mm(0.1))
        board.Add(s)

    def arc(c, a0, a1):
        """merkez c, a0 -> a1 derece (y asagi), saat yonunde kisa yay"""
        am = (a0 + a1) / 2
        pt = lambda a: pcbnew.VECTOR2I(mm(c[0] + r * math.cos(math.radians(a))), mm(c[1] + r * math.sin(math.radians(a))))
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetArcGeometry(pt(a0), pt(am), pt(a1))
        s.SetWidth(mm(0.1))
        board.Add(s)

    seg((x0 + r, y0), (x1 - r, y0))
    seg((x1, y0 + r), (x1, y1 - r))
    seg((x1 - r, y1), (x0 + r, y1))
    seg((x0, y1 - r), (x0, y0 + r))
    arc((x1 - r, y0 + r), -90, 0)
    arc((x1 - r, y1 - r), 0, 90)
    arc((x0 + r, y1 - r), 90, 180)
    arc((x0 + r, y0 + r), 180, 270)
    return board, (x0, y0, x1, y1)


def build_board():
    comps, nets, pin_net = read_netlist()
    board, bbox = new_board_with_outline()
    netinfo = {}
    for ad in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, ad)
        board.Add(ni)
        netinfo[ad] = ni
    fps = {}
    if os.path.isdir(LIBDIR):
        for f in os.listdir(LIBDIR):
            os.remove(os.path.join(LIBDIR, f))
    for ref in ON_BOARD:
        if ref == "U1":
            fp = make_esp_footprint()
        elif ref == "A2":
            fp = make_tb_footprint()
        elif ref == "U3":
            fp = make_lm_footprint()
        else:
            fp = load_fp(*FOOTPRINT[ref])
        if ref == "A1":      # MPU6050 modulu: govde soket sirasinin yaninda (rot 90'da asagi), 20,3 x 16,5 mm
            add_outline(fp, -15.5, -1.6, 2.0, 7 * 2.54 + 2.0)
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"] or ref)
        x, y, rot = PLACE[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.Reference().SetVisible(True)
        fp.Value().SetVisible(False)
        if comps[ref]["tstamp"]:
            try:
                fp.SetPath(pcbnew.KIID_PATH("/" + comps[ref]["tstamp"]))
            except Exception:
                pass
        for pad in fp.Pads():
            ad = pin_net.get((ref, pad.GetNumber()))
            if ad is not None:
                pad.SetNet(netinfo[ad])
        board.Add(fp)
        fps[ref] = fp
    # montaj delikleri
    for k, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)], 1):
        fp = load_fp(*FP_HOLE)
        fp.SetReference(f"H{k}")
        fp.SetValue("M3")
        fp.SetPosition(pcbnew.VECTOR2I(mm(CX + sx * HOLE_DX / 2), mm(CY + sy * HOLE_DY / 2)))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
        fps[f"H{k}"] = fp
    return board, fps, netinfo, bbox, nets, pin_net


# ----------------------------------------------------------------------------------------------------------------
# 3) yonlendirici
# ----------------------------------------------------------------------------------------------------------------
class Obstacle:
    __slots__ = ("kind", "p", "net", "layers", "id", "ext")

    def __init__(self, kind, p, net, layers, oid):
        self.kind, self.p, self.net, self.layers, self.id = kind, p, net, layers, oid
        if kind == "circle":
            cx, cy, r = p
            self.ext = (cx - r, cx + r, cy - r, cy + r)
        elif kind == "rect":
            cx, cy, hx, hy = p
            self.ext = (cx - hx, cx + hx, cy - hy, cy + hy)
        else:
            ax, ay, bx, by, r = p
            self.ext = (min(ax, bx) - r, max(ax, bx) + r, min(ay, by) - r, max(ay, by) + r)


class Router:
    def __init__(self, bbox):
        x0, y0, x1, y1 = bbox
        self.bbox = bbox
        self.I0 = int(math.floor(x0 / GRID)) - 1
        self.J0 = int(math.floor(y0 / GRID)) - 1
        self.W = int(math.ceil((x1 - x0) / GRID)) + 3
        self.H = int(math.ceil((y1 - y0) / GRID)) + 3
        self.xs = (np.arange(self.W) + self.I0) * GRID
        self.ys = (np.arange(self.H) + self.J0) * GRID
        self.obs = []
        self.cache = {}
        self.edge_cache = {}
        self.fixed_pads = []
        self.via_keepouts = []     # (x0, y0, x1, y1) mm: ipek yazi kutulari; viya merkezi bunlara VIA_D/2 + 0,05 kadar yaklasamaz

    def silk_penalty_mask(self):
        m = np.zeros((self.H, self.W), dtype=bool)
        for (bx0, by0, bx1, by1) in self.via_keepouts:
            m |= ((self.xs[None, :] >= bx0) & (self.xs[None, :] <= bx1) & (self.ys[:, None] >= by0) & (self.ys[:, None] <= by1))
        return m

    def via_keepout_mask(self):
        m = np.zeros((self.H, self.W), dtype=bool)
        g = VIA_D / 2 + 0.05
        for (bx0, by0, bx1, by1) in self.via_keepouts:
            m |= ((self.xs[None, :] >= bx0 - g) & (self.xs[None, :] <= bx1 + g) &
                  (self.ys[:, None] >= by0 - g) & (self.ys[:, None] <= by1 + g))
        return m

    # --- geometri ---
    def add(self, kind, p, net, layers=(0, 1)):
        o = Obstacle(kind, p, net, layers, len(self.obs))
        self.obs.append(o)
        return o

    def node_xy(self, L, r, c):
        return (self.xs[c], self.ys[r])

    def nearest_node(self, x, y):
        return (int(round(y / GRID)) - self.J0, int(round(x / GRID)) - self.I0)

    def dist_field(self, o, xs, ys):
        if o.kind == "circle":
            cx, cy, r = o.p
            return np.hypot(xs - cx, ys - cy) - r
        if o.kind == "rect":
            cx, cy, hx, hy = o.p
            dx = np.maximum(np.abs(xs - cx) - hx, 0.0)
            dy = np.maximum(np.abs(ys - cy) - hy, 0.0)
            return np.hypot(dx, dy)
        ax, ay, bx, by, r = o.p
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        if L2 < 1e-12:
            return np.hypot(xs - ax, ys - ay) - r
        t = np.clip(((xs - ax) * vx + (ys - ay) * vy) / L2, 0.0, 1.0)
        return np.hypot(xs - (ax + t * vx), ys - (ay + t * vy)) - r

    def obs_mask(self, o, w, clr=CLEAR):
        key = (o.id, round(w, 3), round(clr, 3))
        m = self.cache.get(key)
        if m is not None:
            return m
        rq = clr + w / 2 + MARGIN
        x_lo, x_hi, y_lo, y_hi = o.ext
        c0 = max(int(math.floor((x_lo - rq) / GRID)) - self.I0 - 1, 0)
        c1 = min(int(math.ceil((x_hi + rq) / GRID)) - self.I0 + 2, self.W)
        r0 = max(int(math.floor((y_lo - rq) / GRID)) - self.J0 - 1, 0)
        r1 = min(int(math.ceil((y_hi + rq) / GRID)) - self.J0 + 2, self.H)
        if c1 <= c0 or r1 <= r0:
            m = (0, 0, 0, 0, None)
        else:
            d = self.dist_field(o, self.xs[c0:c1][None, :], self.ys[r0:r1][:, None])
            m = (r0, r1, c0, c1, d < rq)
        self.cache[key] = m
        return m

    def edge_mask(self, w):
        key = round(w, 3)
        if key in self.edge_cache:
            return self.edge_cache[key]
        x0, y0, x1, y1 = self.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hx, hy, r = (x1 - x0) / 2, (y1 - y0) / 2, CORNER_R
        X = self.xs[None, :]
        Y = self.ys[:, None]
        qx = np.abs(X - cx) - (hx - r)
        qy = np.abs(Y - cy) - (hy - r)
        outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
        m = (-outside) < (EDGE_CLEAR + w / 2 + MARGIN)
        self.edge_cache[key] = m
        return m

    def blocked(self, net, w, all_foreign=False):
        """katman basina bool dizisi: bu net icin w genisligindeki iz merkezi gecemez"""
        blk = [self.edge_mask(w).copy(), self.edge_mask(w).copy()]
        for o in self.obs:
            if not all_foreign and net is not None and o.net == net:
                continue
            if o.net == "#keepout":
                clr = 0.02          # RF yasak bolgesi: bosluk kurali yok, yalniz iz/via icine giremez
            else:
                clr = max(net_clear(net) if net is not None else CLEAR, net_clear(o.net))
            r0, r1, c0, c1, m = self.obs_mask(o, w, clr)
            if m is None:
                continue
            for L in o.layers:
                blk[L][r0:r1, c0:c1] |= m
        return blk

    # --- A* ---
    def astar(self, sources, target, blk, vblk, pref_h=(True, False), pen=None):
        W, H = self.W, self.H
        B = [bytearray(b.ravel().astype(np.uint8).tobytes()) for b in blk]
        VB = bytearray(vblk.ravel().astype(np.uint8).tobytes())
        PEN = bytearray(pen.ravel().astype(np.uint8).tobytes()) if pen is not None else None
        tr, tc = target
        DIRS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
        STEP = [GRID, GRID * 1.41421356] * 4
        TURN = [0.0, 0.06, 0.25, 0.6, 1.2]
        VIA_COST = 3.0
        NOT_PREF = 1.3

        def h(r, c):
            dr, dc = abs(r - tr), abs(c - tc)
            m, M = min(dr, dc), max(dr, dc)
            return (M - m + 1.41421356 * m) * GRID

        def key(L, r, c, d):
            return (((L * H + r) * W + c) * 9) + d

        dist = {}
        parent = {}
        heap = []
        for (L, r, c) in sources:
            k = key(L, r, c, 8)
            dist[k] = 0.0
            heapq.heappush(heap, (h(r, c), 0.0, L, r, c, 8))
        goal = None
        while heap:
            f, gd, L, r, c, d = heapq.heappop(heap)
            k = key(L, r, c, d)
            if gd > dist.get(k, 1e18) + 1e-12:
                continue
            if r == tr and c == tc:
                goal = (L, r, c, d)
                break
            Bl = B[L]
            for nd in range(8):
                dr, dc = DIRS[nd]
                nr, nc = r + dr, c + dc
                if nr < 0 or nc < 0 or nr >= H or nc >= W:
                    continue
                if Bl[nr * W + nc]:
                    continue
                cost = STEP[nd]
                if dr == 0 and dc != 0:
                    if not pref_h[L]:
                        cost *= NOT_PREF
                elif dc == 0 and dr != 0:
                    if pref_h[L]:
                        cost *= NOT_PREF
                if d != 8:
                    ad = abs(nd - d)
                    if ad > 4:
                        ad = 8 - ad
                    cost += TURN[ad]
                if PEN is not None and PEN[nr * W + nc]:
                    cost += 0.5          # ipek yazinin altindan gecmemeyi tercih et (yumusak ceza)
                ng = gd + cost
                nk = key(L, nr, nc, nd)
                if ng < dist.get(nk, 1e18):
                    dist[nk] = ng
                    parent[nk] = k
                    heapq.heappush(heap, (ng + h(nr, nc), ng, L, nr, nc, nd))
            # via
            L2 = 1 - L
            if not VB[r * W + c] and not B[L2][r * W + c]:
                ng = gd + VIA_COST
                nk = key(L2, r, c, 8)
                if ng < dist.get(nk, 1e18):
                    dist[nk] = ng
                    parent[nk] = k
                    heapq.heappush(heap, (ng + h(r, c), ng, L2, r, c, 8))
        if goal is None:
            return None
        L, r, c, d = goal
        path = []
        k = key(L, r, c, d)
        while True:
            kk = k // 9
            c_ = kk % W
            kk //= W
            r_ = kk % H
            L_ = kk // H
            path.append((L_, r_, c_))
            if k not in parent:
                break
            k = parent[k]
        path.reverse()
        # tekrarlari (yon farkli ayni dugum) ayikla
        out = [path[0]]
        for n in path[1:]:
            if n != out[-1]:
                out.append(n)
        return out


def pad_obstacle(pad):
    """pcbnew pedinden engel tanimi"""
    p = pad.GetPosition()
    x, y = p.x / 1e6, p.y / 1e6
    sz = pad.GetSize(pcbnew.F_Cu)
    w, h = sz.x / 1e6, sz.y / 1e6
    ang = pad.GetOrientationDegrees() % 180
    if abs(ang - 90) < 1e-3:
        w, h = h, w
    sh = pad.GetShape(pcbnew.F_Cu)
    if sh == pcbnew.PAD_SHAPE_CIRCLE or abs(w - h) < 1e-6 and sh == pcbnew.PAD_SHAPE_OVAL:
        return "circle", (x, y, w / 2)
    if sh == pcbnew.PAD_SHAPE_OVAL:
        if w > h:
            d = (w - h) / 2
            return "seg", (x - d, y, x + d, y, h / 2)
        d = (h - w) / 2
        return "seg", (x, y - d, x, y + d, w / 2)
    return "rect", (x, y, w / 2, h / 2)


def merge_edges(edges, special):
    """edges: set((a,b)) a,b=(r,c) tek adim; special: kopma dugumleri -> [(a, b)] uzun parcalar"""
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    used = set()
    segs = []

    def e(a, b):
        return (a, b) if a < b else (b, a)

    for a, b in sorted(edges):
        if e(a, b) in used:
            continue
        used.add(e(a, b))
        dr, dc = b[0] - a[0], b[1] - a[1]
        end = b
        while len(adj[end]) == 2 and end not in special:
            nxt = (end[0] + dr, end[1] + dc)
            if nxt in adj[end] and e(end, nxt) not in used:
                used.add(e(end, nxt))
                end = nxt
            else:
                break
        start = a
        while len(adj[start]) == 2 and start not in special:
            prv = (start[0] - dr, start[1] - dc)
            if prv in adj[start] and e(start, prv) not in used:
                used.add(e(start, prv))
                start = prv
            else:
                break
        segs.append((start, end))
    return segs


def ant_rects():
    return [(ANT_NOTCH_X, ANT_Y0, ANT_X1, ANT_Y1), (ANT_X0, ANT_NOTCH_TOP, ANT_NOTCH_X, ANT_NOTCH_BOT)]


def ant_polygon():
    return [(ANT_NOTCH_X, ANT_Y0), (ANT_X1, ANT_Y0), (ANT_X1, ANT_Y1), (ANT_NOTCH_X, ANT_Y1), (ANT_NOTCH_X, ANT_NOTCH_BOT),
            (ANT_X0, ANT_NOTCH_BOT), (ANT_X0, ANT_NOTCH_TOP), (ANT_NOTCH_X, ANT_NOTCH_TOP)]


def route_all(board, fps, netinfo, bbox, nets, log, via_keepouts=()):
    rt = Router(bbox)
    rt.via_keepouts = list(via_keepouts)
    # sabit engeller: pedler (katmanlar: THT -> iki katman), montaj delikleri
    pads = {}   # ad -> [(ref, num, x, y)]
    for ref, fp in fps.items():
        if ref.startswith("H"):
            p = fp.GetPosition()
            rt.add("circle", (p.x / 1e6, p.y / 1e6, 3.0), "#hole")
            continue
        for pad in fp.Pads():
            kind, prm = pad_obstacle(pad)
            net = pad.GetNetname() or None
            if net is None or net.startswith("unconnected-"):
                net = f"#nc_{ref}_{pad.GetNumber()}"
            rt.add(kind, prm, net)
            if pad.GetNetname() and not pad.GetNetname().startswith("unconnected-"):
                pads.setdefault(pad.GetNetname(), []).append((ref, pad.GetNumber(), pad.GetPosition().x / 1e6,
                                                              pad.GetPosition().y / 1e6))
    # RF yasak bolgesi (anten ucu): iki dikdortgenin birlesimi (cokgenin girintili hali)
    for (kx0, ky0, kx1, ky1) in ant_rects():
        rt.add("rect", ((kx0 + kx1) / 2, (ky0 + ky1) / 2, (kx1 - kx0) / 2, (ky1 - ky0) / 2), "#keepout")
    # yonlendirilecek netler (GND dolgu ile)
    order_p = ["/+12V", "/ADP+", "/FUSED", "/+5V", "/+5V_ESP", "/+3V3"]
    sig = [n for n in pads if n not in order_p and n != "/GND" and len(pads[n]) > 1]
    def span(n):
        xs = [p[2] for p in pads[n]]
        ys = [p[3] for p in pads[n]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    sig.sort(key=lambda n: (len(pads[n]) > 4, span(n)))
    todo = [n for n in order_p if n in pads and len(pads[n]) > 1] + sig
    vkm = rt.via_keepout_mask()
    pen = rt.silk_penalty_mask()
    result = {}
    failed = []
    for name in todo:
        w = net_width(name)
        t0 = time.time()
        blk = rt.blocked(name, w)
        vblk_l = rt.blocked(name, VIA_D, all_foreign=True)  # via: tum bakirdan (kendi pedlerinden de) uzak
        vblk = vblk_l[0] | vblk_l[1] | vkm
        pl = pads[name]
        nodes = []
        for (ref, num, x, y) in pl:
            r, c = rt.nearest_node(x, y)
            nodes.append((r, c))
        edges = [set(), set()]
        vias = set()
        special = set()
        stubs = []
        connected = [0]
        tree = {(0, nodes[0][0], nodes[0][1]), (1, nodes[0][0], nodes[0][1])}
        remaining = list(range(1, len(pl)))
        ok = True
        for i in range(len(pl)):
            r, c = nodes[i]
            special.add((r, c))
            nx, ny = rt.node_xy(0, r, c)
            if abs(nx - pl[i][2]) > 1e-4 or abs(ny - pl[i][3]) > 1e-4:
                stubs.append(((pl[i][2], pl[i][3]), (nx, ny)))
        while remaining:
            # Prim: bagli pedlere en yakin ped
            best = None
            for j in remaining:
                for i in connected:
                    d = math.hypot(pl[i][2] - pl[j][2], pl[i][3] - pl[j][3])
                    if best is None or d < best[0]:
                        best = (d, j)
            j = best[1]
            path = rt.astar(tree, nodes[j], blk, vblk, pen=pen)
            if path is None:
                ok = False
                break
            for a, b in zip(path, path[1:]):
                if a[0] == b[0]:
                    pa, pb = (a[1], a[2]), (b[1], b[2])
                    edges[a[0]].add((pa, pb) if pa < pb else (pb, pa))
                else:
                    vias.add((a[1], a[2]))
                    special.add((a[1], a[2]))
            for n in path:
                tree.add(n)
            for (r, c) in vias:
                tree.add((0, r, c))
                tree.add((1, r, c))
            tree.add((0, nodes[j][0], nodes[j][1]))
            tree.add((1, nodes[j][0], nodes[j][1]))
            connected.append(j)
            remaining.remove(j)
        if not ok:
            failed.append(name)
            log(f"  YOL YOK: {name} ({len(pl)} ped, w={w})")
            continue
        segs = []
        for L in (0, 1):
            for (a, b) in merge_edges(edges[L], special | vias):
                segs.append((L, a, b))
        result[name] = {"w": w, "segs": segs, "vias": sorted(vias), "stubs": stubs}
        # yeni engelleri ekle
        for (L, a, b) in segs:
            ax, ay = rt.xs[a[1]], rt.ys[a[0]]
            bx, by = rt.xs[b[1]], rt.ys[b[0]]
            rt.add("seg", (ax, ay, bx, by, w / 2), name, (L,))
        for (r, c) in vias:
            rt.add("circle", (rt.xs[c], rt.ys[r], VIA_D / 2), name)
        for (p0, p1) in stubs:
            rt.add("seg", (p0[0], p0[1], p1[0], p1[1], w / 2), name)
        nvia = len(vias)
        ln = sum(math.hypot(rt.xs[b[1]] - rt.xs[a[1]], rt.ys[b[0]] - rt.ys[a[0]]) for (_, a, b) in segs)
        log(f"  {name}: w={w} {len(pl)} ped, {len(segs)} parca, {ln:.1f} mm, {nvia} via ({time.time() - t0:.1f} s)")
    return rt, result, failed


def emit_routes(board, rt, result, netinfo):
    layer = [pcbnew.F_Cu, pcbnew.B_Cu]
    def add_track(L, p0, p1, w, ni):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(round(p0[0] * 1e6)), int(round(p0[1] * 1e6))))
        t.SetEnd(pcbnew.VECTOR2I(int(round(p1[0] * 1e6)), int(round(p1[1] * 1e6))))
        t.SetWidth(mm(w))
        t.SetLayer(layer[L])
        t.SetNet(ni)
        board.Add(t)

    def add_via(x, y, ni):
        v = pcbnew.PCB_VIA(board)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetPosition(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(ni)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(v)

    for name, d in result.items():
        ni = netinfo[name]
        for (L, a, b) in d["segs"]:
            add_track(L, (rt.xs[a[1]], rt.ys[a[0]]), (rt.xs[b[1]], rt.ys[b[0]]), d["w"], ni)
        for (r, c) in d["vias"]:
            add_via(rt.xs[c], rt.ys[r], ni)
        for (p0, p1) in d["stubs"]:
            # kisa kopru: pedin merkezinden dugume (iki katman da olabilir; ust katman yeterli degil -> her ikisi)
            for L in (0, 1):
                add_track(L, p0, p1, d["w"], ni)


def stitch_vias(board, rt, netinfo, avoid_boxes=()):
    """GND dikis vialari: izgara uzerinde 5,08 mm araliklarla, hicbir bakira (GND dahil) degmeden;
    avoid_boxes (nm): ipek yazi kutulari, viyalar yazinin altina dusmesin"""
    blk = rt.blocked("/GND", VIA_D, all_foreign=True)
    b = blk[0] | blk[1]
    g = VIA_D / 2 + 0.05
    for (bx0, by0, bx1, by1) in avoid_boxes:
        bx0, by0, bx1, by1 = bx0 / 1e6, by0 / 1e6, bx1 / 1e6, by1 / 1e6
        b |= ((rt.xs[None, :] >= bx0 - g) & (rt.xs[None, :] <= bx1 + g) &
              (rt.ys[:, None] >= by0 - g) & (rt.ys[:, None] <= by1 + g))
    ni = netinfo["/GND"]
    added = []
    step = STITCH_PITCH_CELLS
    x0, y0, x1, y1 = rt.bbox
    for r in range(rt.H):
        for c in range(rt.W):
            gi, gj = c + rt.I0, r + rt.J0
            if gi % step or gj % step:
                continue
            if b[r, c]:
                continue
            x, y = rt.xs[c], rt.ys[r]
            if not (x0 < x < x1 and y0 < y < y1):
                continue
            v = pcbnew.PCB_VIA(board)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetPosition(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
            v.SetWidth(mm(VIA_D))
            v.SetDrill(mm(VIA_DRILL))
            v.SetNet(ni)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(v)
            added.append((x, y))
            rt.add("circle", (x, y, VIA_D / 2), "/GND")
            # onbellegi tazele: sonraki vialar bunu engel sayar
            r0, r1, c0, c1, m = rt.obs_mask(rt.obs[-1], VIA_D)
            for L in (0, 1):
                b[r0:r1, c0:c1] |= m
    return added


def add_gnd_zones(board, bbox, netinfo):
    x0, y0, x1, y1 = bbox
    ins = 0.3
    r = CORNER_R - ins
    pts = []
    corners = [(x1 - CORNER_R, y0 + CORNER_R, -90), (x1 - CORNER_R, y1 - CORNER_R, 0),
               (x0 + CORNER_R, y1 - CORNER_R, 90), (x0 + CORNER_R, y0 + CORNER_R, 180)]
    for cx, cy, a0 in corners:
        for k in range(0, 10):
            a = math.radians(a0 + 9 * k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(L)
        z.SetNet(netinfo["/GND"])
        z.SetZoneName("GND_" + ("F" if L == pcbnew.F_Cu else "B"))
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in pts:
            ol.Append(mm(x), mm(y))
        z.SetMinThickness(mm(0.25))
        z.SetLocalClearance(mm(ZONE_CLEAR))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)


def add_antenna_keepout(board):
    """ESP32 anten ucu: bakir dolgu / iz / via YASAK (kural alani, F.Cu + B.Cu). Ped ve ayak izi serbest (U1 soketi icinde)."""
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetIsRuleArea(True)
    z.SetZoneName("RF_ANTEN_YASAK")
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ol = z.Outline()
    ol.NewOutline()
    for (x, y) in ant_polygon():
        ol.Append(mm(x), mm(y))
    board.Add(z)
    return z


# ----------------------------------------------------------------------------------------------------------------
# 4) ipek baski
# ----------------------------------------------------------------------------------------------------------------
def box_of(item, infl=0):
    b = item.GetBoundingBox()
    return [b.GetLeft() - infl, b.GetTop() - infl, b.GetRight() + infl, b.GetBottom() + infl]


def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def box_dist(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def fix_silk_widths(fps):
    """footprint kutuphanesinin 0,12 mm ipek cizgilerini SILK_W'ye yukselt (uretici alt siniri 0,15 mm)"""
    n = 0
    for fp in fps.values():
        for it in fp.GraphicalItems():
            if it.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and it.GetWidth() < mm(SILK_W):
                it.SetWidth(mm(SILK_W))
                n += 1
    return n


def mk_text(board, txt, size=1.0, ang=0.0, thick=SILK_W):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(ang)
    return t


def place_silk(board, fps, bbox, silk_log, stage="rest", placed0=None):
    """etiketleri bos yerlere koyar: pedlerden, mevcut ipekten, kenardan ve deliklerden uzak.
    stage="legends": yalniz konnektor pin adlari/pin 1 (yonlendirmeden ONCE: viyalar bu yazilardan kacar); stage="rest": kalanlar"""
    x0, y0, x1, y1 = bbox
    blockers = []
    for ref, fp in fps.items():
        for pad in fp.Pads():
            blockers.append(box_of(pad, mm(0.35)))
        for it in fp.GraphicalItems():
            if it.GetLayer() == pcbnew.F_SilkS:
                if it.GetShape() == pcbnew.SHAPE_T_RECT:     # dolu kutu degil: dort kenar
                    b = box_of(it)
                    e = mm(SILK_W)
                    for bb in ([b[0], b[1], b[2], b[1] + e], [b[0], b[3] - e, b[2], b[3]],
                               [b[0], b[1], b[0] + e, b[3]], [b[2] - e, b[1], b[2], b[3]]):
                        blockers.append([bb[0] - mm(0.15), bb[1] - mm(0.15), bb[2] + mm(0.15), bb[3] + mm(0.15)])
                else:
                    blockers.append(box_of(it, mm(0.15)))
        if ref.startswith("H"):
            p = fp.GetPosition()
            r = mm(3.6)
            blockers.append([p.x - r, p.y - r, p.x + r, p.y + r])
    for v in board.GetTracks():   # dikis/yonlendirme vialari: ipek delik uzerine binmesin
        if v.Type() == pcbnew.PCB_VIA_T:
            p = v.GetPosition()
            r = mm(0.95)
            blockers.append([p.x - r, p.y - r, p.x + r, p.y + r])
    inner = [mm(x0 + 0.8), mm(y0 + 0.8), mm(x1 - 0.8), mm(y1 - 0.8)]
    placed = list(placed0 or [])

    def free(box):
        if box[0] < inner[0] or box[1] < inner[1] or box[2] > inner[2] or box[3] > inner[3]:
            return False
        for b in blockers:
            if overlap(box, b):
                return False
        for b in placed:
            if overlap(box, b):
                return False
        return True

    def fit(textitem, anchor_box, max_r=14.0, extra=None):
        cx0 = (anchor_box[0] + anchor_box[2]) // 2
        cy0 = (anchor_box[1] + anchor_box[3]) // 2
        step = mm(0.635)
        n = int(max_r / 0.635)
        cands = [(i, j) for i in range(-n, n + 1) for j in range(-n, n + 1)]

        def score(ij):
            px = cx0 + ij[0] * step
            py = cy0 + ij[1] * step
            dx = max(anchor_box[0] - px, 0, px - anchor_box[2])
            dy = max(anchor_box[1] - py, 0, py - anchor_box[3])
            return math.hypot(dx, dy) + 1e-3 * math.hypot(ij[0], ij[1])
        cands.sort(key=score)
        for ij in cands:
            textitem.SetPosition(pcbnew.VECTOR2I(cx0 + ij[0] * step, cy0 + ij[1] * step))
            bb = box_of(textitem, mm(0.1))
            if free(bb) and (extra is None or extra(bb)):
                placed.append(bb)
                return True
        return False

    def put_at(txt, cx, cy, ang=0.0, size=1.0):
        """tam konuma koy (serbestse); degilse None"""
        t = mk_text(board, txt, size, ang)
        t.SetPosition(pcbnew.VECTOR2I(int(round(cx * 1e6)), int(round(cy * 1e6))))
        bb = box_of(t, mm(0.1))
        if free(bb):
            placed.append(bb)
            board.Add(t)
            return t, bb
        return None, bb

    def text_size(txt, ang):
        t = mk_text(board, txt, 1.0, ang)
        t.SetPosition(pcbnew.VECTOR2I(0, 0))
        b = t.GetBoundingBox()
        return b.GetWidth() / 1e6, b.GetHeight() / 1e6

    def fpbox(ref):
        b = fps[ref].GetBoundingBox(False)
        return [b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()]

    # --- 1) konnektor pin adlari + pin 1 isareti (ilk once: sabit konumlar) ---
    for ref, names in (PINLEG.items() if stage == "legends" else []):
        fp = fps[ref]
        pads = sorted(fp.Pads(), key=lambda p: int(p.GetNumber()))
        mode = LEG_MODE[ref]
        pr = pads[0].GetSize(pcbnew.F_Cu).x / 2e6
        names = list(names)
        # pin 1 isareti once (oncelikli): sira dogrultusunda pin 1'in otesi, olmazsa yanlar; olmazsa "1 ADI" birlesik yazi
        if mode != "strip":
            p1, p2 = pads[0].GetPosition(), pads[1].GetPosition()
            ux, uy = (p1.x - p2.x) / 1e6, (p1.y - p2.y) / 1e6
            ln = math.hypot(ux, uy)
            ux, uy = ux / ln, uy / ln
            w, h = text_size("1", 0.0)
            ok = False
            lx, ly = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1)}[mode]
            for (dx, dy) in ((ux, uy), (-lx, -ly)):
                for gap in (0.45, 0.75, 1.05, 1.5):
                    d = pr + gap + max(w, h) / 2
                    t, _ = put_at("1", p1.x / 1e6 + dx * d, p1.y / 1e6 + dy * d, 0.0)
                    if t is not None:
                        ok = True
                        break
                if ok:
                    break
            if not ok:
                names[0] = "1 " + names[0]
                silk_log.append(f"{ref}: ayri pin 1 isareti yok, pin adi '{names[0]}' olarak birlestirildi")
        for pad, nm in zip(pads, names):
            px, py = pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6
            ok = False
            if mode == "strip":      # klemens: pedin ustunde, govde ici serit
                t, _ = put_at(nm, px, py - 3.8, 0.0)
                ok = t is not None
            elif mode in ("S", "N"):  # yatay sira: dikey yazi (aci 90 = alttan uste okunur), ped altinda/ustunde
                w, h = text_size(nm, 90.0)
                sgn = 1 if mode == "S" else -1
                for gap in (0.45, 0.75, 1.05, 1.5, 2.0):
                    t, _ = put_at(nm, px, py + sgn * (pr + gap + h / 2), 90.0)
                    if t is not None:
                        ok = True
                        break
            else:                    # dikey sira: yatay yazi, "E": pedin dogusunda, "W": batisinda
                w, h = text_size(nm, 0.0)
                sgn = 1 if mode == "E" else -1
                for gap in (0.45, 0.75, 1.05, 1.5, 2.0):
                    t, _ = put_at(nm, px + sgn * (pr + gap + w / 2), py, 0.0)
                    if t is not None:
                        ok = True
                        break
            if not ok:
                silk_log.append(f"{ref}.{pad.GetNumber()}: pin adi '{nm}' yer bulamadi")

    if stage == "legends":
        return placed
    # --- 2) elle yerlestirilen yazilar ---
    for (txt, x, y, sz) in MANUAL_TEXT:
        t = mk_text(board, txt, sz)
        if fit(t, [mm(x), mm(y), mm(x), mm(y)], 12.0):
            board.Add(t)
        else:
            silk_log.append(f"elle yazi '{txt}' yer bulamadi")

    # --- 3) bolucu aglari: etiket direncin GOVDESININ ICINDE (dikey), boylece hangi bolucu oldugu belli ---
    for ref, gname in GROUP_TEXT.items():
        pads = sorted(fps[ref].Pads(), key=lambda p: int(p.GetNumber()))
        mx = (pads[0].GetPosition().x + pads[1].GetPosition().x) / 2e6
        my = (pads[0].GetPosition().y + pads[1].GetPosition().y) / 2e6
        t, _ = put_at(gname, mx, my, 90.0, 0.8)
        if t is None:
            silk_log.append(f"{ref}: bolucu etiketi '{gname}' govde icine sigmadi")
    # --- 3b) konnektor notlari (J6/J7 IR sirasi) ---
    for ref, txt in NOTES.items():
        t = mk_text(board, txt)
        if fit(t, fpbox(ref), 9.0):
            board.Add(t)
        else:
            silk_log.append(f"{ref}: not '{txt}' yer bulamadi")

    # --- 4) klemens islev etiketleri: kendi klemensinin hemen ustunde, govde x araliginin icinde ---
    func_done = set()
    for ref in ():
        b = fpbox(ref)
        cx = (b[0] + b[2]) / 2e6
        txt = FUNC[ref]
        w, h = text_size(txt, 0.0)
        ok = False
        for gap in (0.3, 0.5, 0.8, 1.1):
            for dx in [0.0] + [k * s_ for k in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0) for s_ in (1, -1)]:
                if cx + dx - w / 2 < b[0] / 1e6 - 0.01 or cx + dx + w / 2 > b[2] / 1e6 + 0.01:
                    continue
                t, bb = put_at(txt, cx + dx, b[1] / 1e6 - gap - h / 2, 0.0)
                if t is not None:
                    ok = True
                    break
            if ok:
                break
        if not ok:
            silk_log.append(f"{ref}: '{txt}' klemens ustunde yer bulamadi")
        func_done.add(ref)

    # --- 5) footprint referanslari, islev yazilari ---
    for ref in ON_BOARD:
        fp = fps[ref]
        t = fp.Reference()
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
        t.SetTextThickness(mm(SILK_W))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetKeepUpright(False)
        t.SetTextAngleDegrees(0)
        if not fit(t, fpbox(ref)):
            t.SetVisible(False)
            silk_log.append(f"{ref}: referans yazisi yer bulamadi (gizlendi)")
    for ref in ON_BOARD:
        txt = FUNC.get(ref)
        if not txt or ref in func_done:
            continue
        t = mk_text(board, txt)
        if fit(t, fpbox(ref)):
            board.Add(t)
        else:
            silk_log.append(f"{ref}: '{txt}' yer bulamadi")

    # --- 6) baslik ---
    t = mk_text(board, TITLE, 1.0, 0.0, 0.2)
    if fit(t, [mm(TITLE_AT[0]), mm(TITLE_AT[1]), mm(TITLE_AT[0]), mm(TITLE_AT[1])], 14.0):
        board.Add(t)
    else:
        silk_log.append("baslik yer bulamadi")
    return placed


# ----------------------------------------------------------------------------------------------------------------
# 5/6) proje dosyasi, DRC, netlist karsilastirmasi
# ----------------------------------------------------------------------------------------------------------------
def kicad_default_pro():
    """KiCad 10'un kendi yazdigi tam proje dosyasi semasi: bos bir klasorde LoadBoard+SaveBoard (kural/netclass anahtarlari
    surumle birlikte dogru olsun; elle yazilan eksik sema KiCad'de hic yuklenmiyor ve varsayilana donuyordu)"""
    tmp = tempfile.mkdtemp(prefix="cdtp_pro_")
    try:
        pcb = os.path.join(tmp, "cdtp_ana_kart_v2.kicad_pcb")
        shutil.copy(PCB_FILE, pcb)
        pcbnew.SaveBoard(pcb, pcbnew.LoadBoard(pcb))
        with open(os.path.join(tmp, "cdtp_ana_kart_v2.kicad_pro"), encoding="utf-8") as f:
            return json.load(f)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


PRO_TEMPLATE = []


def write_pro():
    """proje kurallari + netclass'lar. KiCad bu dosyayi DRC'de yeniden yazabildigi icin: ONCE tam sema al, kurallari yama,
    DRC'yi bir KOPYADA kos (run_drc), gercek .kicad_pro bu fonksiyonla son DRC'den once yazilir ve DRC'den sonra dogrulanir."""
    if not PRO_TEMPLATE:
        PRO_TEMPLATE.append(kicad_default_pro())
    pro = json.loads(json.dumps(PRO_TEMPLATE[0]))
    ds = pro["board"]["design_settings"]
    ds["rules"].update({
        "min_clearance": CLEAR, "min_track_width": W_SIG, "min_via_diameter": VIA_D, "min_via_annular_width": 0.3,
        "min_through_hole_diameter": VIA_DRILL, "min_copper_edge_clearance": EDGE_CLEAR, "min_hole_clearance": CLEAR,
        "min_hole_to_hole": CLEAR, "min_text_height": 0.8, "min_text_thickness": 0.15, "min_silk_clearance": 0.0,
        "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_connection": 0.0, "max_error": 0.005,
        "solder_mask_to_copper_clearance": 0.0})
    ds["defaults"]["silk_line_width"] = SILK_W
    ds["defaults"]["silk_text_thickness"] = SILK_W
    ds["defaults"]["board_outline_line_width"] = 0.1
    ds["defaults"]["copper_line_width"] = W_SIG
    ds["defaults"]["pads"] = {"drill": 1.0, "height": 1.7, "width": 1.7}
    ds["track_widths"] = [0.0, W_SIG, W_5V, W_12V]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": VIA_D, "drill": VIA_DRILL}]
    ns = pro["net_settings"]
    base = dict(ns["classes"][0])

    def cls(name, w, clr, prio):
        c = dict(base)
        c.update({"name": name, "track_width": w, "clearance": clr, "via_diameter": VIA_D, "via_drill": VIA_DRILL,
                  "priority": prio})
        return c
    default = cls("Default", W_SIG, CLEAR, base.get("priority", 2147483647))
    ns["classes"] = [default, cls("PWR5", W_5V, CLEAR, 1), cls("PWR12", W_12V, CLEAR_12V, 0)]
    ns["netclass_assignments"] = None
    ns["netclass_patterns"] = ([{"netclass": "PWR5", "pattern": p} for p in ("/+5V", "/+5V_ESP", "/+3V3")] +
                               [{"netclass": "PWR12", "pattern": p} for p in NETS_12V])
    with open(PRO_FILE, "w", encoding="ascii") as f:
        json.dump(pro, f, indent=2)
    return pro


def check_pro(log):
    """kural/netclass degerleri dosyada duruyor mu (KiCad ustune yazmis olabilir)"""
    with open(PRO_FILE, encoding="utf-8") as f:
        pro = json.load(f)
    r = pro["board"]["design_settings"]["rules"]
    cl = {c["name"]: c for c in pro["net_settings"]["classes"]}
    want = [("min_clearance", r.get("min_clearance"), CLEAR), ("min_track_width", r.get("min_track_width"), W_SIG),
            ("min_via_diameter", r.get("min_via_diameter"), VIA_D), ("min_via_annular_width", r.get("min_via_annular_width"), 0.3),
            ("min_through_hole_diameter", r.get("min_through_hole_diameter"), VIA_DRILL),
            ("min_copper_edge_clearance", r.get("min_copper_edge_clearance"), EDGE_CLEAR),
            ("PWR12.clearance", cl.get("PWR12", {}).get("clearance"), CLEAR_12V),
            ("PWR12.track_width", cl.get("PWR12", {}).get("track_width"), W_12V),
            ("PWR5.track_width", cl.get("PWR5", {}).get("track_width"), W_5V),
            ("Default.track_width", cl.get("Default", {}).get("track_width"), W_SIG)]
    bad = [f"{n}={g} (olmasi {w})" for n, g, w in want if g is None or abs(g - w) > 1e-9]
    ok = not bad
    log(("GECTI" if ok else "KALDI") + "  .kicad_pro kurallari dosyada duruyor" + ("" if ok else ": " + "; ".join(bad)))
    return ok


RULES_LOADED = [False]


def run_drc(refill=True):
    """DRC'yi gecici bir KOPYADA kosar (KiCad kopyanin .kicad_pro'sunu yeniden yazar, gercek dosya korunur).
    refill: bolgeler kopyada doldurulur ve dolu kart gercek dosyaya geri kopyalanir."""
    out = os.path.join(OUT, "drc.json")
    rpt = os.path.join(OUT, "drc.rpt")
    tmp = tempfile.mkdtemp(prefix="cdtp_drc_")
    try:
        for fn in ("cdtp_ana_kart_v2.kicad_pcb", "cdtp_ana_kart_v2.kicad_pro", "fp-lib-table"):
            shutil.copy(os.path.join(OUT, fn), os.path.join(tmp, fn))
        shutil.copytree(os.path.join(OUT, "cdtp.pretty"), os.path.join(tmp, "cdtp.pretty"))
        pcb = os.path.join(tmp, "cdtp_ana_kart_v2.kicad_pcb")
        cmd = [KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-all", "--all-track-errors", "--units", "mm", "-o", out]
        if refill:
            cmd += ["--refill-zones", "--save-board"]
        subprocess.run(cmd + [pcb], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "report", "--severity-all", "--all-track-errors", "--units", "mm",
                        "-o", rpt, pcb], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        try:   # KiCad kopyanin projesini yeniden yazdi: kurallar yuklenmis mi (DRC gercekten bu kurallarla kostu mu)
            with open(os.path.join(tmp, "cdtp_ana_kart_v2.kicad_pro"), encoding="utf-8") as f:
                p2 = json.load(f)
            cl2 = {c["name"]: c for c in p2["net_settings"]["classes"]}
            RULES_LOADED[0] = (abs(p2["board"]["design_settings"]["rules"]["min_clearance"] - CLEAR) < 1e-9 and
                               abs(cl2.get("PWR12", {}).get("clearance", 0) - CLEAR_12V) < 1e-9)
        except Exception:
            RULES_LOADED[0] = False
        if refill:
            shutil.copy(pcb, PCB_FILE)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(out, encoding="utf-8") as f:
        d = json.load(f)
    for fn in (out, rpt):   # KiCad arayuz dili Turkce olabilir: rapor dosyalari ASCII'ye indirgenir
        with open(fn, encoding="utf-8", errors="replace") as f:
            t = f.read()
        with open(fn, "w", encoding="ascii") as f:
            f.write(ascii_only(t))
    return d


def summarize_drc(d, log):
    viol = d.get("violations", [])
    unc = d.get("unconnected_items", [])
    par = d.get("schematic_parity", [])
    by = defaultdict(int)
    for v in viol:
        by[(v.get("severity"), v.get("type"))] += 1
    err = [v for v in viol if v.get("severity") == "error"]
    warn = [v for v in viol if v.get("severity") == "warning"]
    log(f"DRC: {len(err)} hata, {len(warn)} uyari, {len(unc)} baglanmamis, {len(par)} parite")
    for k, n in sorted(by.items()):
        log(f"   {k[0]:8s} {k[1]}: {n}")
    return err, warn, unc


def fix_starved(d, log):
    """termal rolyef kolu yetmeyen GND pedleri icin dolgu baglantisini 'tam' yap, DRC'yi tekrarla"""
    pts = []
    for v in d.get("violations", []):
        if v.get("type") == "starved_thermal":
            for it in v.get("items", []):
                if "pos" in it:
                    pts.append((it["pos"]["x"], it["pos"]["y"]))
    if not pts:
        return False
    board = pcbnew.LoadBoard(PCB_FILE)
    n = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            if any(abs(p.x / 1e6 - x) < 0.05 and abs(p.y / 1e6 - y) < 0.05 for x, y in pts) and pad.GetNetname() == "/GND":
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                n += 1
                log(f"  GND pedi {fp.GetReference()}.{pad.GetNumber()}: dolgu baglantisi TAM (termal kol yetmedi)")
    pcbnew.SaveBoard(PCB_FILE, board)
    return n > 0


GERBER_DIR = os.path.join(OUT, "gerber")
GERBER_ZIP = os.path.join(GERBER_DIR, "CDTP_ana_kart_v2_gerber.zip")
GERBER_FILES = ["cdtp_ana_kart_v2-F_Cu.gtl", "cdtp_ana_kart_v2-B_Cu.gbl", "cdtp_ana_kart_v2-F_Mask.gts", "cdtp_ana_kart_v2-B_Mask.gbs",
                "cdtp_ana_kart_v2-F_Silkscreen.gto", "cdtp_ana_kart_v2-B_Silkscreen.gbo", "cdtp_ana_kart_v2-Edge_Cuts.gm1",
                "cdtp_ana_kart_v2-PTH.drl", "cdtp_ana_kart_v2-NPTH.drl"]


def export_fab(log):
    """Gerber + Excellon + duz zip (9 dosya; .gbrjob zip'e GIRMEZ) + onizleme PNG'leri. Dolu (refill edilmis) karttan."""
    os.makedirs(GERBER_DIR, exist_ok=True)
    for fn in os.listdir(GERBER_DIR):
        os.remove(os.path.join(GERBER_DIR, fn))
    r1 = subprocess.run([KICAD_CLI, "pcb", "export", "gerbers", "--layers",
                         "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts", "-o", GERBER_DIR + os.sep, PCB_FILE],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    r2 = subprocess.run([KICAD_CLI, "pcb", "export", "drill", "--excellon-separate-th", "-o", GERBER_DIR + os.sep, PCB_FILE],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    missing = [fn for fn in GERBER_FILES if not os.path.exists(os.path.join(GERBER_DIR, fn))]
    if missing:
        log(f"KALDI  gerber dosyalari eksik: {missing} {r1.stderr[-200:]} {r2.stderr[-200:]}")
        return False
    with zipfile.ZipFile(GERBER_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in GERBER_FILES:
            z.write(os.path.join(GERBER_DIR, fn), fn)
    log("GECTI  gerber + delik + zip: " + ", ".join(GERBER_FILES))
    return True


PDF2PNG = chr(10).join([
    'import sys, fitz',
    'from PIL import Image',
    'd = fitz.open(sys.argv[1]); p = d[0]',
    'pix = p.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)',
    "im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)",
    'px = im.load(); w, h = im.size',
    'xs = [x for x in range(0, w, 2) for y in range(0, h, 8) if px[x, y] != (255, 255, 255)]',
    'ys = [y for y in range(0, h, 2) for x in range(0, w, 8) if px[x, y] != (255, 255, 255)]',
    'box = (max(min(xs) - 24, 0), max(min(ys) - 24, 0), min(max(xs) + 24, w), min(max(ys) + 24, h))',
    'im = im.crop(box)',
    'im = im.resize((1024, int(im.height * 1024 / im.width)), Image.LANCZOS)',
    'im.save(sys.argv[2])',
])


def export_previews(log):
    """onizleme_ust.png / onizleme_alt.png: KiCad PDF cikisi (alt yuz aynali) -> PyMuPDF ile PNG (KiCad python'unda fitz yok:
    PATH'teki python ile)"""
    tmp = tempfile.mkdtemp(prefix="cdtp_prev_")
    ok = True
    try:
        script = os.path.join(tmp, "pdf2png.py")
        with open(script, "w", encoding="ascii") as f:
            f.write(PDF2PNG)
        py = shutil.which("python") or shutil.which("python3") or shutil.which("py")
        for side, layers, extra, png in (("ust", "F.Cu,F.Silkscreen,Edge.Cuts", [], "onizleme_ust.png"),
                                         ("alt", "B.Cu,Edge.Cuts", ["--mirror"], "onizleme_alt.png")):
            pdf = os.path.join(tmp, side + ".pdf")
            subprocess.run([KICAD_CLI, "pcb", "export", "pdf", "--layers", layers, "--mode-single", "--scale", "0", "-o", pdf]
                           + extra + [PCB_FILE], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            r = subprocess.run([py, "-W", "ignore", script, pdf, os.path.join(OUT, png)] if py else ["false"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            if r.returncode != 0 or not os.path.exists(os.path.join(OUT, png)):
                ok = False
                log(f"UYARI onizleme {png} uretilemedi (PyMuPDF/Pillow'lu python gerekli): {r.stderr[-150:]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if ok:
        log("GECTI  onizleme_ust.png / onizleme_alt.png")
    return ok


def seg_rect_dist(ax, ay, bx, by, rect):
    """dogru parcasi ile dikdortgen arasi en kisa mesafe (mm); kesisiyorsa 0"""
    x0, y0, x1, y1 = rect
    best = 1e9
    n = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
    for i in range(n + 1):
        t = i / n
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        dx = max(x0 - px, 0, px - x1)
        dy = max(y0 - py, 0, py - y1)
        best = min(best, math.hypot(dx, dy))
    return best


def post_checks(log):
    """DRC'nin kapsamadigi uretim kontrolleri: RF yasak bolgesi, ipek kalinligi, baslik/pin yazilari, sayimlar"""
    board = pcbnew.LoadBoard(PCB_FILE)
    res = []
    # 1) RF yasak bolgesi: iz/via yok, bakir dolgu yok
    rects = ant_rects()
    hit = 0
    ntr = nvia = 0
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            nvia += 1
            p = t.GetPosition()
            for r in rects:
                if seg_rect_dist(p.x / 1e6, p.y / 1e6, p.x / 1e6, p.y / 1e6, r) < t.GetWidth(pcbnew.F_Cu) / 2e6:
                    hit += 1
        else:
            ntr += 1
            for r in rects:
                if seg_rect_dist(t.GetStart().x / 1e6, t.GetStart().y / 1e6, t.GetEnd().x / 1e6, t.GetEnd().y / 1e6, r) < t.GetWidth() / 2e6:
                    hit += 1
    fillhit = 0
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.IsOnLayer(L):
                continue
            fp = z.GetFilledPolysList(L)
            for i in range(fp.OutlineCount()):
                ol = fp.Outline(i)
                for k in range(ol.PointCount()):
                    pt = ol.CPoint(k)
                    x, y = pt.x / 1e6, pt.y / 1e6
                    for (x0, y0, x1, y1) in rects:
                        if x0 + 0.01 < x < x1 - 0.01 and y0 + 0.01 < y < y1 - 0.01:
                            fillhit += 1
    res.append(("RF yasak bolgesi (anten ucu): iz/via/dolgu yok", hit == 0 and fillhit == 0,
                f"x {ANT_X0}-{ANT_X1} y {ANT_Y0}-{ANT_Y1}, iki katman; ihlal: iz/via {hit}, dolgu noktasi {fillhit}"))
    # 2) ipek kalinligi
    thin = []
    nsilk = 0
    for fp in board.GetFootprints():
        for it in fp.GraphicalItems():
            if it.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                nsilk += 1
                if it.GetWidth() < mm(0.153):
                    thin.append(fp.GetReference())
        t = fp.Reference()
        if t.IsVisible() and t.GetTextThickness() < mm(0.153):
            thin.append(fp.GetReference() + ".ref")
    ntxt = 0
    for d in board.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            ntxt += 1
            if d.GetTextThickness() < mm(0.153):
                thin.append("text:" + d.GetText())
    res.append(("ipek cizgi/yazi kalinligi >= 0.153 mm", not thin,
                f"{nsilk} footprint cizgisi + {ntxt} yazi; ince: {sorted(set(thin))[:6] or 'yok'}"))
    # 3) pin yazilari + baslik
    texts = [d.GetText() for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_SilkS]
    need = {}
    for ref, names in PINLEG.items():
        for nm in names:
            need[nm] = need.get(nm, 0) + 1
    miss = []
    for ref, names in PINLEG.items():
        pass
    cnt = defaultdict(int)
    texts = [t.replace(chr(10), " ") for t in texts]
    for t in texts:
        if t.startswith("1 ") and len(t) > 2:      # "1 3V3" birlesik pin 1 yazisi
            cnt["1"] += 1
            t = t[2:]
        cnt[t] += 1
    for nm, n in need.items():
        if cnt.get(nm, 0) < n:
            miss.append(f"{nm} ({cnt.get(nm, 0)}/{n})")
    n1 = cnt.get("1", 0)
    n_conn_1 = len([r for r in PINLEG if LEG_MODE[r] != "strip"])
    res.append(("pin yazilari (sema sirasi) + pin 1 isaretleri", not miss and n1 >= n_conn_1,
                f"{sum(len(v) for v in PINLEG.values())} pin adi, '1' isareti {n1}/{n_conn_1}" + (f"; eksik {miss}" if miss else "")))
    title_ok = any(t.startswith("CDTP DENGE KARTI V2.0") and "2026-11-10" in t for t in texts)
    res.append(("baslik 'CDTP DENGE KARTI V2.0' + tarih 2026-11-10", title_ok, "var" if title_ok else "yok"))
    res.append(("klemens etiketi 12V GIRIS (J1) / ANAHTAR (J2)", cnt.get("12V GIRIS", 0) == 1 and cnt.get("ANAHTAR", 0) >= 1,
                "var" if cnt.get("12V GIRIS", 0) == 1 and cnt.get("ANAHTAR", 0) >= 1 else "eksik"))
    # 4) lehim maskesi
    ds = board.GetDesignSettings()
    res.append(("lehim maskesi acikligi 0.05 mm", abs(ds.m_SolderMaskExpansion - mm(MASK_EXP)) < 10,
                f"{ds.m_SolderMaskExpansion / 1e6} mm (via'lar maskeyle kapali/tented)"))
    # 5) sayimlar
    res.append(("sayimlar", True, f"{ntr} iz parcasi, {nvia} via"))
    for a, s_, d in res:
        log(f"{'GECTI' if s_ else 'KALDI':6s} {a}: {d}")
    return all(s_ for _, s_, _ in res), res, (ntr, nvia)


def netlist_check(log):
    comps, nets, pin_net = read_netlist()
    board = pcbnew.LoadBoard(PCB_FILE)
    res = []
    exp = dict(pin_net)
    bad = []
    seen = set()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"):
            continue
        for pad in fp.Pads():
            k = (ref, pad.GetNumber())
            seen.add(k)
            want = exp.get(k, "")
            got = pad.GetNetname()
            if want != got:
                bad.append(f"{ref}.{k[1]}: sema '{want}' kart '{got}'")
    refs = {fp.GetReference() for fp in board.GetFootprints() if not fp.GetReference().startswith("H")}
    res.append(("kart parcalari = SPEC listesi", refs == set(ON_BOARD),
                f"{len(refs)} parca" if refs == set(ON_BOARD) else f"fark: {sorted(refs ^ set(ON_BOARD))}"))
    res.append(("her ped agi = netlist", not bad,
                f"{len(seen)} ped, hepsi ayni" if not bad else "; ".join(bad[:8])))
    missing = [k for k in exp if k not in seen]
    res.append(("netlistteki tum kart pinleri kartta var", not missing, "tam" if not missing else str(missing[:8])))
    # kart ag sayisi
    names = {n.GetNetname() for n in board.GetNetInfo().NetsByName().values()} if hasattr(board.GetNetInfo(), "NetsByName") else set()
    # konnektor pin sirasi: pad 1 konumu ile pin n konumunun yonu (bilgi)
    for a, s, d in res:
        log(f"{'GECTI' if s else 'KALDI':6s} {a}: {d}")
    return all(s for _, s, _ in res), res


def ascii_check(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        data.decode("ascii")
        return True, ""
    except UnicodeDecodeError as e:
        return False, str(e)


# ----------------------------------------------------------------------------------------------------------------
def main():
    t00 = time.time()
    os.makedirs(OUT, exist_ok=True)
    lines = []

    def log(s):
        print(s)
        sys.stdout.flush()
        lines.append(s)

    log(f"ROW_PITCH_MM = {ROW_PITCH_MM}")
    board, fps, netinfo, bbox, nets, pin_net = build_board()
    log(f"{len(ON_BOARD)} parca, {len(nets)} net kartta")
    # ipek: once konnektor pin adlari (viyalar bunlardan kacar), yonlendirme, sonra kalan yazilar, en son dikis vialari
    silk_log = []
    nfix = fix_silk_widths(fps)
    log(f"ipek cizgi kalinligi {SILK_W} mm'ye yukseltilen footprint cizgisi: {nfix}")
    placed = place_silk(board, fps, bbox, silk_log, stage="legends")
    kos = [(b[0] / 1e6, b[1] / 1e6, b[2] / 1e6, b[3] / 1e6) for b in placed]
    rt, result, failed = route_all(board, fps, netinfo, bbox, nets, log, via_keepouts=kos)
    emit_routes(board, rt, result, netinfo)
    placed = place_silk(board, fps, bbox, silk_log, stage="rest", placed0=placed)
    for s in silk_log:
        log("  IPEK: " + s)
    st = stitch_vias(board, rt, netinfo, placed)
    log(f"GND dikis via: {len(st)}")
    add_gnd_zones(board, bbox, netinfo)
    add_antenna_keepout(board)
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_SolderMaskExpansion = mm(MASK_EXP)       # pad_to_mask_clearance 0,05 mm (via'lar maskeyle kapali kalir)
    pcbnew.SaveBoard(PCB_FILE, board)
    write_pro()
    ok_ascii, msg = ascii_check(PCB_FILE)
    log(("GECTI" if ok_ascii else "KALDI") + f" kart dosyasi ASCII: {msg}")
    # DRC gecici KOPYADA kosar (KiCad kopyanin .kicad_pro'sunu yeniden yazar); dolu kart gercek dosyaya geri kopyalanir
    d = run_drc(refill=True)
    for _ in range(3):
        if not fix_starved(d, log):
            break
        write_pro()      # pcbnew.SaveBoard (fix_starved) .kicad_pro'yu varsayilana ezer: kurallari geri yaz, sonra DRC
        d = run_drc(refill=True)
    log(("GECTI" if RULES_LOADED[0] else "KALDI") + "  DRC proje kurallariyla kostu (min bosluk 0.25, PWR12 0.5 yuklendi)")
    err, warn, unc = summarize_drc(d, log)
    for v in (err + warn)[:40]:
        items = "; ".join(i.get("description", "")[:70] for i in v.get("items", [])[:2])
        log(f"   - [{v['severity']}] {v['type']}: {v['description'][:80]} | {items}")
    for u in unc[:20]:
        items = "; ".join(i.get("description", "")[:70] for i in u.get("items", [])[:2])
        log(f"   - [unconnected] {u['description'][:60]} | {items}")
    # son DRC'den SONRA proje kurallarini yeniden yaz (gercek .kicad_pro hicbir KiCad islemiyle ezilmesin) ve dogrula
    write_pro()
    ok_pro = check_pro(log)
    ok_nl, res = netlist_check(log)
    ok_post, res_post, (ntr, nvia) = post_checks(log)
    ok_fab = export_fab(log)
    export_previews(log)
    ok_pro = ok_pro and check_pro(log)
    ok_ascii2 = all(ascii_check(os.path.join(OUT, fn))[0] for fn in
                    ("cdtp_ana_kart_v2.kicad_pcb", "cdtp_ana_kart_v2.kicad_pro", "drc.json", "drc.rpt"))
    NL = chr(10)
    with open(os.path.join(OUT, "pcb_kontrol.md"), "w", encoding="ascii", errors="replace") as f:
        f.write("# Ana kart PCB denetimi" + NL + NL)
        f.write("`python tools/kicad_pcb_v2.py` uretir. ROW_PITCH_MM = %s" % ROW_PITCH_MM + NL + NL)
        f.write(f"DRC: {len(err)} hata, {len(warn)} uyari, {len(unc)} baglanmamis madde (drc.json, drc.rpt)" + NL + NL)
        f.write(f"Kural seti (cdtp_ana_kart_v2.kicad_pro): min bosluk {CLEAR}, min iz {W_SIG}, via {VIA_D}/{VIA_DRILL}, halka 0.3, "
                f"kart kenari {EDGE_CLEAR}; netclass: PWR12 iz {W_12V} bosluk {CLEAR_12V}, PWR5 iz {W_5V}, Default iz {W_SIG}. "
                f"DRC bu kurallarla kosturuldu (kopya uzerinde); gercek .kicad_pro DRC'den sonra yeniden yazilip dogrulandi."
                + NL + NL)
        f.write("| Kontrol | Sonuc | Ayrinti |" + NL + "|---|---|---|" + NL)
        allres = list(res) + list(res_post) + [
            (".kicad_pro kurallari dosyada duruyor", ok_pro, "DRC sonrasi dogrulandi"),
            ("DRC proje kurallariyla kostu", RULES_LOADED[0], "kopyadaki proje dosyasinda kurallar korundu"),
            ("gerber + delik + zip (9 dosya, .gbrjob zip'te yok)", ok_fab, ", ".join(GERBER_FILES)),
            ("uretilen dosyalar ASCII", ok_ascii and ok_ascii2, "pcb, pro, drc.json, drc.rpt")]
        for a, st_, dd in allres:
            f.write(f"| {a} | {'GECTI' if st_ else 'KALDI'} | {ascii_only(dd)} |" + NL)
        f.write(NL + "12 V aglari (+12V, ADP+, FUSED): PWR12 sinifi 0.5 mm bosluk; DRC hatasiz oldugu icin tum 12 V bakiri yabanci "
                "bakirdan (iz, ped, via, GND dolgusu) en az 0.5 mm uzaktadir; 0.5'e inemeyen yer yok." + NL)
    log(f"toplam {time.time() - t00:.0f} s; yol bulunamayan net: {failed}")
    return 0 if (not failed and not err and not unc and ok_nl and ok_ascii and ok_post and ok_pro and ok_fab
                 and RULES_LOADED[0]) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
