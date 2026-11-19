# Denge kodu rehberi (tek dosyada her şey)

Bu dosya, ÇDTP iki tekerlekli denge robotunun yazılımını anlamak, derlemek, yüklemek ve ayarlamak için gereken her şeyi toplar.
Güncelleme: 2026-11-19. Kod: https://github.com/adakarda/dengerobot (takımın deposunda `modules/A-balancing-robot/`).

> **Durum özeti.** Model gerçek ölçülerle güncellendi, benzetimde 20/20 kabul testi geçiyor. ESP32 üzerinde sensörler
> (MPU6050, enkoderler) doğrulandı. **Motor testi yapılmadı ve robot gerçekte dengelenmedi.** Aşağıdaki "Bilinen eksikler" bölümünü oku.

---

## 1. Robot ve ölçüler

| Büyüklük | Değer | Kaynak |
|---|---|---|
| Toplam kütle (tekerlekler takılı) | 1225 g | terazi (pil dahil mi, doğrulanmadı) |
| Tekerlek + kaplin (tek) | 53 g | terazi |
| Tekerlek | Ø65 mm × 28 mm | kumpas |
| **Gövde kütlesi** `m_body` | **1,119 kg** | 1225 − 2 × 53 g |
| Ağırlık merkezi (zeminden) | 120 mm | yandan bakış |
| **Ağırlık merkezi (teker ekseninden)** `l_com` | **87,5 mm** | 120 − 32,5 |
| İz genişliği `track` | **270 mm** | 298 mm (dıştan dışa) − 28 mm |
| Motor | 12 V, 19:1 dişli, yaklaşık 530 rpm, Hall enkoder | katalog |
| Pil | 3S Li-ion/LiPo, 11,1 V (9,9–12,6 V) | tasarım |

**Tahmin olanlar (ölçülmeli):** gövde yunuslama ataleti `I_body` = 0,0066 kg m², dönme ataleti `I_yaw` = 0,0066 kg m².
Ölçmek için sarkaç testi: robotu ince bir telden as, 10 salınımın süresini ölç, `tools/lqr_design.py` içindeki `P` sözlüğünü güncelle.

---

## 2. Yazılım haritası

Tüm karar mantığı **donanımdan bağımsız çekirdekte** durur. Robot, eldiven ve PC benzetimi aynı kodu kullanır.

| Yol | Ne işe yarar |
|---|---|
| `common/cdtp_core/src/robot_logic.*` | Mod makinesi (BEKLE, DENGE, YANAŞMA, ŞARJ, DÜŞTÜ), LQR, hareket adımları, telemetri |
| `common/cdtp_core/src/cdtp_config.h` | **Tüm ayar sabitleri** (mekanik, filtre, güvenlik, hareket). Finalde bu dosya donar |
| `common/cdtp_core/src/gains.h` | LQR kazançları. **Elle düzenleme**, `tools/lqr_design.py` üretir |
| `common/cdtp_core/src/imu_filter.h` | Eksen eşlemesi, tümleyen filtre, Kalman eğim filtresi |
| `common/cdtp_core/src/protocol.h` | Eldiven paketi (ESP-NOW, CRC-8, takım anahtarı) |
| `firmware/robot/src/main.cpp` | ESP32 robot: 200 Hz denge görevi (çekirdek 1), bağlantılar (çekirdek 0), seri konsol |
| `firmware/robot/src/hw.h` | MPU6050, PCNT enkoder/IR sayacı, motor sürücü |
| `firmware/robot/src/pins.h` | Pin haritası |
| `firmware/robot/src/links.h` | ESP-NOW (eldiven) ve Wi-Fi WebSocket (telefon) |
| `firmware/bench/` | Denge kodu içermeyen donanım testi (I2C, MPU, enkoder, motor) |
| `firmware/glove/` | Eldiven ESP32-C3 |
| `tools/lqr_design.py` | Fiziksel model + LQR. `gains.h` ve `sim/plant_nominal.h` üretir |
| `tools/run_sim.sh` | PC benzetimi: birim testleri + 20 kabul testi |
| `sim/`, `twin/` | Benzetim, MuJoCo dijital ikizi |

