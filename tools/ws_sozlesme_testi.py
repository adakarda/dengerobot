#!/usr/bin/env python3
"""Robot WebSocket sozlesme testi (shared/protocol/messages.md v1).
Bir robota (gercek robot veya mock) baglanir, telemetriyi ve ping/pong'u uygulamanin bekledigi kurallara gore denetler.

  pip install websockets
  python tools/ws_sozlesme_testi.py ws://192.168.4.1:81/        # gercek robot (once Wi-Fi: CDTP-ROBOT)
  python tools/ws_sozlesme_testi.py ws://127.0.0.1:8181/        # takim mock robotu
  python tools/ws_sozlesme_testi.py --stdin < kareler.txt       # satir basina bir JSON karesi (sadece alan denetimi)
Cikis kodu 0 = hepsi gecti."""
import asyncio
import json
import sys
import time

STATES = {"IDLE", "BALANCING", "MANUAL", "DOCKING", "CHARGING", "FAULT"}
CMDS = {"F", "B", "L", "R", "S", "-"}
fails = []


def check(cond, msg):
    print(("  [GECTI] " if cond else "  [HATA ] ") + msg)
    if not cond:
        fails.append(msg)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_frame(f):
    check(f.get("type") == "telemetry", "type = telemetry")
    check(isinstance(f.get("t"), int) and f["t"] >= 0, "t: tamsayi, ms")
    check(isinstance(f.get("seq"), int) and 0 <= f["seq"] <= 65535, "seq: 0..65535")
    check(is_num(f.get("tilt")), "tilt: sayi (derece)")
    check(isinstance(f.get("charging"), bool), "charging: bool")
    check(is_num(f.get("battery")) and 0 <= f["battery"] <= 100, "battery: 0..100")
    check(f.get("state") in STATES, f"state gecerli ({f.get('state')})")
    check(f.get("cmd") in CMDS, f"cmd gecerli ({f.get('cmd')})")
    for k in ("voltage",):
        if k in f:
            check(is_num(f[k]), f"{k}: sayi")
    for k in ("docked",):
        if k in f:
            check(isinstance(f[k], bool), f"{k}: bool")
    if "box" in f:
        check(f["box"] is None or isinstance(f["box"], bool), "box: bool veya null")


async def live(url):
    import websockets
    async with websockets.connect(url) as ws:
        frames, t0 = [], time.monotonic()
        while time.monotonic() - t0 < 3.2:
            try:
                m = await asyncio.wait_for(ws.recv(), 1.0)
            except asyncio.TimeoutError:
                continue
            f = json.loads(m)
            if f.get("type") == "telemetry":
                frames.append((time.monotonic(), f))
        print(f"{len(frames)} telemetri karesi alindi (3,2 s)")
        check(len(frames) >= 3, "en az 1 Hz telemetri (spec REQ-D-02)")
        if len(frames) >= 2:
            gaps = [b[0] - a[0] for a, b in zip(frames, frames[1:])]
            check(max(gaps) < 2.0, f"kare arasi bosluk < 2 s (en buyuk {max(gaps):.2f} s) (REQ-D-03)")
            rate = (len(frames) - 1) / (frames[-1][0] - frames[0][0])
            print(f"  olculen hiz: {rate:.1f} Hz (onerilen 5 Hz)")
            seqs = [f["seq"] for _, f in frames]
            check(all((b - a) % 65536 == 1 for a, b in zip(seqs, seqs[1:])), "seq her karede +1")
        if frames:
            check_frame(frames[-1][1])
        await ws.send(json.dumps({"type": "ping", "id": 17}))
        got = None
        t1 = time.monotonic()
        while time.monotonic() - t1 < 1.5 and got is None:
            f = json.loads(await asyncio.wait_for(ws.recv(), 1.5))
            if f.get("type") == "pong":
                got = f
        check(got is not None and got.get("id") == 17, "ping -> pong, id geri yansitilir")
        await ws.send(json.dumps({"type": "cmd", "cmd": "S", "src": "app"}))
        print("  cmd S gonderildi (robot durdurma komutu, zararsiz)")


def main():
    if "--stdin" in sys.argv:
        for line in sys.stdin:
            if line.strip():
                print(line.strip()[:100])
                check_frame(json.loads(line))
    else:
        url = next((a for a in sys.argv[1:] if a.startswith("ws")), "ws://192.168.4.1:81/")
        asyncio.run(live(url))
    print("SONUC:", "HEPSI GECTI" if not fails else f"{len(fails)} HATA")
    sys.exit(1 if fails else 0)


main()
