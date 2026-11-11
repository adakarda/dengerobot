# Gerçek robot ölçüleri ve dengede kalma (2026-11-11)

Bu belge, gerçek robotun ölçülen değerlerini, modele nasıl işlendiğini ve denge kazançlarının nasıl yeniden
hesaplandığını anlatır. Ölçümler elle yapıldı, tahmin olanlar ayrıca işaretli.

## 1. Ölçülen değerler

| Büyüklük | Değer | Nasıl ölçüldü |
|---|---|---|
| Toplam kütle (tekerlekler takılı) | 1225 g | Terazi, her şey takılıyken |
| Tekerlek + kaplin (tek) | 53 g | Terazi |
| Tekerlek çapı / genişliği | 65 mm / 28 mm | Kumpas (küçük arazi tekerleği) |
| **Gövde kütlesi** | **1,119 kg** | 1225 g - 2 x 53 g |
| Ağırlık merkezi (zeminden) | 120 mm | Yandan bakış, yukarıdan 10x20 cm plakanın ortasında |
| **Ağırlık merkezi (teker ekseninden)** | **87,5 mm** | 120 mm - teker yarıçapı 32,5 mm |
| Tekerlekler arası (dıştan dışa) | 298 mm | Cetvel |
| **İz genişliği (teker orta çizgileri)** | **270 mm** | 298 mm - 28 mm |

Pil veya adaptör 1225 g'a dahil mi, doğrulanmadı. Pil takılınca yeniden tartıp `tools/lqr_design.py` içindeki
`m_body` değerini güncelleyin.

## 2. Tahmin olan değerler (ölçülmeli)

| Büyüklük | Kullanılan | Dayanak |
|---|---|---|
| Gövde yunuslama ataleti `I_body` | 0,0066 kg m^2 | Eski 0,00737 değerini kütle oranıyla (1,119/1,245) ölçekledik |
| Gövde dönme (yaw) ataleti `I_yaw` | 0,0066 kg m^2 | 10x20 cm plaka m(L^2+W^2)/12 + 2 tekerlek |

Ölçmek için robotu ince bir telden asıp 10 salınımın süresini ölçün (sarkaç testi), sonra
`tools/lqr_design.py` içindeki bu iki değeri güncelleyip betiği yeniden çalıştırın.

## 3. Hangi dosyalar değişti

| Dosya | Değişiklik |
|---|---|
| `tools/lqr_design.py` | `m_body`, `l_com`, `I_body`, `m_wheel`, `r`, `track`, `I_yaw` gerçek değerlerle |
| `common/cdtp_core/src/cdtp_config.h` | `WHEEL_RADIUS_M` 0,0325 ve `TRACK_WIDTH_M` 0,270 |
| `common/cdtp_core/src/gains.h` | Betikle yeniden üretildi (LQR, yaw, gözleyici) |
| `sim/plant_nominal.h` | Betikle yeniden üretildi (benzetimin nominal modeli) |
| `twin/twin.py` | `R_WHEEL`, `TRACK` |

## 4. Kazançlar (eski -> yeni)

| Kazanç | Eski | Yeni |
|---|---|---|
| K_X | -54,19 | -50,53 |
| K_V | -66,49 | -62,57 |
| K_TH | -108,21 | -107,94 |
| K_OM | -13,46 | -13,48 |
| YAW_KP | 2,947 | 1,059 |
| YAW_KD | 0,663 | 0,238 |

Eğim kazançları az değişti (ağırlık merkezi yükseldi, kütle azaldı). Dönüş kazançları belirgin düştü: iz genişliği
190 mm'den 270 mm'ye çıktı, dönüş ataleti de küçüldü.

## 5. Benzetim sonucu

`bash tools/run_sim.sh` ile birim testleri ve kabul testleri çalıştırıldı: **20/20 kabul testi geçti, birim testi
hatası 0.** Örnekler: 30 s statik denge en büyük eğim 1,09 derece; +-10 derece'den toparlanma 1,5 s; eldivenle 90
derece dönüş 88,8 derece; belirsizlik testi (kütle +-25%, ağırlık merkezi -25/+60%) statik 40/40.

Benzetim ilaç kutusunu da ekler (60 g). Robotta kutu yoksa sonuçlar biraz daha iyi çıkar.

## 6. Robota yüklemeden önce

- Firmware'deki `ENC_COUNTS_PER_REV` (836) gerçek motor için doğrulanmadı. Tekerleği 10 tur çevirip sayımı okuyun
  (`firmware/bench` test yazılımının `p` komutu).
- Motor ve enkoder yönleri (`MOTOR_*_INVERT`, `ENC_*_INVERT`) robot üzerinde denenmeli.
- İlk denemede robotu elle dik tutun, tekerlekler havada olsun. Kazançlar benzetimde doğrulandı, gerçek robotta henüz
  denenmedi.

## 7. Donanım test yazılımı

`firmware/bench` denge kodu içermeyen bir donanım testidir (I2C tarama, MPU6050, enkoder ve IR sayacı, düşük güçle
motor testi). Seri komutlar: `?`, `i`, `m`, `p`, `l 0.3`, `r 0.3`, `b 0.3`, `s`. Derleme:
`pio run -d firmware/bench`. Yükleme için ESP32'yi BOOT düğmesine basarak yükleme moduna alın.
Test sonucu: MPU6050 0x68'de bulundu, iki enkoder elle çevrilince sayıyor. Motor testi TB6612 VM bağlantısı
düzeltilince yeniden denenecek.
