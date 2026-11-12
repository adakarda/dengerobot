"""38 pinli ESP32'den 30 pinliye gecis rehberi uretici -> docs/ESP32_38den_30a_gecis.html
Calistir: python docs/gecis_uret.py   (breadboard_uret.py'den iki surumun pin konumlarini okur)"""
import json
import os
import pathlib
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
CODE = r'''
import json, sys
sys.path.insert(0, r"%s")
import breadboard_uret as B
names = [("4","GPIO4","STBY (15)"),("27","GPIO27","AIN1 (16)"),("14","GPIO14","AIN2 (17)"),("16","GPIO16","BIN1 (18)"),("17","GPIO17","BIN2 (19)"),
         ("32","GPIO32","Sol enkoder A (26)"),("33","GPIO33","Sol enkoder B (27)"),("25","GPIO25","Sağ enkoder A (30)"),("26","GPIO26","Sağ enkoder B (31)"),
         ("22","GPIO22","MPU SCL (34)"),("21","GPIO21","MPU SDA (35)"),("19","GPIO19","MPU INT (37)"),
         ("VP","GPIO36 (VP)","Sol IR OUT (40)"),("VN","GPIO39 (VN)","Sağ IR OUT (43)"),
         ("3V3","3V3","+3,3 V rayına (9)"),("5V","5V / VIN","LM2596 OUT+ (7)")]
out = []
for k, label, use in names:
    c, r, pr = B.esp_find(k)
    out.append([label, use, c, r, pr])
g = B.esp_find("GND", True)
out.append(["GND (alt sıra)", "alt iç GND rayına (10)", g[0], g[1], g[2]])
print(json.dumps(out))
''' % str(here)


def load(v30):
    env = dict(os.environ, ESP30="1" if v30 else "0")
    r = subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, env=env, encoding="utf-8")
    if r.returncode:
        raise SystemExit(r.stderr)
    return json.loads(r.stdout)


a, b = load(False), load(True)
rows = []
for x, y in zip(a, b):
    ch = (x[2], x[3]) != (y[2], y[3])
    cls = ' class="chg"' if ch else ""
    rows.append(f'<tr{cls}><td>{x[0]}</td><td>{x[1]}</td><td>{x[2]}. sütun, {x[3]} <small>(pin {x[4]})</small></td><td>{y[2]}. sütun, {y[3]} <small>(pin {y[4]})</small></td></tr>')
table = "\n".join(rows)

