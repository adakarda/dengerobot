# Eğim kestirimi: tümleyen filtre ve Kalman (açı + jiroskop bias)

Tarih: 2026-11-09. Bütün sayılar simülasyondan; gerçek robotta henüz denenmedi.

## Ne eklendi

- `common/cdtp_core/src/imu_filter.h` → `TiltKalman`: 2 durumlu Kalman, durum `[θ, b]`, `b` jiroskopta kalan bias (rad/s).
  - Tahmin: `θ += (ω − b)·dt`.
  - Ölçüm: ivmeölçerden açı, `H = [1, 0]`.
  - İvme büyüklüğü 1 g'den 2 m/s²'den fazla saparsa `R` büyür. Bu, tümleyen filtredeki güven azaltmanın aynı fikri.
  - `pitchRate()` bias'ı çıkarılmış hızı verir. LQR'ın ω girdisi de düzelir.
  - Yapı: Lauszus 2012, TKJ Electronics, "A practical approach to Kalman filter and how to implement it".
- Seçim derlemede yapılır: `-DCDTP_TILT_KALMAN=1`. Varsayılan (0) tümleyen filtredir. Firmware değişmedi.
- Ayar değerleri `cdtp_config.h` içinde `KF_*`.
- `sim/filtre_karsilastir.cpp` + `tools/run_filtre.sh`: iki filtreyi aynı IMU örnekleri üzerinde karşılaştırır.
  - Robotlar SAG testinin aynı 40 rastgele robotu: kütle, kütle merkezi, IMU montaj hatası ±1.5°, jiro bias ±0.5 °/s.
  - Ayar için 0–19, sınama için 20–39 kullanıldı.
  - Senaryo: 30 s; 5 s bekleme ve beş adım komutu.
  - Gerçek değer, IMU'nun eğimi: `plant.th` + montaj hatası.
- `tools/run_sim.sh`: `KALMAN=1 bash tools/run_sim.sh` 20 kabul testini Kalman ile koşar.

## Sonuç 1: kestirim hatası (açık döngü, sınama robotları 20–39)

| Filtre | RMS ort | RMS en kötü | Anlık en kötü | RMS hareket sırasında | Bias hatası ort / en kötü |
|---|---|---|---|---|---|
| Tümleyen, α = 0.98 (bugünkü) | 0.865° | 0.982° | 2.70° | 1.11° | kestirmez |
| Tümleyen, en iyi α = 0.995 | 0.574° | 0.684° | 1.55° | 0.66° | kestirmez |
| **Kalman, config değerleri** | **0.265°** | **0.477°** | 1.68° | **0.34°** | 0.002 / 0.006 °/s |

- Bu tablo, kapalı döngü Kalman ile koşan robotlardan alındı (`KALMAN=1 bash tools/run_filtre.sh`).
- Kapalı döngü tümleyen filtreyle koşunca da sıra aynı: 1.11° / 0.59° / 0.25°.
- Karşılaştırma adil olsun diye tümleyen filtrenin α değeri de aynı eğitim robotlarında ayarlandı.
- Ayarlı tümleyen filtreye göre RMS hatası yaklaşık **2.2 kat** küçük. Fark, Kalman'ın bias'ı kestirmesinden geliyor.

## Sonuç 2: kapalı döngü, 20 kabul testi

| Test | Tümleyen | Kalman |
|---|---|---|
| Hepsi | 20/20 | 20/20 |
| C1.1 statik: en büyük eğim / kayma | 0.68° / 1.3 cm | **0.10° / 0.4 cm** |
| C1.2 1 m ileri: duruşta kayma, hız tepesi | 8.9 mm, 0.039 m/s | **7.1 mm, 0.016 m/s** |
| C2.5 son 3 s kayma | 8.8 mm | **0.6 mm** |
| SAG: ±3 cm durma | 37/40 | **40/40** |
| C1.4 ±10°'den toparlanma | **1.44 s** | 2.22 / 2.11 s |

C1.4'teki yavaşlama testin kendisinden geliyor, gerçek bir kötüleşme değil:
- Test robotun açısını bir anda 10° değiştiriyor (`plant.th = ...`). Jiroskop bu sıçramayı görmüyor.
- Kalman ivmeölçere az güvendiği için yeni açıyı daha geç kabul ediyor.
- Gerçekte robot elle itilir. İtme sırasında jiroskop dönüşü görür.
- Bu yüzden C1.4, Kalman'ı haksız yere cezalandırıyor. Robotu itilerek eğilen bir test eklemek daha doğru olur.

## Ayar

- `filtre_izgara.tsv`, 168 nokta: q_θ 1e-8…1e-7, r_acc 0.0016…0.025 ve q_b 1e-13…1e-9 aralığı düz bir plato. RMS hep ≈ 0.25°.
- Seçilen değerler platonun ortası: `q_θ = 1e-7`, `r_acc = 6.4e-3`, `q_b = 1e-9`.
  - q_b platonun üst ucunda. Gerçek MPU6050'nin bias'ı sıcaklıkla kayar; filtre bunu izleyebilmeli.
- Fiziksel kontrol: simülasyonda jiro gürültüsü 0.05 °/s. Buna göre `σ²·dt ≈ 4e-9 rad²/s`, platonun altıyla tutarlı.
  - r_acc ≈ (4.6°)². Titreşim ve hareket ivmesi ivmeölçer açısını bu kadar bozuyor.

