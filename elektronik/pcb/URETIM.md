# CDTP ana kart - uretim notlari

Dosyalar (hepsi ASCII): gerber/CDTP_ana_kart_gerber.zip (Gerber + Excellon delik, duz zip).
Onizleme: onizleme_ust.png, onizleme_alt.png (alt yuz aynalanmis).

## Kart ozellikleri
- Boyut: 100 x 50 mm, kose yaricapi 3 mm, 4 adet M3 montaj deligi (3.2 mm, kaplamasiz) 94 x 44 mm aralikla
- Katman: 2, kalinlik 1.6 mm, bakir 1 oz (35 um)
- Yuzey: HASL kursunsuz (lead-free), maske yesil, serigrafi beyaz
- Kullanilan en kucuk iz: 0.30 mm, en kucuk bosluk (kural): 0.25 mm (12 V aglari: 0.50 mm, bkz. asagi)
- En kucuk delik: 0.80 mm. Halka (annular ring): via 1.45/0.8 -> 0.325 mm; 1.7 mm pedli 1.0 mm delik (header/soket/JP1) -> 0.35 mm; 1.6 mm pedli 0.8 mm delik (direnc, kondansator) -> 0.40 mm; klemens 2.6/1.3 -> 0.65 mm
- Delikler: 0.8 mm -> 58 via + 22 pad (R1-R7, C1-C4); 1.0 mm -> 73 header/soket/JP1 pini (ESP32 sokeri 38, header 33, JP1 2); 1.3 mm -> YALNIZ 6 klemens pedi (J1, J9, J10); 3.2 mm -> 4 montaj deligi (kaplamasiz)
- Toplam delik: 159 kaplamali (101 pad + 58 via) + 4 kaplamasiz = 163

