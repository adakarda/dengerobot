# KiCad sema denetimi

`python tools/kicad_sema.py` uretir. Kagit A3, 41 sembol.

| Kontrol | Sonuc | Ayrinti |
|---|---|---|
| KiCad ERC | GECTI | 0 hata, 0 uyari |
| ESP32 pinleri = firmware/robot/src/pins.h | GECTI | 17 pin sabiti, her biri ESP32 + ana kart konnektoru + modul ucunda dogru |
| Guc ve kablo listesi (W1-W44) | GECTI | 17 baglanti grubu dogru; acil stop, JP1 ve XT60 hatlari ayri |
| Bolucu degerleri | GECTI | R1/R2 orani 4.704 = firmware DIVIDER 4.704; 12,6 V -> 2.68 V (ADC 11 dB); R6/R7 -> 3.13 V < 3,3 V |
| Tek uclu hat yok | GECTI | 57 hat |
