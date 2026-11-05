"""3B baski parcalarinin tum olculeri (mm). Eksenler: X ileri, Y sol, Z yukari; orijin teker ekseninin ortasi.
Zemin z = -35. Parca gelince kumpasla olcun; (OLC) isaretlileri saticiya gore degisir.
Degistirdikten sonra: python cad/robot_cad.py  (STL'ler ve kontrol raporu yeniden uretilir)."""

# --- Genel ---
R_TEKER = 35.0           # 70 mm teker (Pololu 3272)
TEKER_EN = 25.0          # lastik genisligi
IZ = 190.0               # iz genisligi; degisirse cdtp_config.h TRACK_WIDTH_M de degismeli
ZEMIN = -R_TEKER
BOSLUK = 0.3             # yuva bosluk payi (her yanda), PLA 0,4 mm nozul icin
DUVAR = 1.6              # yuva duvari kalinligi
VIDA_D = 3.4             # M3 gecis deligi
KILAVUZ_D = 2.8          # M3 vidanin plastige dogrudan girecegi pilot delik
SOMUN_AA = 5.7           # M3 somun anahtar agzi + bosluk
KELEPCE = (4.0, 2.2)     # kablo bagi yuvasi (uzunluk, genislik); 3,6 mm bag icin

# --- Katlar ---
KAT_X, KAT_Y, KAT_T = 110.0, 150.0, 4.0
KAT_KOSE_R = 6.0
DISTANS_XY = (49.0, 69.0)            # kose delikleri (kenardan 6 mm)
DISTANS_AA = 5.5                     # M3 disi-disi distans altigen
KAT1_Z, KAT2_Z, KAT3_Z = 22.0, 106.0, 190.0   # alt yuzler; 30+50 = 80 mm distans + 4 mm kat

# --- Motor: JGB37-520, eksantrik mil ---
MOTOR_SANZ_D, MOTOR_SANZ_L = 37.0, 26.0   # sanziman (cizim: 26, oran ile 26-29 degisir)
MOTOR_GOVDE_D, MOTOR_GOVDE_L = 33.0, 31.0  # motor + enkoder kapagi (OLC: toplam ~55)
MOTOR_MIL_KACIK = 7.0                     # mil, motor ekseninin 7 mm ustunde (motor asagida)
MOTOR_MIL_D, MOTOR_MIL_L = 6.0, 15.0
MOTOR_BURC_D = 12.5                       # (OLC) mil burcu cikintisi icin delik
MOTOR_DELIK_PCD, MOTOR_DELIK_ACI0 = 31.0, 0.0   # 6 x M3, 31 mm daire; (OLC) delik acisi
MOTOR_YUZ_Y = 75.0                        # sanziman on yuzu |Y|
TUTUCU_T = 5.0                            # motor tutucu on plaka kalinligi

# --- Moduller (en, boy, yukseklik); delikler (OLC) ---
BTS = (50.0, 50.0, 35.0)
BTS_DELIK = 43.0          # (OLC) dort kose delik araligi
BTS_AYAK = 5.0            # kart alti bosluk
MPU = (21.0, 16.0, 3.0)   # GY-521; uzun kenar X'e (ileri)
MPU_DELIK = (15.2, 7.5)   # (OLC) iki delik: aralik Y, uzun kenarin ucundan X
LM2596 = (48.0, 23.0, 14.0)
SIGORTA = (36.0, 18.0, 15.0)   # (OLC) bicak sigorta yuvasi
WAGO = (30.0, 18.8, 8.6)       # 221-415
C5 = (13.0, 25.0)              # 1000 uF 25 V (cap, boy) yatay
PIL = (78.0, 60.0, 21.0)       # 3x18650 yuva (Y, X, Z)
BMS = (50.0, 16.0, 4.0)        # HX-3S-01
XT60 = (16.0, 15.6, 8.2)
ANAKART = (100.0, 50.0, 1.6)   # 5x10 delikli plaket
ANAKART_DELIK = (94.0, 44.0)   # (OLC) kose delik araliklari
ANAKART_YUK = 22.0             # header + ESP32 kart + modul yuksekligi
ACIL_DELIK = 22.3              # 22 mm buton deligi
ACIL_GOVDE = (32.0, 42.0, 45.0)  # (OLC) kat 3 altindaki kontak blogu
ACIL_MANTAR = (40.0, 28.0)     # mantar cap, yukseklik
KUTU = (70.0, 45.0, 25.0)      # ilac kutusu (X, Y, Z)
KUTU_PAY = 1.0                 # her yanda
KUTU_DUVAR = (2.4, 25.0)       # kalinlik, yukseklik
KUTU_Y = 27.0                  # cep merkezi (sol); sag tarafta acil stop

# --- Sarj temasi (istasyonla ortak; robot_src.html bolum 09) ---
POGO_D, POGO_L, POGO_CIKIS = 5.0, 16.0, 3.0     # (OLC)
PIM_UST_ZEMIN, PIM_ALT_ZEMIN = 102.0, 77.0
MIKNATIS = (10.0, 3.0)          # N52, iki tane ust uste
SERIT_ZEMIN = (85.0, 94.0)      # direkteki celik serit
V_SERIT_ON_X = 59.0             # arka seridin on yuzu (ikizle ayni)
V_SERIT_Y = 20.0
V_KANAT_L, V_KANAT_T = 42.0, 3.0
DIREK_D = 40.0

# --- IR gozleri ---
GOZ_ZEMIN = 147.0
GOZ_ACI = 15.0
GOZ_Y = 14.0
GOZ_PENCERE = (7.4, 7.4)        # VS1838B basi
GOZ_TUP_L = 15.0