---

## 3. Pin haritası (`pins.h`)

| İşlev | GPIO | Not |
|---|---|---|
| MPU6050 SDA / SCL / INT | 21 / 22 / 19 | adres 0x68, AD0 → GND |
| Sol motor ileri / geri | 27 / 14 | TB6612: AIN1 / AIN2 |
| Sağ motor ileri / geri | 16 / 17 | TB6612: BIN1 / BIN2. **WROVER kartta 16/17 PSRAM'e gider, WROOM kullan** |
| Motor etkinleştirme | 4 | TB6612: **STBY**, 10 kΩ ile GND'ye çekili |
| Sol enkoder A / B | 32 / 33 | 3,3 V ile beslenir |
| Sağ enkoder A / B | 25 / 26 | |
| IR gözler sol / sağ | 36 / 39 | VS1838B, 3,3 V'ta çalışır |
| Pil ölçümü / şarj plakası | 35 / 34 | 100k/27k bölücü. **Breadboardda henüz bağlı değil** (bkz. bölüm 9) |
| LED | 2 | kart üstündeki mavi LED |

**TB6612 notu.** Firmware BTS7960 stilinde çalışır (her yön için bir PWM pini, `EN` ortak). TB6612'de aynı iş şöyle yapılır:
`PWMA` ve `PWMB` pinleri **3,3 V'a** bağlanır (sürekli yüksek), hız `AIN1/AIN2` ve `BIN1/BIN2` üzerindeki PWM ile verilir,
`STBY` = `GPIO4`. `VM` motor gerilimi (12 V), `VCC` mantık gerilimi (3,3 V).

Breadboard bağlantıları ve sütun numaraları: `docs/breadboard_sema.html` (38 pin) ve `docs/breadboard_sema_30pin.html`
(30 pin ESP32). Geçiş rehberi: `docs/ESP32_38den_30a_gecis.html`.

---

## 4. Kontrol: model ve kazançlar

- **Model:** iki tekerlekli ters sarkaç + DC motor + dişli. Durum `[x, v, θ, ω]` = konum, hız, eğim, eğim hızı.
- **Kontrolcü:** LQR, `u = −K (s − s_ref)`, çıkış her motora gerilim (V). Dönüş için ayrı yaw PD.
- **Güncel kazançlar** (ölçülere göre, `gains.h`):

| Kazanç | Değer |
|---|---|
| `K_X` | −50,525 |
| `K_V` | −62,566 |
| `K_TH` | −107,938 |
| `K_OM` | −13,485 |
| `YAW_KP` / `YAW_KD` | 1,059 / 0,238 |

- **Yeniden hesaplama:** `python tools/lqr_design.py`. Ölçüyü `P` sözlüğüne yaz, çalıştır, `bash tools/run_sim.sh` ile testlerin geçtiğini gör.
- **Döngü:** 200 Hz, MPU6050 veri-hazır kesmesiyle tetiklenir. Eğim tahmini için varsayılan tümleyen filtre (`COMP_ALPHA = 0,98`);
  Kalman sürümü `-DCDTP_TILT_KALMAN=1` ile seçilir. LQG (`CDTP_LQG`) benzetimde kabul testlerini bozduğu için kapalı (`docs/KALMAN_FILTRE.md`).

**Önemli ayar sabitleri** (`cdtp_config.h`):

| Sabit | Değer | Anlamı |
|---|---|---|
| `WHEEL_RADIUS_M` | 0,0325 | teker yarıçapı |
| `TRACK_WIDTH_M` | 0,270 | iz genişliği |
| `ENC_COUNTS_PER_REV` | 836 | **doğrulanmadı**: tekeri 10 tur çevirip say |
| `ENC_RIGHT_INVERT`, `MOTOR_RIGHT_INVERT` | true | sağ motor ayna takılı (robotta denenmeli) |
| `FALL_ANGLE_DEG` | 40 | bunun üstünde motorlar kapanır |
| `ARM_ANGLE_DEG` / `ARM_HOLD_S` | 3° / 0,5 s | elle dik tutunca dengeye girer |
| `STEP_DIST_M` | 0,50 | ileri/geri komut adımı |
| `TURN_ANGLE_DEG` | 90 | dönüş komutu |
| `DUTY_MAX` | 0,95 | en yüksek PWM oranı |
| `GLOVE_TIMEOUT_S` | 0,30 | eldiven paketi gelmezse dur |

