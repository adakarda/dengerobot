# Elektrikci / Montajci Rehberi - Denge Robotu

> Bu dosya, elektronikten anlamayan birinin (veya onun yapay zekasinin) **ne alacagini** ve **ne yapacagini** anlamasi icin yazildi.
> Kaynaklar: `docs/kitap.html` (parca tablosu), `docs/parca_listesi.html` (fiyat/stok, 3 Kasim 2026), `docs/breadboard_sema.html` (kablolama), `elektronik/pcb_v2/URETIM.md` (PCB).
> **Fiyatlar ve stok eskidir. Satin almadan once urun sayfasindan tekrar kontrol et.**

## 0. Robot nedir
Iki tekerlekli, kendi kendine dengede duran robot (ters sarkac). ESP32 beyin, MPU6050 egim sensoru, iki enkoderli 12 V DC motor, TB6612 motor surucu, 3S Li-ion pil. Denge kodu ESP32'de 200 Hz calisir.
Kapsam yalniz **denge**. Sarj istasyonu, IR goz, ilac kutusu, eldiven baska kisilerin isi.

## 1. Durum - NELER DOGRULANDI, NELER DOGRULANMADI
| Konu | Durum |
|---|---|
| Kod derleniyor, simulasyonda 20/20 test geciyor | Dogrulandi |
| Breadboard semasi (43 kablo) otomatik denetimden geciyor | Dogrulandi (yazilim ile) |
| Motorlar donuyor mu, yon dogru mu | **Denenmedi** |
| Gercek robotta denge | **Denenmedi** |
| Telefon uygulamasi ile Wi-Fi baglantisi | **Denenmedi** (sahte robotla test edildi) |
| Ataletler (I_body, I_yaw) | Tahmin, olculmedi |
| Pil agirligi dahil kutle | Olculmedi |
| Breadboard'da sigorta, anahtar, kondansator | **Yok**, eklenmeli |
| GPIO34 / GPIO35 (sarj / pil olcumu) | Breadboard'da bagli degil, havada |
| PCB v2 (Gerber) | Siparis edilmedi; varsayimlar once olculmeli (bkz. 6) |

## 2. Alinacaklar listesi (denge robotu, eklentiler haric)
Adet = bir robot icin. Fiyat TL, KDV dahil, 9-10 Ekim / 3 Kasim 2026 tarihli, **tahmindir**.

### 2.1 Beyin ve sensor
| Parca | Adet | Onemli sart |
|---|---|---|
| ESP32 DevKit (WROOM-32D, 38 pin **veya** 30 pin) | 1 | **WROVER, S3, C3 ALMA**: GPIO16/17 baska ise gider. USB cipi CH340 veya CP2102 olabilir |
| MPU6050 GY-521 modulu | 1 | 3-5 V, I2C adresi 0x68 (AD0 GND) |

### 2.2 Hareket
| Parca | Adet | Onemli sart |
|---|---|---|
| JGB37-520 12 V 530 RPM Hall enkoderli DC motor | 2 | 6 mm D mil, dişli 1:19, enkoder 11 darbe/tur. Durma akimi 2,3 A/motor |
| TB6612FNG motor surucu modulu | 1 | **Breadboard ve PCB v2 icin bu**. (Eski listedeki BTS7960 x2 eski tasarimdir) |
| Tekerlek 65-70 mm + 6 mm mil adaptoru (Pololu PL2674 tipi) | 2 | Kodda yaricap 32,5 mm (65 mm) kabul edildi; baska boyut alirsan haber ver |
| 3B baskili motor tutucu, katlar | - | PLA/PETG, STL `cad/stl/` icinde |

### 2.3 Guc
| Parca | Adet | Onemli sart |
|---|---|---|
| Orion 18650P 2450 mAh 12C hucre | 3 | Ucu **ayni partiden**, 3S1P. Tahmini calisma suresi ~1,5-2 saat (olculmedi) |
| 18650 3'lu pil yuvasi (ici seri) | 1 | |
| 3S 10 A BMS (HX-3S-01) | 1 | Zorunlu |
| LM2596 5 V 3 A regulator (ayarli) | 1 | **Once 5,0 V'a ayarla**, sonra ESP32'ye bagla |
| Bicak sigorta yuvasi + 5 A sigorta (yedek 7,5 A) | 1 | Zorunlu. Iki motor kilitlenirse ~4,6 A, 5 A sinirda |
| Acil stop Chint NP2-BE102 (NC, 10 A) | 1 | Zorunlu, 22 mm delik |
| Ana anahtar (en az 5 A) | 1 | Breadboard asamasi icin |
| 1000 uF 25 V dusuk ESR elektrolitik kondansator | 1 | Motor hatti, kutba dikkat |
| XT60 konnektor takimi | 2 | |
| WAGO 221-415 | 2 | 12 V ve GND dagitimi |
| 18 AWG silikon kablo kirmizi/siyah | 2+2 m | Guc hatti |
| 12 V >=3 A adaptor (masa testi icin) | 1 | Pilden once bununla dene |

