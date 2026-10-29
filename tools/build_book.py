"""Robot yapim kitabi: egitimler + semalar + dogrulama + tum kodlar -> docs/CDTP_Denge_Robotu_Kitap.pdf

Kaynaklar: docs/robot_src.html (semalar), sim/results/summary.tsv, twin/results/summary.tsv,
docs/tutarlilik.md, tools/ref/github_karsilastirma.tsv ve kaynak dosyalar.
Calistir: python tools/build_book.py   (Edge ya da Chrome ile PDF basar)
"""
import datetime
import html
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_robot_doc  # noqa: E402

rd = lambda p: (ROOT / p).read_text(encoding="utf-8")
esc = html.escape

CODE = [
    ("Robot firmware", ["firmware/robot/platformio.ini", "firmware/robot/src/main.cpp", "firmware/robot/src/pins.h",
                        "firmware/robot/src/hw.h", "firmware/robot/src/links.h"]),
    ("Ortak çekirdek (robotta çalışan karar mantığı)", [
        "common/cdtp_core/library.json", "common/cdtp_core/src/cdtp_config.h", "common/cdtp_core/src/gains.h",
        "common/cdtp_core/src/robot_logic.h", "common/cdtp_core/src/robot_logic.cpp",
        "common/cdtp_core/src/imu_filter.h", "common/cdtp_core/src/dock_fsm.h", "common/cdtp_core/src/ir_frame.h",
        "common/cdtp_core/src/core_math.h", "common/cdtp_core/src/battery.h", "common/cdtp_core/src/protocol.h",
        "common/cdtp_core/src/gesture.h"]),
    ("Tasarım araçları", ["tools/mass_budget.py", "tools/lqr_design.py", "tools/check_consistency.py",
                          "tools/run_sim.sh", "tools/plot_sim.py"]),
    ("C++ simülasyonu", ["sim/plant.h", "sim/harness.h", "sim/sim_main.cpp", "sim/unit_tests.h"]),
    ("MuJoCo dijital ikizi", ["twin/twin.py", "twin/bridge.cpp", "tools/plot_twin.py"]),
    ("3B baskı ve KiCad şeması", ["cad/olcu.py", "cad/robot_cad.py", "cad/ciz.py", "tools/kicad_sema.py"]),
]


