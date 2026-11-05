# Ana kart PCB tanimi (enkoderli, JGB37 + BTS7960 surumu)

ASCII ONLY: dosya adlari, net adlari, deger, ipek baski. Turkce karakter YOK.

## Amac
5x10 cm delikli plaketin yerine, ESP32 DevKitC (38 pin) soketli, 2 katli, tek yuzlu parcali (THT) ana kart.
Sema kaynagi: elektronik/cdtp_robot.kicad_sch ve elektronik/netlist.xml (KiCad 10). Sema degismez.
Pin atamalari firmware/robot/src/pins.h ile ayni; sema bunlari zaten dogruluyor.

## Kart uzerindeki parcalar (netlist.xml referanslari)
U1 (ESP32 DevKitC 38 pin, iki sira dis soket, sira araligi PARAMETRE: ROW_PITCH_MM=25.4 varsayilan, DevKitC V4 icin dogrula),
J1 (5 V klemens 5.08), C1 100uF 16V, JP1 (2 pin jumper header), R5 10k,
J2 (1x5 IMU), J3 (1x5 BTS sol), J8 (1x5 BTS sag), J4 (1x4 enkoder sol), J5 (1x4 enkoder sag),
J6 (1x3 IR sol), J7 (1x3 IR sag), J9 (1x2 klemens 5.08), J10 (1x2 klemens 5.08), J13 (1x4 I2C),
R1 100k, R2 27k, C2 100nF, R3 100k, R4 27k, C3 100nF, R6 100k, R7 33k, C4 100nF.
Kart disi (kabloyla baglanir, KARTA KONMAZ): A1,A2,A3,M1,M2,BT1-3,U2,U3,J11,J12,F1,X1,X2,S1,C5.
Konnektor pin sirasi sema ile BIREBIR ayni olmali (pin 1 = semadaki 1).

## Mekanik
Kart 100 x 50 mm, kose yaricapi 3 mm. 4 adet M3 montaj deligi (3.2 mm) 94 x 44 mm aralikla (ortalanmis).
Konnektorlerin kart kenarina bakan yonu: J10,J9,J1 klemensler alt kenarda; J3,J8 (BTS) ve J4,J5 ust kenarda;
J2,J13 (I2C hatti) ve J6,J7 yan kenarlarda. ESP32 USB ucu kart disina bakmali (kisa kenar, kartin disina tasma yok).

## Elektrik kurallari
Alt/ust bakir 35 um (1 oz). Sinyal izi >= 0.30 mm, +5V/+3V3 >= 0.6 mm, +12V ve +12V_MOT/GND >= 1.0 mm.
Bosluk >= 0.25 mm. Delik >= 0.8 mm, halka >= 0.3 mm. GND icin iki yuzde bakir dolgu (zone) ve vialarla birlestirme.
Yuksek akim yok: motor akimi karta girmez (BTS kartlari 12 V ve motoru dogrudan WAGO/klemenslerden alir). Kartta yalniz
olcum boluculeri, 3V3/5V dagitimi ve sinyal vardir. +12V (J9-1) ve +12V_MOT (J10-1) yalnizca bolucu girisidir (<1 mA).

## Cikti
elektronik/pcb/cdtp_ana_kart.kicad_pcb, DRC raporu (0 hata), gerber/ klasoru (F_Cu, B_Cu, F_Mask, B_Mask,
F_Silkscreen, B_Silkscreen, Edge_Cuts, F_Paste yok) + delik (Excellon) + zip: elektronik/pcb/gerber/CDTP_ana_kart_gerber.zip.
Uretim notlari: elektronik/pcb/URETIM.md (ASCII, JLCPCB/PCBWay ayarlari).
