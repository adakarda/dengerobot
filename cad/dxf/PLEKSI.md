# Pleksi kesim notlari - sadece vida delikleri

Dosyalar: `kat1.dxf`, `kat2.dxf`, `kat3.dxf`, `pleksi_hepsi.dxf` (yan yana). Yerlesim onerisi: `yerlesim.png`. Yeniden uretmek icin: `python cad/pleksi_dxf.py` (olculer `PLAKA` ve `DISTANS`).

- Birim mm, 1:1, tek katman `KES`, 4 mm pleksi, kose R6. Dikdortgen, pencere, yuva, acil stop deligi YOK; sadece yuvarlak Ø3,4 vida delikleri.
- **kat1: 80 x 160 mm** (x ileri, y yanlara). 160'ta kaldi cunku teker ic yuzu |y| = 82,5; 170 olsa bile plaka tekerlege (yaricap 35, plaka z = 22) carpardi.
- **kat2 ve kat3: 80 x 170 mm** (tekerlegin ustunde kaldiklari icin sorun yok).
- Distans delikleri her katta ayni: x = +-32, y = +-72 (4 adet).
- kat1: 4 distans + 2 BTS7960 (4'er delik, merkez x = -12, |y| = 38, aralik 43 mm) + 2 L braket (4'er delik, x = +-15, |y| = 45 ve 69) = 20 delik.
- kat2: 4 distans + ana kart (altta asili, merkez x = -10, aralik 44 x 94 mm) 4 delik = 8 delik. kat3: 4 delik.

## Motor braketi (37 mm L klemens, aluminyum 3 mm)
- Kat1'in altina asili, ayak plakaya 1 mm aralikla (2 adet M3 pul). Vida M3x12, 8 vida + 8 somun + 16 pul. Vida basi ustte, somun ayagin altinda.
- Dik plakadaki yuva genisligi cizimde yok (13 mm varsayildi); braket gelince burca uydugunu kontrol et. Parametre: `cad/olcu.py BRK_YUVA`.

## Onerilen yerlesim (kesimde yok; bant / kablo bagi ile tutulur)
- kat1: 2 BTS7960, 2 WAGO, MPU6050 (x = 0, y = 0, teker ekseninin ustu), 1000 uF.
- kat2: 3x18650 pil, BMS, XT60, LM2596 (yatik); ana kart plakanin altinda.
- kat3: sigorta (acil stop butonu istersen Ø22 deligini sonradan delersin).

## Dikkat
- 3B baski CAD'i (`cad/robot_cad.py`, `montaj.glb`) hala 110 x 150 mm baski katlarina gore; pleksi plakalar ayri uretildi. Braket modeli (`stl/motor_braket_37mm.stl`) ayni kaldi.
- Plaka 80 mm genis: ana kart ve pil paketi sigiyor ama yerlesim sikisik; parcalar gelince kagit modelle dene.
