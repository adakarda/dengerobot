# ÇDTP iki tekerlekli hasta destek robotu — denge, hareket ve yanaşma

YTÜ EEF ÇDTP 2026-27 Güz. Kontrol bölümünün işi (denge, hareket, istasyona yaklaşma) ve onun dokunduğu her şey:
robot firmware'i, eldiven firmware'i, LQR tasarımı, fizik simülasyonu ve kabul testleri.

Parça listesi ve takımın ortak şeması: <https://cdtp-robot.netlify.app>. Buradaki pinler o şemayla aynıdır;
farklar `docs/` altındaki plan sayfasında "değişiklik önerisi" olarak işaretli.

## Klasörler

| Klasör | İçerik |
|---|---|
| `common/cdtp_core/` | Donanımdan bağımsız çekirdek: mod makinesi, LQR denge, hareket adımları, IR yanaşma, eldiven jesti, paket. **Robot, eldiven ve simülasyon aynı kodu kullanır.** |
| `firmware/robot/` | Robot ESP32 (WROOM-32D): MPU6050, PCNT enkoder/IR, BTS7960, ESP-NOW, Wi-Fi WebSocket |
| `firmware/glove/` | Eldiven ESP32-C3 Super Mini: MPU6050 → 5 komut → ESP-NOW 20 Hz |
| `tools/lqr_design.py` | Fiziksel model + LQR. `gains.h` ve simülasyon modelini üretir |
| `sim/` | Ters sarkaç + motor + sensör gürültüsü + IR istasyon simülasyonu, kabul testleri |
| `twin/` | MuJoCo dijital ikizi: robot firmware mantığı + 3B gövde, V-yuva, direk |
| `cad/` | 3B baskı: `olcu.py` (bütün ölçüler), `robot_cad.py` (STL + montaj denetimi), `stl/` (6 parça), `montaj.glb` |
| `elektronik/` | KiCad 10 projesi: `cdtp_robot.kicad_pro`, şema PDF/SVG, ERC ve netlist; `tools/kicad_sema.py` üretir |
| `docs/` | Robot yapım dosyası, PDF kitap, eski BLE protokolü (yerine WebSocket), grafikler |

## Hızlı başlangıç

```bash
python tools/lqr_design.py        # model değişince kazançları yeniden üret
bash tools/run_sim.sh             # 20 kabul testi + birim testleri (Git Bash / Linux)
python tools/plot_sim.py          # docs/img/*.png
python cad/robot_cad.py           # 3B parçalar + montaj denetimi (pip install manifold3d trimesh)
python tools/kicad_sema.py        # KiCad şeması + ERC + pins.h karşılaştırması (KiCad 10 gerekir)
python tools/check_consistency.py # belge, kod, 3B model ve şema tutarlılığı
```

Firmware: VS Code + PlatformIO eklentisi → `firmware/robot` (ya da `firmware/glove`) klasörünü açın → Upload.
Kod yüklerken robotta **JP1 köprüsünü çıkarın**, eldivende **SW1'i kapatın**.

## İlk çalıştırma sırası (robot)

1. **Motorsuz:** EN kablosu takılı değilken yükleyin. Seri monitörde (115200) jiroskop kalibrasyonu ve
   `Robot MAC` satırını görün. MAC'i `firmware/glove/src/main.cpp` içindeki `ROBOT_MAC`'e yazın.
2. **IMU yönü:** robotu elle öne eğin → telemetride `tilt` artmalı. Azalıyorsa `imu_filter.h > AxisMap`
   işaretlerini çevirin. Sola döndürün → `yaw` artmalı.
3. **Enkoder:** tekeri elle 10 tur ileri çevirin → `x` ≈ 2,04 m. Değilse `ENC_COUNTS_PER_REV`; yön tersse
   `ENC_*_INVERT`.
4. **Motor yönü:** robotu tekerler havada kalacak şekilde destekleyin, seri porta `mtest` yazın: önce sol, sonra
   sağ teker 1'er saniye yavaşça **ileri** dönmeli. Ters dönen için `MOTOR_*_INVERT`.
5. **Model:** gövdeyi tartın, kütle merkezini (ip ile asarak) bulun → `tools/lqr_design.py` `P` sözlüğü →
   yeniden çalıştırın → simülasyon testlerinin hâlâ geçtiğini görün → yükleyin.
6. **Denge noktası:** robotu elle en rahat durduğu açıda tutun, seri porta `cal` yazın.
7. Tamamen bitince `main.cpp` içinde `FREEZE = true` (finalde parametre değiştirilemez).

## Seri komutlar

`stat` · `mtest` · `task=0..3` · `glove=step|cont` · `cal` · `vscale=1.000`