## Kart notlari
- GND dolgusu montaj deliklerine 0.3 mm kadar yaklasir (bakir-delik kenari). Metal M3 vida + somun/kasa kullanirsaniz GND kasaya baglanir. GND yuzdurulecekse (kasadan yalitilacaksa) naylon vida ve naylon pul kullanin.
- 12 V aglari (+12V, +12V_MOT, CHG+) netclass PWR12: iz 1.0 mm, yabanci bakirdan (iz, ped, via, GND dolgusu) en az 0.5 mm. DRC 0 hata; 0.5 mm'ye inemeyen nokta yok (ped/iz/dolgu olcumu >= 0.5).
- RF yasak bolgesi: ESP32 anten ucunda (x 148-157 mm, y 60.5-89.5 mm, iki katman) bakir dolgu, iz ve via YOKTUR (kart dosyasinda "RF_ANTEN_YASAK" kural alani). U1 pin 1 ve pin 20 (x=149.86) icin girinti birakildi. Anten ucunun yeri modul olculerine gore tahmin (pin 1'in yaklasik 4 mm otesi): gercek modulle dogrulayin. Bu yuzden 12 V ust direncleri R1, R3, R6 bolgenin dogusuna (x 158-165) tasindi; VBAT/VCHG/MSENSE dugumleri (sinyal) kuzey kenardan ESP32 pinlerine gider.
- ESP32 USB ucundaki fisin gecis yolu (x < 100 mm, y 69-81 mm) bos: C1 (100uF) J1'in sagina (alt kenar) tasindi, JP1 USB ucundan 5 mm uzaga alindi (modulle temas etmez).
- Ipek baski: her konnektor pininin yaninda pin adi (sema pin sirasi), pin 1 isareti "1" (kare ped de pin 1), klemenslerde ustte islev ("12V CHG" J9, "12V MOT" J10), bolucu direnclerinin govdesinde ag adi (VBAT, VCHG, MSENSE), baslik "CDTP ANA KART V1.0 / 2026-11-05". Ipek cizgi/yazi kalinligi >= 0.16 mm.
- IR konnektorleri J6/J7 pin sirasi 3V3, GND, OUT: VS1838B modulunun (OUT, GND, VCC) TERSIDIR; kartta "VS1838B TERS!" yazar. Modulu duz takmayin, kabloyu ters baglayin veya sirayi duzeltin.
- Klemens J9 (+12V, CHG+) ve J10 (+12V, NC) iki pinde de eksi (-) yoktur: yazilar "+12V", "CHG+", "NC"; J1 "+5V", "-GND".
- J9 ve J10 ayak izi sinirlari: J9 ~1 mm doguya kaydirildi, aralarinda ~1.2 mm bosluk var; 5.08 mm'lik klemens govdeleri yine de birbirine yaslanabilir, sikisiyorsa J9'u hafifce itin.

## Siparis ayarlari (JLCPCB / PCBWay)
- Base material FR-4, Layers 2, Dimensions 100 x 50 mm, PCB qty 5 (veya 10)
- Thickness 1.6 mm, Copper weight 1 oz, Surface finish HASL (lead free)
- Lehim maskesi acikligi (pad_to_mask_clearance) 0.05 mm; viyalar maskeyle KAPALI (tented), siparis formunda via covering/tenting default birakin
- Solder mask Green, Silkscreen White, Min track/spacing 6/6 mil yeterli (kullanilan 0.3 mm = 12 mil)
- Min hole size 0.3 mm secenegi yeterli (kullanilan 0.8), Via covering: default (tented)
- Castellated holes: yok, Edge plating: yok, Impedance: yok, Gold fingers: yok
- Remove order number: "Specify a location" veya sormasi icin not birakin
- Montaj (assembly) YOK: tum parcalar delikli, elle lehimlenir

## Malzeme listesi (kart uzerindeki parcalar, netlist.xml)
| Ref | Deger | Adet | Not |
|---|---|---|---|
| U1 | ESP32 DevKitC 38 pin | 1 | karta 2 adet 1x19 disi soket (2.54 mm) ile takilir, soket 2 adet |
| J1 | 5 V klemens 5.08 mm, 2 pin | 1 | |
| J9, J10 | klemens 5.08 mm, 2 pin | 2 | J9 sarj girisi (bos), J10 motor hatti |
| JP1 | 2 pin header + jumper | 1 | USB'de cikar |
| J2 | 1x5 header (IMU) | 1 | |
| J3, J8 | 1x5 header (BTS sol/sag) | 2 | |
| J4, J5 | 1x4 header (enkoder sol/sag) | 2 | |
| J6, J7 | 1x3 header (IR sol/sag) | 2 | genisleme, bos birakilabilir |
| J13 | 1x4 header (I2C) | 1 | genisleme |
| C1 | 100uF 16V elektrolitik | 1 | polarite: + isareti serigrafide |
| C2, C3, C4 | 100nF seramik | 3 | |
| R1, R3, R6 | 100k, 1/4 W | 3 | |
| R2, R4 | 27k, 1/4 W | 2 | |
| R7 | 33k, 1/4 W | 1 | |
| R5 | 10k, 1/4 W | 1 | |

Karta KONMAZ (kabloyla): A1-A3, M1-M2, BT1-3, U2, U3, J11, J12, F1, X1, X2, S1, C5.

## Montaj sirasi
1. Alcak parcalar: direncler R1-R7, sonra seramik C2-C4
2. JP1 ve tum header'lar (J2-J8, J13); header'i once tek pin lehimleyip duzeltin
3. Klemensler J1, J9, J10 (tel girisi kart disina baksin)
4. C1 (polarite!)
5. ESP32 soketleri (U1): once ESP32 modulunu soketlere takip hizalayin, sonra lehimleyin
6. En son ESP32 modulunu takin; 5 V olmadan once +5V/GND arasi kisa devre olcun

## UYARI: SIPARISTEN ONCE KONTROL EDIN
- **ESP32 DevKitC sira araligi: kartta ROW_PITCH_MM = 25.4 mm (1.0 inc) kullanildi. Elinizdeki gercek karti (pin sirasi merkezleri arasi) kumpasla olcun. Farkliysa SIPARIS VERMEYIN, once tools/kicad_pcb.py parametresini duzeltin.**
- **Klemens (J1, J9, J10) tel girisi yonu: tel kart kenarina bakan taraftan girmeli. Gercek klemensin tel girisi yonunu ve 5.08 mm pin araligini kontrol edin.**
- **ESP32 USB ucu kartin SOL kisa kenarina bakmali (serigrafide "ESP32 <USB"). Kart yonunu ve USB kablosunun disari erisimini dogrulayin.**
- **Konnektor pin 1 yonleri semadaki pin 1 ile ayni olmali (J2-J8, J13); BTS ve IMU modullerinin pin sirasini kendi modulunuzle karsilastirin.**
- **Montaj deligi M3 (3.2 mm) ve 100 x 50 mm kasa/yuva olculerini dogrulayin.**