HTML = '''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 30 pin geçişi</title>
<style>
:root{--bg:#f6f5f1;--fg:#1d2127;--mut:#5b6470;--card:#ffffff;--line:#dcdad2;--acc:#0b6b5d;--warn:#a4570b;--warnbg:#fbf0e0;--chg:#e6f2ee;--code:#ece9e1}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14181c;--fg:#e8e6df;--mut:#9aa3ad;--card:#1c2127;--line:#2e353d;--acc:#4cc2ac;--warn:#e8a458;--warnbg:#2a2217;--chg:#18312c;--code:#242b32;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14181c;--fg:#e8e6df;--mut:#9aa3ad;--card:#1c2127;--line:#2e353d;--acc:#4cc2ac;--warn:#e8a458;--warnbg:#2a2217;--chg:#18312c;--code:#242b32;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;padding-block:28px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
main{max-width:920px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
h1{font-size:28px;line-height:1.2;margin:0;text-wrap:balance}
h2{font-size:19px;margin:0 0 8px;text-wrap:balance}
p{margin:6px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;min-width:0}
.lead{color:var(--mut);font-size:17px}
.warn{background:var(--warnbg);border-color:var(--warn)}
.warn h2{color:var(--warn)}
ol,ul{margin:6px 0;padding-left:22px}li{margin:5px 0}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14.5px;min-width:560px}
th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
tr.chg td{background:var(--chg)}
small{color:var(--mut)}
code{font-family:ui-monospace,Consolas,monospace;font-size:13.5px;background:var(--code);padding:1px 5px;border-radius:4px}
.big{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.fact{border:1px solid var(--line);border-radius:10px;padding:11px}.fact b{display:block;font-size:17px;color:var(--acc)}
</style></head><body><main>
<header><h1>38 pinli ESP32'den 30 pinliye geçiş</h1>
<p class="lead">Kanka, kısa özet: <b>firmware aynı kalır</b>, kullandığımız 14 GPIO'nun hepsi 30 pinli kartta var. Değişen sadece breadboard'daki yerleşim: ESP32 daha kısa, pin satırı daha dar, 3V3 pini öbür sıraya geçiyor.</p></header>

<section class="card"><h2>Neyi değişti, neyi değişmedi</h2>
<div class="big">
<div class="fact"><b>Değişmez</b>Firmware, pin numaraları (GPIO4, 14, 16, 17, 19, 21, 22, 25, 26, 27, 32, 33, 36, 39), kazançlar, MPU6050, TB6612, LM2596, motorlar.</div>
<div class="fact"><b>Değişir</b>Breadboard sütunları ve satırları, 3V3 kablosunun yönü, pin satırı aralığı, USB sürücüsü olabilir.</div>
<div class="fact"><b>Dikkat</b>Modül ESP32-WROVER ise GPIO16 ve 17 kullanılamaz. Aşağıdaki uyarıya bak.</div>
</div></section>

<section class="card warn"><h2>Önce bunu kontrol et: WROOM mu WROVER mı</h2>
<p>Kartın üstündeki metal kapağa bak. <code>ESP32-WROOM-32</code> yazıyorsa sorun yok. <code>ESP32-WROVER</code> yazıyorsa GPIO16 ve 17 PSRAM için ayrılmıştır. BIN1 ve BIN2 çalışmaz. Bu durumda bana yaz, sağ motoru başka pinlere taşırız.</p></section>

<section class="card"><h2>1. Pin satırı aralığını ölç</h2>
<p>38 pinlide iki pin satırı arası 25,4 mm (10 delik), 30 pinlide genelde 22,86 mm (9 delik). Üreticiye göre değişir, bu yüzden cetvelle ölç.</p>
<ul><li><b>9 delik (22,86 mm):</b> pinleri <b>b ve i</b> satırına tak. Dışarıdaki <b>a ve j</b> satırı açık kalır. Kabloyu oraya takarsın, Dupont ucu sığar. Bu rehberdeki şema böyle çizildi.</li>
<li><b>10 delik (25,4 mm):</b> pinleri <b>a ve i</b> satırına tak. Üst sıra için kabloyu pinin altındaki b deliğine tak (ince, tek damarlı kablo), alt sıra için j deliğini kullan.</li></ul></section>

<section class="card"><h2>2. Pin pin yer değişimi</h2>
<p>Sütunlar aynı kalmaz çünkü pin sırası ve kart uzunluğu farklı. Açık yeşil satırlar değişen pinler. Karşı taraftaki modüller (MPU6050 23–30, TB6612 39→32, LM2596 41 ve 57, klemens 60–62) <b>aynı yerde kalır</b>.</p>
<div class="tw"><table><thead><tr><th>ESP32 pini</th><th>Kullanım (kablo no)</th><th>38 pinli</th><th>30 pinli</th></tr></thead><tbody>
{{TABLO}}
</tbody></table></div>
<p><small>Tabloda sütundan sonraki harf <b>kablonun takılacağı delik satırı</b>, parantez içi <b>pinin takılı olduğu satır</b>. Sütun numaraları ESP32'nin anten ucundaki pin 21. sütuna gelecek şekilde. 38 pinli kart 21→3, 30 pinli kart 21→7 sütunlarını kaplar. USB solda, yani 1–6. sütun tarafında.</small></p></section>

<section class="card"><h2>3. Değişen kablolar</h2>
<ol>
<li><b>Kablo 9 (3V3 → +3,3 V rayı):</b> 38 pinlide 3V3 alt sırada ve rayın hemen yanındaydı. 30 pinlide 3V3 <b>üst sıraya (a satırı)</b> geçer. Kablo kartın üstünden alt dış raya gider, uzundur.</li>
<li><b>Kablo 7 (LM2596 OUT+ → 5V):</b> 5V pini artık <b>VIN</b> yazar, 7. sütun, j satırı. Aynı iş: VIN pinine 5,0 V verirsin.</li>
<li><b>Kablo 10 (GND):</b> alt sıradaki GND pini 8. sütunda kalır. Üst sıradaki GND (8. sütun, a) kullanılmaz.</li>
<li><b>Diğer 15 sinyal kablosu:</b> yukarıdaki tablodaki yeni sütunlara taşınır. Satırlar 38 pinliyle aynı mantıkta: üst sıra için a, alt sıra için j.</li>
</ol>
<p>Üreteç kablo listesini senin için hazır verir: <code>breadboard_sema_30pin.html</code>. Doğrulayıcı iki sürümde de kısa devre, kopuk hat ve çakışan delik bulmadı.</p></section>

<section class="card"><h2>4. Kartın pin sırasını doğrula</h2>
<p>Şema yaygın DOIT DevKit V1 (30 pin) dizilimini kullanır. Anten ucundan USB ucuna doğru:</p>
<ul><li><b>Üst sıra (a/b tarafı):</b> D23, D22, TX0, RX0, D21, D19, D18, D5, D17 (TX2), D16 (RX2), D4, D2, D15, GND, 3V3</li>
<li><b>Alt sıra (i tarafı):</b> EN, VP (36), VN (39), D34, D35, D32, D33, D25, D26, D27, D14, D12, D13, GND, VIN</li></ul>
<p>Bazı "ESP-32S" kartlarda sıra farklı çıkabilir (örneğin 3V3 ile GND yer değiştirir). Takmadan önce pin yazılarını şemayla karşılaştır. Özellikle <b>3V3 ile VIN'i karıştırma</b>: VIN'e 5 V, 3V3'e hiçbir şey verilmez.</p></section>

<section class="card"><h2>5. Yazılım yükleme</h2>
<ul><li>Aynı komut: <code>pio run -d firmware/bench -t upload</code>. Kart tipi <code>esp32dev</code>, değişiklik yok.</li>
<li>Kartta <b>CH340</b> çipi varsa (USB yanındaki küçük çip) CP2102 sürücüsü yetmez, CH340 sürücüsü yükle.</li>
<li>Yükleme "Connecting..." diye takılırsa <b>BOOT</b> düğmesini basılı tut, bağlanınca bırak. Bazı kartlarda otomatik reset çalışmaz.</li>
<li>Kartı USB'ye takarken LM2596'dan gelen 5 V kablosunu (kablo 7) çıkar. İkisi aynı anda beslemesin.</li></ul></section>

<section class="card"><h2>6. Geçiş kontrol listesi</h2>
<ol><li>Modül yazısı WROOM mu, cetvelle pin satırı aralığı kaç delik.</li>
<li>Kartın pin sırasını bu sayfadaki dizilimle karşılaştır.</li>
<li>ESP32'yi 21→7. sütunlara, anten ucu 21'de olacak şekilde tak.</li>
<li>Önce GND kablosunu (10), sonra sinyal kablolarını, en son 3V3 (9) ve VIN (7) kablolarını bağla.</li>
<li>Multimetre ile bip testi: 3V3 ile GND arasında, VIN ile GND arasında bip çalmamalı.</li>
<li>Yazılımı yükle, <code>i</code> komutuyla I2C tara (MPU6050 0x68 görünmeli), enkoderi elle çevirip sayıyı kontrol et.</li></ol></section>
</main></body></html>'''
out = HTML.replace("{{TABLO}}", table)
(here / "ESP32_38den_30a_gecis.html").write_text(out, encoding="utf-8")
print("ok", len(out))
