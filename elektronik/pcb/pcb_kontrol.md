# Ana kart PCB denetimi

`python tools/kicad_pcb.py` uretir. ROW_PITCH_MM = 25.4

DRC: 0 hata, 0 uyari, 0 baglanmamis madde (drc.json, drc.rpt)

Kural seti (cdtp_ana_kart.kicad_pro): min bosluk 0.25, min iz 0.3, via 1.45/0.8, halka 0.3, kart kenari 0.5; netclass: PWR12 iz 1.0 bosluk 0.5, PWR5 iz 0.6, Default iz 0.3. DRC bu kurallarla kosturuldu (kopya uzerinde); gercek .kicad_pro DRC'den sonra yeniden yazilip dogrulandi.

| Kontrol | Sonuc | Ayrinti |
|---|---|---|
| kart parcalari = SPEC listesi | GECTI | 24 parca |
| her ped agi = netlist | GECTI | 101 ped, hepsi ayni |
| netlistteki tum kart pinleri kartta var | GECTI | tam |
| RF yasak bolgesi (anten ucu): iz/via/dolgu yok | GECTI | x 148.0-157.0 y 60.5-89.5, iki katman; ihlal: iz/via 0, dolgu noktasi 0 |
| ipek cizgi/yazi kalinligi >= 0.153 mm | GECTI | 269 footprint cizgisi + 73 yazi; ince: yok |
| pin yazilari (sema sirasi) + pin 1 isaretleri | GECTI | 41 pin adi, '1' isareti 9/9 |
| baslik 'CDTP ANA KART V1.0' + tarih 2026-11-05 | GECTI | var |
| klemens etiketleri 12V CHG (J9) / 12V MOT (J10) | GECTI | var |
| lehim maskesi acikligi 0.05 mm | GECTI | 0.05 mm (via'lar maskeyle kapali/tented) |
| sayimlar | GECTI | 190 iz parcasi, 58 via |
| .kicad_pro kurallari dosyada duruyor | GECTI | DRC sonrasi dogrulandi |
| DRC proje kurallariyla kostu | GECTI | kopyadaki proje dosyasinda kurallar korundu |
| gerber + delik + zip (9 dosya, .gbrjob zip'te yok) | GECTI | cdtp_ana_kart-F_Cu.gtl, cdtp_ana_kart-B_Cu.gbl, cdtp_ana_kart-F_Mask.gts, cdtp_ana_kart-B_Mask.gbs, cdtp_ana_kart-F_Silkscreen.gto, cdtp_ana_kart-B_Silkscreen.gbo, cdtp_ana_kart-Edge_Cuts.gm1, cdtp_ana_kart-PTH.drl, cdtp_ana_kart-NPTH.drl |
| uretilen dosyalar ASCII | GECTI | pcb, pro, drc.json, drc.rpt |

12 V aglari (+12V, +12V_MOT, CHG+): PWR12 sinifi 0.5 mm bosluk; DRC hatasiz oldugu icin tum 12 V bakiri yabanci bakirdan (iz, ped, via, GND dolgusu) en az 0.5 mm uzaktadir; 0.5'e inemeyen yer yok.
