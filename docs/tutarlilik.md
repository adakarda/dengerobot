# Belge ve kod tutarlilik denetimi

50 kontrol, 0 uyumsuz.

| Konu | Beklenen | Bulunan | Durum |
|---|---|---|---|
| Site semasi: SDA | [21] | [21] | uygun |
| Site semasi: SCL | [22] | [22] | uygun |
| Site semasi: INT | [19] | [19] | uygun |
| Site semasi: OUT | [36, 39] | [36, 39] | uygun |
| Site semasi: RPWM | [27, 16] | [27, 16] | uygun |
| Site semasi: LPWM | [14, 17] | [14, 17] | uygun |
| Site semasi: R_EN + L_EN | [4, 4] | [4, 4] | uygun |
| Site semasi: C1 (A) | [32, 25] | [32, 25] | uygun |
| Site semasi: C2 (B) | [33, 26] | [33, 26] | uygun |
| Site semasi: pil olcumu | 35 | 35 | uygun |
| Site semasi: sarj algilama | 34 | 34 | uygun |
| Belge pin tablosu: MPU6050 INT | [19] | [19] | uygun |
| Belge pin tablosu: I2C SDA / SCL | [21, 22] | [21, 22] | uygun |
| Belge pin tablosu: Sol / sağ RPWM, LPWM | [27, 14, 16, 17] | [27, 14, 16, 17] | uygun |
| Belge pin tablosu: EN (iki kart) | [4] | [4] | uygun |
| Belge pin tablosu: Enkoder A, B | [32, 33, 25, 26] | [32, 33, 25, 26] | uygun |
| Belge pin tablosu: IR göz sol / sağ | [36, 39] | [36, 39] | uygun |
| Belge pin tablosu: Pil / şarj pimi gerilimi | [35, 34] | [35, 34] | uygun |
| Belge pin tablosu: Acil stop sonrası motor hattı | [23] | [23] | uygun |
| Belge pin tablosu: Karttaki LED | [2] | [2] | uygun |
| Ana kart J2 pin sirasi | 3V3, GND, G22, G21, G19 | 3V3, GND, G22, G21, G19 | uygun |
| Ana kart J3 pin sirasi | G27, G14, G4, 3V3, GND | G27, G14, G4, 3V3, GND | uygun |
| Ana kart J8 pin sirasi | G16, G17, G4, 3V3, GND | G16, G17, G4, 3V3, GND | uygun |
| Ana kart J4 pin sirasi | 3V3, GND, G32, G33 | 3V3, GND, G32, G33 | uygun |
| Ana kart J5 pin sirasi | 3V3, GND, G25, G26 | 3V3, GND, G25, G26 | uygun |
| Ana kart J6/J7 | [36, 39] | [36, 39] | uygun |
| Iz genisligi (kod <-> belge 190 mm) | 190 | 190 | uygun |
| Enkoder sayim/tur (kod <-> belge 836) | 836 | 836 | uygun |
| Dusme acisi 40 deg | 40 | 40 | uygun |
| Dengeye girme +-3 deg, 0,5 s | 3 / 0.5 | 3 / 0.5 | uygun |
| Eldiven zaman asimi 0,3 s | 0.3 | 0.3 | uygun |
| Adim 0,5 m / 90 deg | 0.5 / 90 | 0.5 / 90 | uygun |
| Sarj algilama esigi 9 V | 9 | 9.0 | uygun |
| Butunlesik gorevde bos bekleme 6 s | 6 | 6.0 | uygun |
| LQR kazanclari (gains.h <-> plan sayfasi) | u = 54,2·x + 66,5·v + 108,2·θ + 13,5·ω | plan sayfasinda var | uygun |
| BLE CDTP_SVC_UUID | 6e400001-cd7b-4e3a-9a40-2026cd7b0001 | belgede var | uygun |
| BLE CDTP_TELEM_UUID | 6e400002-cd7b-4e3a-9a40-2026cd7b0001 | belgede var | uygun |
| BLE CDTP_CMD_UUID | 6e400003-cd7b-4e3a-9a40-2026cd7b0001 | belgede var | uygun |
| Pil boluculeri 100k/27k | 100/27 | 100/27 | uygun |
| 12,6 V -> ADC gerilimi < 3,1 V | < 3.1 | 2.68 | uygun |
| Motor hatti bolucu 100k/33k -> < 3,3 V | < 3.3 | 3.13 | uygun |
| Kutle merkezi (mass_budget <-> robot dosyasi) | 70 mm | belgede var | uygun |
| 3B montaj denetimi (cad/kontrol.md) | hepsi gecti | 10 gecti, 0 kaldi | uygun |
| KiCad sema denetimi (sema_kontrol.md) | hepsi gecti | 5 gecti, 0 kaldi | uygun |
| Iz genisligi (cad/olcu.py <-> cdtp_config.h) | 0.19 | 0.19 | uygun |
| KiCad R1 = 100k | 100k | semada var | uygun |
| KiCad R2 = 27k | 27k | semada var | uygun |
| KiCad R6 = 100k | 100k | semada var | uygun |
| KiCad R7 = 33k | 33k | semada var | uygun |
| KiCad F1 = 5 A | 5 A | semada var | uygun |
