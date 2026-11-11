# Ana kart V2 (TB6612) - uretim notlari

Dosya: `gerber/CDTP_ana_kart_v2_gerber.zip` (9 dosya). Uretim: `python tools/kicad_v2_netlist.py` sonra `python tools/kicad_pcb_v2.py`.

- Kart 130 x 80 mm, 2 katman, 1,6 mm, delikten gecmeli (THT), M3 delikler 122 x 72 mm.
- DRC: 0 hata, 0 uyari. Netlist = kart: 96 ped, hepsi ayni. Tum 14 kontrol GECTI.
- Siparis: 2 katman, HASL, 1,6 mm, min 5 adet.

## VARSAYIMLAR - SIPARISTEN ONCE OLC

1. ESP32 DevKitC iki sira arasi 25,4 mm (`ROW_PITCH_MM`). Kendi kartini olc.
2. TB6612 modulu: iki sira arasi 15,24 mm (`TB_ROW_MM`), pin sirasi PWMA AIN2 AIN1 STBY BIN1 BIN2 PWMB GND / VM VCC GND AO1 AO2 BO2 BO1 GND.
3. LM2596 mini: ped araligi 40,64 x 20,32 mm (`LM_DX_MM`, `LM_DY_MM`), IN+ sol alt, IN- sol ust, OUT+ sag alt, OUT- sag ust.
4. IR modul pin sirasi: VCC GND OUT. MPU6050 (GY-521) pin sirasi: VCC GND SCL SDA XDA XCL AD0 INT.
5. Motor konnektoru 6 pin: M1 GND C1 C2 VCC M2 (motor kablosuna gore uyarla).

## Dogrulama
Gerber'i 1:1 yazdir (kart olcusu 130 x 80 mm), modulleri uzerine koy, pinler deliklere denk gelmeli.
Lehim gerekir (soket, klemens, sigorta, kondansator, direnc).
