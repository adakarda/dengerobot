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
    ("twin/twin.py", "MuJoCo dijital ikizi"),
    ("twin/bridge.cpp", "Ikiz koprusu (RobotLogic <-> MuJoCo)"),
]


def tests():
    def rows(path):
        p = ROOT / path
        return [l.split("	") for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

    def pill(r):
        return '<span class="pill p-ok">geçti</span>' if r == "GECTI" else '<span class="pill p-warn">kaldı</span>'

    out = []
    for title, path in (("C++ simülasyonu", "sim/results/summary.tsv"), ("MuJoCo dijital ikizi", "twin/results/summary.tsv")):
        rs = rows(path)
        n = sum(r[2] == "GECTI" for r in rs)
        out.append(f'<h3>{title}: {n}/{len(rs)}</h3><div class="tbl"><table><thead><tr><th>Test</th><th>Ölçülen</th><th>Sonuç</th></tr></thead><tbody>')
        out += [f"<tr><td><b>{html.escape(r[0])}</b> {html.escape(r[1])}</td><td>{html.escape(r[3])}</td><td>{pill(r[2])}</td></tr>" for r in rs]
        out.append("</tbody></table></div>")
    return "\n".join(out)


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
    src = src.replace("<!--TESTLER-->", tests())
    out = src.replace("<!--KOD-->", f'<p class="mono">{len(FILES)} dosya, {total} satır</p>\n' + "\n".join(blocks))
    (ROOT / "docs/robot.html").write_text(out, encoding="utf-8")
    print(f"docs/robot.html: {len(FILES)} dosya, {total} satir")


if __name__ == "__main__":
    main()