## Sınırlar ve sonraki adım

- Simülasyondaki bias sabit. Gerçek sensörde bias sıcaklıkla kayar ve gürültü dağılımı farklıdır.
- Gerçek robotta doğrulamak için:
  1. MPU6050 verisini kaydet.
  2. İki filtreyi aynı veride çevrimdışı koş (yol haritasında D3).
  3. Sonra firmware'de `build_flags`'e `-DCDTP_TILT_KALMAN=1` ekle.
- Sonraki iş: tüm durumu `[x, v, θ, ω]` tek bir durağan Kalman ile kestirmek (LQG, yol haritasında D2). Girdiler enkoder ve IMU.

---

# Durum gözleyicisi (LQG): olumsuz sonuç

Tarih: 2026-11-09. Yol haritasında D2. Simülasyon; varsayılan kapalı (`CDTP_LQG=0`), firmware değişmedi.

## Ne denendi

- `common/cdtp_core/src/state_observer.h`: durağan Kalman gözleyicisi.
  - Durum `[x, v, θ, ω, d]`. d, girişe eklenen yavaş bir bozucu gerilim (V).
  - Ölçümler: x (enkoder), θ (eğim filtresi), ω (jiroskop).
  - Model: `lqr_design.py`'deki ayrık nominal model. Kazanç L çevrimdışı hesaplanıyor (`solve_discrete_are`, dual problem) ve `gains.h`'a yazılıyor.
  - Ayrılma ilkesi gereği LQR K değişmedi.
- d neden eklendi: d olmadan gözleyici, nominal robotta bile enkoder farkından kötüydü (v RMS 5.6 mm/s, enkoder farkı 4.1). Nominal modelde ilaç kutusu (60 g, eksenden 21 cm yukarıda) ve Coulomb sürtünmesi yok.
- Seçim: `LQG=1 bash tools/run_sim.sh` (v, θ, ω gözleyiciden) veya `LQG=2` (yalnız v gözleyiciden).
- Ayar: `sim/gozleyici_karsilastir.cpp` + `tools/run_gozleyici.sh`.
  - Izgara 288 nokta: σ_a, σ_α, σ_d, r_x, r_θ.
  - Ayar için robot 0–19, sınama için 20–39.
  - Seçilen değerler: σ_a 4, σ_α 80, σ_d 4, r_x 2 mm, r_θ 0.1°.
- Denenen ama işe yaramayan iki şey:
  - Ölü bölge telafisini girişe katmak: daha kötü (v 9.5 mm/s).
  - Hızlı gözleyiciler (LTR yönünde, σ_a 16–64): kapalı döngüde 6–11/20.

## Sonuç: açık döngü kestirim (sınama robotları, Kalman eğim filtresiyle)

| Kestirim | v RMS ort / en kötü | θ RMS | ω RMS |
|---|---|---|---|
| Enkoder farkı (4 örnek, 20 ms) | **4.58 / 7.81 mm/s** | 0.265° | 2.89 °/s |
| Gözleyici, ızgaranın en iyisi | 5.20 / 7.83 mm/s | 0.265° | 2.89 °/s |
| Gözleyici, nominal robotlarda | 4.72 mm/s (enkoder farkı 4.14) | 0.239° | 2.50 °/s |

## Sonuç: kapalı döngü (20 kabul testi)

| Yapılandırma | Geçen |
|---|---|
| Kalman eğim filtresi, gözleyici yok | **20/20** |
| Kalman eğim filtresi + LQG=1 | 13/20 (statik eğim 7°, SAG statik 6/40) |
| Kalman eğim filtresi + LQG=2 (yalnız v) | 13/20 |
| Tümleyen filtre + LQG=1 | 5/20 |

## Neden

- Enkoder çözünürlüğü yüksek: 0.26 mm/sayım, 200 Hz. 20 ms'lik fark gürültüsü ile gecikmesi iyi bir noktada. Model tabanlı tahminin ekleyeceği bilgi az.
- Nominal model gerçek robottan uzak: kütle ±%25, kütle merkezi −%25/+%60, kutu, sürtünme. Gözleyici bu hatayı kestirime taşıyor.
- Kapalı döngüde iki seçenek var, ikisi de kötü:
  - Yavaş gözleyici gecikme ekliyor ve K_V = −66'lık hız kazancıyla birleşince kararlılık payını yiyor.
  - Hızlı gözleyici gürültülü v veriyor; bu gürültü motor gerilimine geçiyor.
- Bu, LQG'nin bilinen zayıflığı: LQR'ın garanti ettiği kararlılık payları, araya Kalman gözleyicisi girince geçerli olmaz. Kaynak: Doyle, J.C., "Guaranteed margins for LQG regulators", IEEE Trans. Automatic Control 23(4), 1978.

## Ne öğrenildi, sonraki adım

- D1'deki eğim Kalman'ı işe yaradı, çünkü ölçülemeyen bir şeyi (jiroskop bias'ı) kestiriyor. Bu gözleyici ise zaten iyi ölçülen bir şeyi (v) modelden yeniden kestirmeye çalışıyor.
- Denenebilecekler:
  - Döngü transferi geri kazanımı (LTR, Doyle–Stein 1979), kazanç payı ölçülerek.
  - Gözleyiciyi yalnız d kestirmek için kullanıp d'yi LQR girişinden çıkarmak (bozucu kompanzasyonu). Şu an kodda bunu `thTrim_` elle yapıyor.