def tsv(path):
    p = ROOT / path
    if not p.exists():
        return []
    return [l.split("\t") for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def pill(s):
    return f'<span class="pill {"p-ok" if s == "GECTI" else "p-bad"}">{"geçti" if s == "GECTI" else "kaldı"}</span>'


def test_tables():
    sim = tsv("sim/results/summary.tsv")
    twin = {r[0]: r for r in tsv("twin/results/summary.tsv")}
    out = ['<div class="tbl"><table><thead><tr><th>Test</th><th>C++ simülasyonu</th><th>Sonuç</th></tr></thead><tbody>']
    for r in sim:
        out.append(f"<tr><td><b>{esc(r[0])}</b> {esc(r[1])}</td><td class='small'>{esc(r[3])}</td><td>{pill(r[2])}</td></tr>")
    out.append("</tbody></table></div>")
    if twin:
        out.append('<h3>MuJoCo dijital ikizi</h3><div class="tbl"><table><thead><tr><th>Test</th><th>Dijital ikiz</th><th>Sonuç</th></tr></thead><tbody>')
        for r in twin.values():
            out.append(f"<tr><td><b>{esc(r[0])}</b> {esc(r[1])}</td><td class='small'>{esc(r[3])}</td><td>{pill(r[2])}</td></tr>")
        out.append("</tbody></table></div>")
    return "\n".join(out)


def code_appendix():
    parts = []
    for group, files in CODE:
        parts.append(f'<h3 class="code-group">{esc(group)}</h3>')
        for f in files:
            p = ROOT / f
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            n = text.count("\n") + 1
            parts.append(f'<div class="codefile"><div class="codename">{esc(f)} <span>{n} satır</span></div>'
                         f'<pre>{esc(text)}</pre></div>')
    return "\n".join(parts)


def md_table(path):
    lines = [l for l in rd(path).splitlines() if l.startswith("|")]
    if len(lines) < 3:
        return ""
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    body = [[c.strip() for c in l.strip("|").split("|")] for l in lines[2:]]
    h = "".join(f"<th>{esc(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(
        f"<td>{pill('GECTI') if c == 'uygun' else (pill('KALDI') if c == 'UYUMSUZ' else esc(c))}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tbl"><table class="small"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def github_table():
    rows = tsv("tools/ref/github_karsilastirma.tsv")
    if not rows:
        return ""
    h = "".join(f"<th>{esc(c)}</th>" for c in rows[0])
    b = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<div class="tbl"><table class="small"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


TUTORIALS = r"""
<section class="chapter" id="e1">
<h2>Eğitim 1 · Geliştirme ortamını kurma</h2>
<ol class="steps">
<li>Git, Python 3.13 ve VS Code kurun. VS Code'da <b>PlatformIO IDE</b> eklentisini yükleyin.</li>
<li>Depoyu bilgisayarınıza alın: <code>git clone &lt;takım-reposu&gt;</code> ya da proje klasörünü kopyalayın.</li>
<li>Python paketleri: <code>pip install numpy scipy matplotlib mujoco</code>.</li>
<li>Simülasyonu derlemek için bir C++ derleyicisi gerekir (MinGW g++ ya da Linux gcc). Git Bash'te: <code>bash tools/run_sim.sh</code>. Çıktının sonunda <code>OZET: 20/20</code> görünmeli.</li>
<li>Dijital ikiz: <code>python twin/twin.py</code>. Çıktı <code>twin/results/</code> klasörüne yazılır.</li>
<li>Firmware'i derleme: VS Code'da <code>firmware/robot</code> klasörünü açın, alttaki çubukta ✓ (Build). İlk derlemede ESP32 araçları iner (~1 GB); sonraki derlemeler saniyeler sürer.</li>
</ol>
</section>

<section class="chapter" id="e2">
<h2>Eğitim 2 · Montaj sırası</h2>
<ol class="steps">
<li><b>Baskı:</b> 3 kat, V-yuva ve 2 motor tutucu (Eğitim 7, bölüm "Şasi: 3B baskı parçaları").</li>
<li><b>Motorlar:</b> baskı tutucularla kat 1'in altına; mil eksantrik, motor gövdesi milin 7 mm altında. Tekerleri 6 mm D göbekle takın, vidaları sıkın (gevşek göbek denge döngüsünde boşluk yapar).</li>
<li><b>Kat 1 üstü:</b> BTS7960 × 2 arkada, MPU6050 tam ortada ve teker ekseni hizasında (X ileri, bileşenler yukarı), önde LM2596, sigorta, WAGO × 2, C5 (1000 µF). SR5100 kablo üstünde, makaronlu.</li>
<li><b>V-yuva:</b> kat 1 ile kat 2 arasına önde; pogo pimler zeminden 102 mm (+) ve 77 mm (−), mıknatıslar ortada 89,5 mm.</li>
<li><b>Kat 2:</b> altta ana kart (10 mm naylon distans, ESP32 aşağı bakar); üstte pil yuvası, BMS, XT60 ve ±15° IR göz tutucuları.</li>
<li><b>Kat 3:</b> ilaç kutusu cebi solda, acil stop sağda; ikisi de öne kaydırılmış (kütle merkezi eksen üstünde).</li>
<li><b>Kablolama:</b> Kablo listesindeki sırayla (W1 → W44). Önce pil/BMS (W1–W6), sonra 12 V (W7–W19), şarj (W20–W23), en son sinyal (W24–W30).</li>
<li><b>Tezgâh testleri:</b> "Montaj ve tezgâh testleri" bölümündeki 10 adım. Hepsi geçmeden motorlara EN vermeyin.</li>
</ol>
</section>

<section class="chapter" id="e3">
<h2>Eğitim 3 · İlk çalıştırma ve kalibrasyon</h2>
<ol class="steps">
<li><b>Yükleme:</b> JP1'i çıkarın, USB'yi takın, Upload. Seri monitör 115200 baud.</li>
<li><b>Açılış:</b> "Jiroskop kalibrasyonu" yazısı çıkarken robotu oynatmayın (2 s). <code>Robot MAC</code> satırını eldiven koduna yazın.</li>
<li><b>IMU yönü:</b> robotu öne eğin: telemetride <code>tilt</code> artmalı. Sola çevirin: <code>yaw</code> artmalı. Değilse <code>imu_filter.h</code> içindeki <code>AxisMap</code> işaretlerini değiştirin.</li>
<li><b>Enkoder:</b> tekeri elle 10 tur ileri: <code>x</code> ≈ 2,04 m. Değilse <code>ENC_COUNTS_PER_REV</code>; işaret tersse <code>ENC_*_INVERT</code>.</li>
<li><b>Motor yönü:</b> tekerler havadayken <code>mtest</code>: önce sol, sonra sağ teker ileri dönmeli. Değilse <code>MOTOR_*_INVERT</code>.</li>
<li><b>Model:</b> parçaları tartın, <code>tools/mass_budget.py</code>'yi güncelleyin, kütle merkezini ip ile asarak doğrulayın. <code>python tools/lqr_design.py</code> → <code>bash tools/run_sim.sh</code> → <code>python twin/twin.py</code>. Hepsi geçerse yükleyin.</li>
<li><b>İlk denge:</b> kutusuz, iki el yakında. Robotu dik tutun; 0,5 s sonra kendisi tutar. Sürekli bir yöne kayıyorsa en rahat durduğu açıda tutup <code>cal</code>.</li>
<li><b>Kutulu denge, ±10°, eldiven adımları, istasyon</b> sırasıyla. Her aşamadan sonra <code>stat</code> ile döngü süresi ve paket kaybına bakın.</li>
<li><b>Final öncesi:</b> <code>main.cpp</code> içinde <code>FREEZE = true</code>, son kez yükleyin. Şartname gereği finalde parametre değiştirilmez.</li>
</ol>
</section>

<section class="chapter" id="e4">
<h2>Eğitim 4 · Model ve kazançları güncelleme</h2>
<p>Kazançlar elle ayarlanmaz; robotun fiziksel modelinden hesaplanır.</p>
<ol class="steps">
<li><code>tools/mass_budget.py</code>: her parçanın gerçek kütlesi ve teker ekseninden yüksekliği.</li>
<li><code>tools/lqr_design.py</code>: motor sabitleri (Ke = 12 V / boşta hız rad/s, R = 12 V / kilit akımı), iz genişliği. Çalıştırınca <code>gains.h</code> yeniden yazılır.</li>
<li>Ağırlıkları değiştirmek isterseniz: <code>python tools/lqr_design.py x=0.06 v=0.08</code> (izin verilen en büyük hata, Bryson kuralı).</li>
<li>Her değişiklikten sonra iki doğrulama: <code>bash tools/run_sim.sh</code> (20 test) ve <code>python twin/twin.py</code> (bağımsız MuJoCo modeli).</li>
<li>Belgeler ile kodun uyumu: <code>python tools/check_consistency.py</code>.</li>
</ol>
</section>

<section class="chapter" id="e5">
<h2>Eğitim 5 · Telefon (BLE) ve eldiven arayüzü</h2>
<div class="tbl"><table><thead><tr><th>Ne</th><th>Değer</th></tr></thead><tbody>
<tr><td>BLE adı</td><td><code>CDTP-Robot</code></td></tr>
<tr><td>Servis</td><td><code>6e400001-cd7b-4e3a-9a40-2026cd7b0001</code></td></tr>
<tr><td>Telemetri (notify, 1 Hz, JSON)</td><td><code>6e400002-cd7b-4e3a-9a40-2026cd7b0001</code></td></tr>
<tr><td>Komut (write, metin)</td><td><code>6e400003-cd7b-4e3a-9a40-2026cd7b0001</code></td></tr>
<tr><td>Telemetri alanları</td><td>seq, t, bat, v, tilt, chg, mode, mot, dir, task, dock, x, yaw, glove, ir</td></tr>
<tr><td>Görev seçimi</td><td><code>task=0</code> statik · <code>1</code> yönlendirme · <code>2</code> şarj · <code>3</code> bütünleşik</td></tr>
<tr><td>Eldiven paketi</td><td>ESP-NOW kanal 1, 12 bayt, 20 Hz, TEAM_KEY + CRC-8; 0,3 s gelmezse robot durur</td></tr>
<tr><td>Eldiven komutları (adım modu)</td><td>ileri/geri = 0,5 m, sola/sağa = 90°, düz el = dur</td></tr>
</tbody></table></div>
</section>

<section class="chapter" id="e6">
<h2>Eğitim 6 · Sorun giderme</h2>
<div class="tbl"><table><thead><tr><th>Belirti</th><th>Olası neden</th><th>Ne yapılır</th></tr></thead><tbody>
<tr><td>Robot dengeye girer girmez bir yöne fırlıyor</td><td>Jiroskop ya da motor yönü ters</td><td>Eğitim 3, adım 3 ve 5. Hızlı öne eğince jiroskop Y pozitif olmalı.</td></tr>
<tr><td>Robot titriyor, ses yapıyor</td><td>Gevşek göbek, jumper teması, ölü bölge büyük</td><td>Göbek vidaları, jumper'ları sıcak silikonla sabitleme, <code>MOTOR_DEADBAND_V</code> ölçümü</td></tr>
<tr><td>Durduktan sonra yavaşça kayıyor</td><td>Denge noktası ofseti</td><td>Birkaç saniye bekleyince kendisi öğrenir; kalıcı için <code>cal</code></td></tr>
<tr><td>Eldiven komutu gecikiyor</td><td>ESP-NOW kaybı, kanal farkı</td><td><code>stat</code>: kayıp sayısı. İki kart da kanal 1.</td></tr>
<tr><td>İstasyonu bulamıyor</td><td>38 kHz ayarı, göz açısı, LED gücü</td><td>İstasyon tezgâh testi, gözler ±15°, R8 22–150 Ω</td></tr>
<tr><td>Temas var ama şarj modu yok</td><td>GPIO34 bölücüsü, diyot yönü</td><td>J9-2 gerilimi ≥ 2 V olmalı; SR5100 çizgisi BMS tarafında</td></tr>
<tr><td>Sigorta atıyor</td><td>Kilit akımı yüksek</td><td>Tekeri tutup akım ölçün; 2,5 A üstü ise 7,5 A sigorta</td></tr>
<tr><td>MPU6050 bulunamadı</td><td>I2C kablosu, AD0</td><td>SDA 21, SCL 22, AD0 → GND, 3V3 besleme</td></tr>
</tbody></table></div>
</section>

<section class="chapter" id="e7">
<h2>Eğitim 7 · 3B baskı parçaları</h2>
<ol class="steps">
<li>Parçalar gelince kumpasla ölçün. <code>cad/olcu.py</code>'de <code>(OLC)</code> yazan her satırı kendi parçanızla karşılaştırın: BTS7960 delik aralığı, motor ön yüzü delikleri ve burç çapı, pogo pim çapı, ana kart delikleri, pil yuvası.</li>
<li>Gerekli paketler: <code>pip install manifold3d trimesh matplotlib</code>. Sonra <code>python cad/robot_cad.py</code>. Çıktının sonunda <code>TUMU GECTI</code> görünmeli; bir denetim kalırsa hangi parçanın neye girdiği yazar.</li>
<li><code>python cad/ciz.py</code> önizleme resimlerini yeniler. Montajı döndürerek görmek için <code>cad/montaj.glb</code>'yi herhangi bir 3B görüntüleyicide açın (Windows 3D Viewer, Blender, gltf-viewer).</li>
<li><code>cad/stl/</code> altındaki altı dosyayı dilimleyiciye alın. Dosyalar zaten baskı yönünde, destek kapalı. PLA/PETG, 0,2 mm katman, 3 duvar, %30 gyroid dolgu.</li>
<li>Önce <code>motor_tutucu_sol.stl</code>'yi basıp motoru takarak deneyin: 6 delik ve burç oturmalı. Oturmazsa <code>MOTOR_DELIK_ACI0</code> ve <code>MOTOR_BURC_D</code>'yi düzeltip yeniden üretin.</li>
<li>Katları basın, modülleri ceplerine kuru takın. Sıkıysa <code>BOSLUK</code>'u 0,1 mm artırın.</li>
<li>Montaj sırası: motor tutucular kat 1'in altına, V-yuva kat 1'e, kat 1 modülleri, 30 mm distanslar, ana kart kat 2'nin altına (10 mm naylon distans), V-yuva üst kaması kat 2'ye, kat 2 modülleri, 50 mm distanslar, kat 3, acil stop ve kutu.</li>
<li>Yerleşim veya parça değişirse <code>tools/mass_budget.py</code>'deki konumları güncelleyin. Betik, kütle bütçesini 3B modelle karşılaştırır. Sonra Eğitim 4'teki gibi kazançları yeniden üretin.</li>
</ol>
</section>

<section class="chapter" id="e8">
<h2>Eğitim 8 · KiCad şeması</h2>
<ol class="steps">
<li>KiCad 10'u kurun (kicad.org ya da <code>winget install KiCad.KiCad</code>).</li>
<li>KiCad'de <b>Dosya → Proje aç</b> → <code>elektronik/cdtp_robot.kicad_pro</code> → şema düzenleyicisi. Modül sembolleri proje kütüphanesinden (<code>cdtp</code>) kendiliğinden yüklenir.</li>
<li>Bir hattı bulmak için etikete tıklayın: KiCad aynı adlı bütün etiketleri vurgular. Kablo numaraları ve pin sırası için robot dosyasındaki kablo listesine bakın.</li>
<li>Bağlantı değişirse <code>tools/kicad_sema.py</code>'deki <code>GRUPLAR</code> listesini değiştirin ve <code>python tools/kicad_sema.py</code> çalıştırın. Betik KiCad'in ERC'sini koşar, netlisti çıkarır ve her ESP32 pinini <code>pins.h</code> ile, güç hatlarını kablo listesiyle karşılaştırır.</li>
<li>Firmware'de bir pin değişirse önce <code>pins.h</code>'yi, sonra şemayı güncelleyin. Biri unutulursa denetim "ESP32 pinleri = pins.h" satırında kalır.</li>
<li>Şemanın A3 çıktısı bu kitabın son sayfasıdır; ayrıca <code>elektronik/cdtp_robot.pdf</code>.</li>
</ol>
</section>
"""

VERIFY_INTRO = r"""
<section class="chapter" id="dogrulama">
<h2>Doğrulama</h2>
<p>Yazılan ve çizilen her şey üç bağımsız yolla kontrol edildi: GitHub'daki çalışan robotlarla karşılaştırma, belge ile kodun otomatik tutarlılık denetimi ve MuJoCo fizik motoruyla kurulan dijital ikiz.</p>
<h3>Dijital ikizde bulunan ve düzeltilen hatalar</h3>
<div class="tbl"><table><thead><tr><th>Hata</th><th>Etki</th><th>Düzeltme</th></tr></thead><tbody>
<tr><td><b>Jiroskop işareti ters</b>. Kod, X ileri / Z yukarı monte edilmiş MPU6050'de öne düşüşü jiroskop Y'de negatif varsayıyordu. Gerçekte pozitif okunur (sağ el kuralı, ikizde ölçüldü). İlk C++ simülasyonu aynı yanlış varsayımla yazıldığı için fark etmedi.</td><td>Gerçek robot ilk anda düşerdi: tümleyen filtre jiroskopla ivmeölçeri ters yönde birleştirir.</td><td><code>AxisMap.pitchSign = +1</code>; C++ simülasyonu da fiziksel kurala çevrildi.</td></tr>
<tr><td><b>Enkoder bağıl açı ölçer</b>. Enkoder tekerin gövdeye göre dönüşünü sayar; kod bunu yere göre yol sanıyordu.</td><td>Eğim değişirken hız ölçümünde r·θ̇ kadar hata (~0,03 m/s), K_V ile ~2 V yanlış komut.</td><td><code>x = r·(φ_bağıl) + r·θ</code>; simülasyonun enkoder modeli de bağıl açıya çevrildi.</td></tr>
<tr><td><b>Durduktan sonra kayma</b>. IR gözleri ve V-yuva öne 1,4 mm kütle kaydırıyor; robot −1,1° eğik dengede durur, LQR bunu 3,6 cm konum hatasıyla karşılar.</td><td>1 m testinde durmada 5 cm'ye yakın kayma.</td><td>Robot dururken denge açısını yavaşça öğrenir (±3° sınırlı). LQI (konum integrali) de denendi; yanaşma ve dönüşü bozduğu için alınmadı.</td></tr>
<tr><td><b>Şarjda geri yuvarlanma</b>. Motorlar kesilince tekerler serbest kalıyor; robot yuvarlak direkten geri yuvarlandı, eğim 11,6°'ye çıktı, pim temastan ayrıldı.</td><td>Şarj göstergesi söner, robot 2 s sonra BEKLE'ye düşer; C3 ve C5 başarısız olur.</td><td>V-yuvaya iki neodyum mıknatıs, direğe çelik şerit (şartname manyetik sabitlemeye izin veriyor). İkizde robot 0,2° eğimle temaslı kaldı.</td></tr>
<tr><td><b>Sivri V-yuva</b>. İkizde ilk kurulan sivri V'de Ø40 direk pimlere 8 mm kala kanatlara takıldı.</td><td>Hiç temas yok.</td><td>Belgedeki 20 mm düz arka şerit zorunlu hale getirildi ve açıklandı.</td></tr>
<tr><td><b>Ayrıldıktan sonra yeniden yanaşma</b>. Şarj görevinde eldivenle "geri" deyince robot 1 s sonra kendiliğinden yeniden yanaşıyordu.</td><td>Kullanıcı robotu istasyondan alamaz.</td><td>Ayrıldıktan sonra 10 s yanaşma beklemesi (<code>UNDOCK_HOLD_S</code>).</td></tr>
<tr><td><b>Belgede eksik bilgi</b>. Robot yapım dosyasında eldiven zaman aşımı yazmıyordu.</td><td>Belge ile kod arasında boşluk.</td><td>Eklendi; tutarlılık denetimi 41/41.</td></tr>
</tbody></table></div>
<h3>GitHub karşılaştırması</h3>
<p>GitHub'da en çok yıldızlı ve bize en yakın 6 denge robotu indirildi. Kontrol yöntemi, döngü hızı, filtre, düşme sınırı ve kazançlar karşılaştırıldı. En yakın örnek (suelioalencar, ESP32, 65 mm teker, enkoderli DC motor, gerilim cinsinden LQI) gerçek robotta çalışan kazançlar kullanıyor. Bu kazançlar bizim dijital ikizimizde de robotu dengede tuttu; yani ikiz gerçekçi bir bölgede. Kazançlarımız aynı işaret yapısında ve aynı büyüklükte.</p>
<!--GITHUB-->
<h3>Belge ↔ kod tutarlılık denetimi</h3>
<p><code>tools/check_consistency.py</code>: firmware pinleri, takım sitesindeki pin şeması, yapım dosyasındaki pin tablosu ve header sıraları, ayar sabitleri, LQR kazançları, BLE UUID'leri ve bölücü hesapları karşılaştırıldı.</p>
<!--TUTARLILIK-->
<h3>Dijital ikiz nasıl kuruldu</h3>
<ul>
<li>Gövde, kütle bütçesindeki her parçadan ayrı kutu olarak kuruldu. MuJoCo kütle merkezini ve ataleti kendisi hesaplar; C++ modelindeki elle girilen sayılar kullanılmaz.</li>
<li>Teker–zemin teması, kayma, ilaç kutusunun cepte durması ve V-yuvanın direğe oturması gerçek temas hesabıyla çözülür.</li>
<li>MPU6050 ölçümleri MuJoCo'nun ivmeölçer ve jiroskop sensörlerinden alınır. Bunlara gürültü ve 42 Hz süzgeç eklenir. Enkoder, teker eklemi ile gövde arasındaki bağıl açıdan hesaplanır.</li>
<li>Karar mantığı ESP32'deki <code>RobotLogic</code> sınıfının kendisidir: <code>twin_bridge.exe</code> her 5 ms'de bir sensör satırı alır ve motor komutunu döndürür.</li>
</ul>
<!--IKIZGRAF-->
</section>
"""

PRINT_CSS = r"""
<style>
@page { size: A4; margin: 14mm 12mm 16mm 12mm; }
:root, :root[data-theme="dark"] { color-scheme: light !important; }
@media print { body { padding: 0 !important; } }
body { font-size: 10.5pt; }
.wrap { max-width: none; gap: 22px; }
nav.toc, .copy { display: none !important; }
section, .chapter { break-before: page; }
section h2, .chapter h2 { font-size: 20pt; }
.cover { break-after: page; min-height: 250mm; display: flex; flex-direction: column; justify-content: center; gap: 18px; }
.cover h1 { font-size: 34pt; }
.diagram { break-inside: avoid; }
.diagram svg { min-width: 0 !important; }
.tbl { overflow: visible; }
table { font-size: 8.6pt; }
tr, .box, figure { break-inside: avoid; }
details.code pre, .codefile pre { max-height: none !important; overflow: visible !important; white-space: pre-wrap; word-break: break-all; font-size: 6.9pt; line-height: 1.35; }
.codefile { border: 1px solid var(--line); border-radius: 4px; margin-bottom: 8px; }
.codename { font-family: var(--mono); font-size: 8.5pt; padding: 4px 8px; background: var(--ink-soft); font-weight: 600; }
.codename span { font-weight: 400; color: var(--muted); }
.codefile pre { margin: 0; padding: 6px 8px; background: var(--code-bg); }
h3.code-group { break-before: page; }
.small { font-size: 8.4pt; }
.steps { counter-reset: s; list-style: none; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.steps li { counter-increment: s; position: relative; padding-left: 2em; }
.steps li::before { content: counter(s); position: absolute; left: 0; top: 0; font-family: var(--mono); font-weight: 600; color: var(--ink); }
.p-bad { color: var(--bad); background: var(--bad-bg); }
.toc2 { columns: 2; font-size: 10pt; }
.toc2 li { break-inside: avoid; }
</style>
"""


def main():
    src = rd("docs/robot_src.html")
    style = src[src.index("<style>"):src.index("</style>") + 8]
    body = src[src.index('<div class="wrap">') + len('<div class="wrap">'):src.rindex("<footer>")]
    # header ve kod bolumu kitapta ayri
    body = re.sub(r"<header>.*?</header>", "", body, flags=re.S)
    body = re.sub(r'<!-- =+ KODLAR =+ -->.*', "", body, flags=re.S)
    body = body.replace("<!--TESTLER-->", test_tables())
    body = build_robot_doc.ekler(body)
    sections = re.findall(r'<section id="(\w+)">\s*<div class="sec-head"><span class="sec-num">\d+</span><h2>(.*?)</h2>', body)
    verify = VERIFY_INTRO.replace("<!--GITHUB-->", github_table()).replace("<!--TUTARLILIK-->", md_table("docs/tutarlilik.md"))
    imgs = ""
    for name, cap in (("ikiz_karsilastirma.png", "C++ simülasyonu ile dijital ikiz: aynı senaryo, aynı firmware mantığı"),
                      ("ikiz_yanasma.png", "Dijital ikizde V-yuva ile direğe yanaşma, üstten")):
        p = ROOT / "docs/img" / name
        if p.exists():
            imgs += f'<figure><img src="img/{name}" alt="{esc(cap)}"><figcaption>{esc(cap)}</figcaption></figure>'
    verify = verify.replace("<!--IKIZGRAF-->", f'<div class="grid2">{imgs}</div>' if imgs else "")
    today = datetime.date.today().strftime("%d.%m.%Y")
    toc = ['<li>Eğitim 1 · Geliştirme ortamı</li>', '<li>Eğitim 2 · Montaj sırası</li>', '<li>Eğitim 3 · İlk çalıştırma ve kalibrasyon</li>',
           '<li>Eğitim 4 · Model ve kazançlar</li>', '<li>Eğitim 5 · Telefon ve eldiven arayüzü</li>', '<li>Eğitim 6 · Sorun giderme</li>',
           '<li>Eğitim 7 · 3B baskı parçaları</li>', '<li>Eğitim 8 · KiCad şeması</li>']
    toc += [f"<li>{esc(re.sub('<.*?>', '', t))}</li>" for _, t in sections]
    toc += ["<li>Doğrulama: dijital ikiz, GitHub, tutarlılık</li>", "<li>Ek: tüm kodlar</li>", "<li>Ek: KiCad şeması (A3, son sayfa)</li>"]
    cover = f"""
<div class="cover">
  <span class="eyebrow">YTÜ EEF ÇDTP · 2026-27 Güz · Kontrol ve Otomasyon</span>
  <h1>İki tekerlekli denge robotu<br>yapım kitabı</h1>
  <p class="lede">Eğitimler, parça listesi, güç ve sinyal şemaları, KiCad şeması, ana kart, kablo listesi, 3B baskı şasi, şarj teması, firmware, testler, dijital ikiz doğrulaması ve robotun tüm kaynak kodu.</p>
  <div class="facts"><span>Sürüm: <b>v1.3</b></span><span>Tarih: <b>{today}</b></span><span>Depo: <b>cdtp-denge-robotu</b></span></div>
  <h3>İçindekiler</h3><ol class="toc2">{''.join(toc)}</ol>
</div>"""
    code = f'<section class="chapter" id="kodlar"><h2>Ek · Tüm kodlar</h2><p>Robotta çalışan firmware, ortak çekirdek, tasarım araçları, simülasyon ve dijital ikiz.</p>{code_appendix()}</section>'
    page = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>CDTP Denge Robotu Kitabı</title>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap">'
            f'{style}{PRINT_CSS}</head><body><div class="wrap">{cover}{TUTORIALS}{body}{verify}{code}</div></body></html>')
    out_html = ROOT / "docs/kitap.html"
    out_html.write_text(page, encoding="utf-8")
    pdf = ROOT / "docs/CDTP_Denge_Robotu_Kitap.pdf"
    for exe in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if pathlib.Path(exe).exists():
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                            f"--print-to-pdf={pdf}", out_html.as_uri()], check=True, timeout=180,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break
    sema = ROOT / "elektronik/cdtp_robot.pdf"
    if pdf.exists() and sema.exists():
        try:
            import pymupdf
            kitap = pymupdf.open(pdf)
            kitap.insert_pdf(pymupdf.open(sema))
            kitap.save(pdf, incremental=True, encryption=0)
        except ImportError:
            print("pymupdf yok: KiCad semasi kitaba eklenmedi (pip install pymupdf)")
    print("yazildi:", out_html.name, pdf.name if pdf.exists() else "(PDF yok)", f"{pdf.stat().st_size//1024} KB" if pdf.exists() else "")


if __name__ == "__main__":
    main()