### 2.4 Breadboard / baglanti
| Parca | Adet |
|---|---|
| 830 delikli breadboard (63 sutun, 4 ray) | 1 |
| Jumper kablo erkek-erkek (breadboard icin) ve dişi-dişi | ~60 |
| 2 pin / 3 pin vidali klemens (breadboard tipi, 5,08 mm) | 2-3 |
| 10 kohm direnc (STBY cekme) | 1 |
| 100 nF seramik, 100 uF 16 V | 3 + 1 |
| Direnc 100k x3, 27k x2, 33k, 10k (pil olcum bolucusu, PCB icin) | 1 set |

### 2.5 Sarf ve gövde
PLA/PETG ~0,25 kg, M3 distans 30 mm ve 50 mm (8+8), M3 vida, naylon distans, 5x10 cm delikli plaket (PCB yerine).

## 3. Yapilacak isler, sirasiyla
1. **Masada, pilsiz, motorsuz**: adaptor 12 V'u LM2596'ya ver, cikisi multimetre ile **5,0 V** ayarla. Sonra cikisi bagla.
2. Breadboard'u `docs/breadboard_sema.html` (38 pin) veya `docs/breadboard_sema_30pin.html` (30 pin) semasina gore kur. Tum kablo numaralari ve satir/sutunlar orada. Raylar: ust dis = +12 V, ust ic = GND, alt ic = GND, alt dis = +3,3 V. GND koprusu sutun 22.
3. **Kablo 7'yi (12 V motor beslemesi) en son tak.** Once her hatti multimetre ile **sureklilik (bip)** olarak kontrol et; +12 V ile GND arasinda bip olmamali.
4. ESP32'ye USB **veya** LM2596 5 V ver, ikisini **ayni anda verme**.
5. Kodu yukle (PlatformIO, `firmware/robot`). Yukleme basarisiz olursa BOOT tusunu basili tut.
6. **Motor testi**: tekerlekleri havada tut, dusuk PWM ile her motoru iki yone surdur, yon ve enkoder isaretini kontrol et (bkz. `docs/DENGE_KODU_REHBERI.md`).
7. Sonra sigorta, anahtar, kondansator ve pili ekle; robotu iple veya askidan emniyete alarak ilk denemeyi yap.

## 4. Lehim gereken yerler
- Motor kablolari konnektore (veya klemense)
- Pil yuvasi / BMS / XT60 baglantilari
- PCB siparis edilirse tum THT parcalar (soket, klemens, sigorta, kondansator, direnc)

Breadboard asamasi lehim gerektirmez.

## 5. Pin atamasi (ozet)
ESP32: AIN1=27, AIN2=14, BIN1=16, BIN2=17, STBY=4 (10 kohm GND'ye); enkoder sol A32/B33, sag A25/B26; MPU SDA21, SCL22, INT19; IR sol 36, sag 39. TB6612: PWMA/PWMB/VCC 3,3 V, VM 12 V.

## 6. PCB varsa (elektronik/pcb_v2)
130 x 80 mm, 2 katman, 1,6 mm, THT. Siparis: HASL, min 5 adet. Dosya: `gerber/CDTP_ana_kart_v2_gerber.zip`.
**Siparisten once olc**: ESP32 iki sira arasi 25,4 mm mi, TB6612 modulu sira araligi 15,24 mm mi, LM2596 ped araligi, motor konnektoru 6 pin (M1 GND C1 C2 VCC M2) sirasi. Bilinen hata: J3/J4 pin sirasinda C1/C2 yer degistirmis olabilir, duzeltilmedi.

## 7. Guvenlik
- 3S Li-ion 12,6 V tam dolu. Kisa devre yangin cikarir; sigorta ve BMS olmadan pil baglama.
- Kondansator ve pil kutuplarina dikkat.
- Robot dengede dusebilir; ilk denemelerde tekerlekleri havada tut.
- Acil stop kolay ulasilir olmali.

## 8. Eksikler ve bilinen riskler
- Motor ve denge testleri yapilmadi, kazanclar (LQR) simulasyon degerleri.
- 65 mm tekerlek icin hub CAD'i eksik.
- ENC_COUNTS_PER_REV = 836 hesaplandi, gercekte dogrulanmadi.
- TB6612 durma akimi (2,3 A) icin sinirda; uzun kilitlenmede isinir.
- Bilgisayar USB portlari arizali oldugundan kod henüz karta yuklenmedi.

## 9. Yapay zeka icin ipucu
Bu dosyayi, `docs/breadboard_sema.html` ve `docs/DENGE_KODU_REHBERI.md` ile birlikte ver. "Alisveris listesi cikar", "sirayla kablolama adimlarini ver", "multimetre testlerini yaz" gibi isteklerde bu dosyadaki bolum 2, 3 ve 7 temel alinmali. Fiyatlari ve stogu guncel olarak yeniden kontrol ettir.