---

## 5. Derleme ve yükleme

```bash
pio run -d firmware/robot                       # robot yazılımı (derleme)
pio run -d firmware/bench -t upload             # donanım testi yükle
pio run -d firmware/robot -t upload             # robotu yükle
```

- Kart tipi `esp32dev`, platform `espressif32@6.9.0` (Arduino-ESP32 2.0.17). Kütüphane: `links2004/WebSockets@2.4.1`.
- **Sürücü:** CP2102 kartlarda Silicon Labs, CH340 kartlarda CH340 sürücüsü.
- **Yükleme "Connecting..." diye takılırsa:** BOOT düğmesini basılı tut, bağlanınca bırak. Yüklemeden sonra EN düğmesine bas.
- **Yüklerken** LM2596'dan gelen 5 V kablosunu (şemada kablo 7) çıkar; USB ve 5 V aynı anda beslemesin.
- 30 pinli ESP32 kullanılacaksa pin numaraları aynıdır, sadece breadboard yerleşimi değişir.

---

## 6. İlk çalıştırma sırası

1. **Bench testi** (`firmware/bench`, seri 115200): `i` I2C taraması (MPU6050 `0x68` görünmeli), `m` bir ölçüm
   (z ekseni ≈ ±9,8 m/s²), `p` akış (acc, gyro, enkoder, IR, duty). Tekerleği elle çevirip enkoder sayısını gör.
2. **Motor testi (bench):** `l 0.3`, `r 0.3`, `b 0.3`, durdurmak için `s` (en fazla ±0,5, 1,5 s komut kesilince otomatik durur).
   **Tekerlekler havada olsun.** Ters dönen motor için `MOTOR_*_INVERT`.
3. **Robot yazılımı** (`firmware/robot`): motorsuz yükle, seri monitörde jiroskop kalibrasyonunu gör (robot kıpırdamasın).
4. **IMU yönü:** robotu öne eğ, telemetride `tilt` artmalı. Azalıyorsa `imu_filter.h > AxisMap` işaretini çevir.
5. **Enkoder:** tekeri 10 tur ileri çevir, `x` ≈ 2,04 m olmalı. Değilse `ENC_COUNTS_PER_REV`.
6. **Motor yönü:** tekerlekler havada, seri porta `mtest` yaz: sol sonra sağ teker 1 s yavaşça **ileri** dönmeli.
7. **Denge noktası:** robotu elle en rahat durduğu açıda tut, `cal` yaz.
8. **İlk deneme:** robotu elle tut, tekerlekler havada. 3° ve altında 0,5 s dik tutunca dengeye girer. Sonra yere koy, hafifçe bırak.
9. **Finalde** `main.cpp` içinde `FREEZE = true` (şartname: finalden sonra parametre değişmez).

**Seri komutlar** (robot yazılımı): `stat` · `mtest` · `task=0..3` · `glove=step|cont` · `cal` · `vscale=1.000`.

---

## 7. Bağlantılar

- **Eldiven → robot:** ESP-NOW, 20 Hz, 12 baytlık paket (anahtar, sürüm, komut, sıra no, CRC-8). Aynı kanal (1), robot MAC'i eldiven yazılımına yazılır.
  Komutlar: ileri, geri, sol, sağ, dur. Adım modu: bir jest = 0,5 m veya 90°.
