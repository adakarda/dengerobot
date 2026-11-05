# Tekerlek surucu gobegi (3B baski) - Pololu 3272, JGB37-520 6 mm D mil

Dosyalar (cad/stl/): teker_gobek_A.stl (2 adet), teker_kapak_B.stl (2 adet), teker_olcu_testi.stl (1 adet, once bunu basin).
Uretici: python cad/teker_gobek.py   (olculer dosyanin basinda)

## Once olcu testi
teker_olcu_testi.stl: dort tapa diski (21.6 / 21.8 / 22.0 / 22.2 mm) ve dort burun diski (14 / 15 / 15.6 / 16 mm).
Tapa: tekerlek rulman yuvasina eli ile hafif zorlanarak giren EN BUYUK diski secin.
Burun: iki yuva arasindaki ic kenar deligine sigan en buyuk disk. Secimi yazin / cad/teker_gobek.py icinde
SEAT_D, LIP_D degerlerini degistirip betigi yeniden calistirin. (Varsayilan: yuva 22.0, derinlik 7.0, ic kenar deligi 16.0 = TAHMIN)

## Baski
PETG, 0.2 mm katman, 5 duvar (en az 3 mm), %60 dolgu. A: mil ucu asagi, kenarlar destek gerektirmez. B: duz yuz asagi.
## Montaj (her tekerlek icin)
1. 3 adet M3 somunu A'daki tapa yuvalarina yan taraftan itin (kenardan acik yuva).
2. A'yi motor tarafindan yuvaya, burnu ic kenar deligine gecirin.
3. B'yi diger yuvaya takin. 3 adet M3 x 20 mm yuvarlak bas vida B'den girip somunlara sikilir (esit sikin).
4. Gobegi motor miline itin (mil duz yuzu +X yonunde = sabitleme vidasi tarafi), M3 x 6 set vidayi sikin (vida kilit yapistirici onerilir).
5. Tekerlek ic yuzu ile motor yuzu arasinda yaklasik 1 mm bosluk kalmali.
Malzeme: 6 adet M3 x 20, 6 adet M3 somun, 2 adet M3 x 6 set vida, 2 adet M3 somun (set vida cebi).
## Sinirlar
Tork sadece iki tapanin tekerlege sikisma surtunmesi ile iletilir; pololu aluminyum adaptor kadar saglam degildir.
Kayma olursa tapalara 3 M3 vida ile cift tarafli teker yan yuzune baglayin ya da tutkal kullanin.
