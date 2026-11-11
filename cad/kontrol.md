# 3B montaj kontrolu

`python cad/robot_cad.py` uretir.

| Kontrol | Sonuc | Ayrinti |
|---|---|---|
| Carpisma (tum parcalar ikili) | GECTI | 38 parca, 703 cift; hic biri birbirine girmiyor |
| Zemin payi (+-30 derece egim) | GECTI | en alcak nokta zeminden 4.0 mm (braket sol) |
| Direk yanasmasi (O40, seride temas) | GECTI | yalniz pogo pimler direge giriyor (yay payi 3 mm) |
| V kanatlari direge degmiyor | GECTI | kanat ic yuzu ile direk arasi 1.2 mm |
| Pim, miknatis ve goz yukseklikleri | GECTI | + pim 102.0, - pim 77.0, miknatis 89.5 (celik serit 85-94), IR goz 147.0 mm (zeminden) |
| IR gorus hatti | GECTI | iki gozun onu 25 cm acik |
| MPU6050 teker ekseni ustunde, ortada | GECTI | x=0, y=0 mm, z=27 mm |
| Kutle butcesi 3B modelle uyumlu | GECTI | en buyuk fark 6.0 mm (2x BTS7960: dz +0, MPU6050 (kat 1 ustu, ortada): dz +0, 3x18650 + yuva + BMS: dz +0, Ana kart + ESP32: dz -1, Kat 3 baski: dz +0, Ilac kutusu: dz +0, Acil stop: dz +0, Kutu yuvasi: dz +0) |
| Kutle merkezi teker ekseni ustunde (x) | GECTI | x = -0.1 mm (one +); robot dik dururken dengede |
| Baski tablasina sigma (180x180) | GECTI | hepsi sigiyor |

| Parca | Boyut (mm, baski yonu) | Hacim cm3 | Kutle g (%60 dolu PLA) |
|---|---|---|---|
| kat1 | 110.0 x 150.0 x 12.0 | 67.7 | 50 |
| kat2 | 110.0 x 150.0 x 18.0 | 67.1 | 50 |
| kat3 | 110.0 x 150.0 x 29.0 | 77.4 | 58 |
| v_yuva | 47.7 x 83.6 x 80.0 | 36.5 | 27 |