- **Robot → telefon (takım protokolü, ADR-0003):** robot `CDTP-ROBOT` Wi-Fi ağını açar (şifresiz, `192.168.4.1`),
  WebSocket sunucusu `ws://192.168.4.1:81/`. Telemetri saniyede 5 JSON:
  `{"type":"telemetry","t":..,"seq":..,"tilt":..,"charging":..,"battery":..,"voltage":..,"state":"BALANCING","cmd":"-","docked":false}`.
  `ping` → `pong`, `cmd` (F/B/L/R/S) geliştirme içindir; eldiven önceliklidir.
- **Test:** `python tools/ws_sozlesme_testi.py ws://192.168.4.1:81/` (takım mock robotuna karşı geçti, gerçek robotta henüz denenmedi).

---

## 8. Benzetim ve testler

```bash
bash tools/run_sim.sh      # Git Bash veya Linux, g++ gerekir; birim + 20 kabul testi
python tools/lqr_design.py # model değişince kazançları yeniden üret
```

Güncel sonuç: **20/20 kabul testi geçti, birim testi hatası 0.** Örnekler: 30 s statik denge en büyük eğim 1,09°;
±10°'den toparlanma 1,5 s; eldivenle 90° dönüş 88,8°; belirsizlik testi (kütle ±%25, ağırlık merkezi −%25/+%60) statik 40/40.
Benzetim 60 g ilaç kutusunu da içerir.

Kabul testi kayıtları: takım deposunda `tests/acceptance/C1-balance-and-motion.md` (30 s denge, 1 m ileri/geri, ±10° toparlanma).

---

## 9. Bilinen eksikler ve riskler

1. **Motor testi yapılmadı.** TB6612 `VM` bağlantısı düzeltildi ama hareket doğrulanmadı. Bir ara ESP32 USB gücü kayboldu (geri besleme şüphesi).
2. **Gerçek robotta denge denenmedi.** Kazançlar yalnız benzetimde doğrulandı.
3. **`I_body`, `I_yaw` tahmin.** Sarkaç testiyle ölç. Pil takılıyken yeniden tart.
4. **`ENC_COUNTS_PER_REV` = 836 doğrulanmadı.**
5. **Pil ve şarj ölçüm pinleri (GPIO35/34) breadboardda bağlı değil.** Havada kalan pinler rastgele değer okuyabilir:
   GPIO34'ü 10 kΩ ile GND'ye çek, GPIO35'e 100k/27k bölücü bağla. Aksi halde pil yüzdesi ve "şarj var" algısı yanlış çıkabilir.
6. **Breadboardda sigorta, anahtar ve 1000 µF kondansatör yok.** 12 V hattına sigorta önerilir.
7. **Pasif denge ön testi** (REQ-G-03, motorsuz ±10° bırakma) yapılmadı: `tests/acceptance/00-pretest.md`.
8. **Wi-Fi WebSocket bağlantısı** derlendi ve sözleşme testinden geçti ama robotta ve telefon uygulamasıyla denenmedi.
9. **3D göbek (hub)** yeni 65 mm tekerlek için çizilmedi (`cad/teker_gobek.py` eski tekerlek içindir).
10. Geliştirme bilgisayarının USB portları çalışmıyor; yükleme başka bilgisayardan yapılmalı.

---

## 10. Dosya ve bağlantılar

| Konu | Yer |
|---|---|
| Ölçüler ve model | `docs/OLCULER_VE_DENGE.md` |
| Breadboard şemaları | `docs/breadboard_sema.html`, `docs/breadboard_sema_30pin.html` |
| 38 → 30 pin geçişi | `docs/ESP32_38den_30a_gecis.html` |
| Kalman / LQG çalışması | `docs/KALMAN_FILTRE.md` |
| Eski BLE protokolü (kullanımdan kalktı) | `docs/BLE_PROTOKOL.md` |
| Ana kart PCB v2 (TB6612) | `elektronik/pcb_v2/` (Gerber: `gerber/`) |
| Takımın deposu | https://github.com/Festus26/CDTP-patient-assistance-robot (dal `a/denge-modeli-ve-olculer`) |
| Senin deponun | https://github.com/adakarda/dengerobot |
