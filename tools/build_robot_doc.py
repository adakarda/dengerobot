"""docs/robot_src.html icine robotun kaynak kodlarini gomer -> docs/robot.html
Calistir: python tools/build_robot_doc.py  (kod degisince yeniden calistirin)"""
import html
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = [
    ("firmware/robot/platformio.ini", "PlatformIO ayarlari"),
    ("firmware/robot/src/main.cpp", "Ana program: 200 Hz gorev, radyolar, komutlar"),
    ("firmware/robot/src/pins.h", "Pin haritasi"),
    ("firmware/robot/src/hw.h", "MPU6050, PCNT, BTS7960, ADC suruculeri"),
    ("firmware/robot/src/links.h", "ESP-NOW alici, BLE sunucu"),
    ("common/cdtp_core/src/cdtp_config.h", "Tum ayar sabitleri"),
    ("common/cdtp_core/src/gains.h", "LQR kazanclari (uretilir)"),
    ("common/cdtp_core/src/robot_logic.h", "Mod makinesi arayuzu"),
    ("common/cdtp_core/src/robot_logic.cpp", "Mod makinesi, LQR, hareket, telemetri"),
    ("common/cdtp_core/src/imu_filter.h", "Tumleyen filtre, eksen eslemesi"),
    ("common/cdtp_core/src/dock_fsm.h", "Otonom yanasma durum makinesi"),
    ("common/cdtp_core/src/ir_frame.h", "IR cerceve sayaci"),
    ("common/cdtp_core/src/core_math.h", "Yardimcilar, trapez profil"),
    ("common/cdtp_core/src/battery.h", "Pil yuzdesi"),
    ("common/cdtp_core/src/protocol.h", "Eldiven paketi (eldivenle ortak)"),
    ("common/cdtp_core/library.json", "Kutuphane tanimi"),
    ("tools/mass_budget.py", "Kutle butcesi"),
    ("tools/lqr_design.py", "Model ve LQR tasarimi"),
]


def main():
    blocks = []
    total = 0
    for i, (rel, what) in enumerate(FILES):
        text = (ROOT / rel).read_text(encoding="utf-8")
        n = text.count("\n") + 1
        total += n
        blocks.append(
            f'<details class="code"><summary><b>{html.escape(rel)}</b><span>{html.escape(what)} · {n} satır</span>'
            f'<button class="copy" data-target="src{i}" type="button">kopyala</button></summary>'
            f'<pre id="src{i}">{html.escape(text)}</pre></details>'
        )
    src = (ROOT / "docs/robot_src.html").read_text(encoding="utf-8")
    out = src.replace("<!--KOD-->", f'<p class="mono">{len(FILES)} dosya, {total} satır</p>\n' + "\n".join(blocks))
    (ROOT / "docs/robot.html").write_text(out, encoding="utf-8")
    print(f"docs/robot.html: {len(FILES)} dosya, {total} satir")


if __name__ == "__main__":
    main()
