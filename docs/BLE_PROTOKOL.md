> **ESKI (kullanimdan kalkti, 2026-11-12).** Robot firmware'i artik takimin kararina uygun **Wi-Fi WebSocket** kullanir (ADR-0003, shared/protocol/messages.md): robot `CDTP-ROBOT` agini acar, sunucu `ws://192.168.4.1:81/`, telemetri 5 Hz JSON, `cmd` ve `ping` mesajlari. Bu dosya sadece tarihce icin duruyor.

# Robot ↔ telefon BLE protokolü (Bilgisayar ekibi için)

Robot kendini **`CDTP-Robot`** adıyla duyurur. Tek servis, iki karakteristik:

| Ne | UUID | Özellik |
|---|---|---|
| Servis | `6e400001-cd7b-4e3a-9a40-2026cd7b0001` | |
| Telemetri | `6e400002-cd7b-4e3a-9a40-2026cd7b0001` | READ + NOTIFY, saniyede 1 (1 Hz) |
| Komut | `6e400003-cd7b-4e3a-9a40-2026cd7b0001` | WRITE (metin) |

Bağlandıktan sonra MTU'yu 247 isteyin (telemetri ~200 bayt). Android: `requestMtu(247)`.

## Telemetri (robot → telefon, 1 Hz)

```json
{"seq":42,"t":42013,"bat":78,"v":11.83,"tilt":0.6,"chg":0,"mode":"DENGE","mot":"ilerliyor",
 "dir":"ileri","task":"butunlesik","dock":"-","x":0.512,"yaw":0,"glove":"ileri","ir":[0,0]}
```

| Alan | Anlamı |
|---|---|
| `seq` | Her pakette +1. Atlama varsa paket kaybı. |
| `t` | Robotun açılıştan beri ms'si |
| `bat`, `v` | Pil yüzdesi (gerilimden) ve gerilim |
| `tilt` | Gövde eğimi, derece (öne +) — **şartnamedeki eğim bilgisi** |
| `chg` | 1 = plakada şarj gerilimi var — **şartnamedeki şarj durumu** |
| `mode` | `BEKLE`, `DENGE`, `YANASMA`, `SARJ`, `DUSTU` |
| `mot` | `statik`, `ilerliyor`, `donuyor`, `toparlaniyor` |
| `dir` | `ileri`, `geri`, `sol`, `sag`, `-` |
| `task` | Seçili görev |
| `dock` | Yanaşma durumu: `ARA`, `HIZALAN`, `YAKLAS`, `YERLES`, `SARJ`, `BASARISIZ`, `-` |
| `x`, `yaw` | Enkoder yolu (m) ve dönüş açısı (derece). Kamera ölçümünü doğrulamak için. |
| `glove` | Son eldiven komutu, eldiven sessizse `yok` |
| `ir` | Sol/sağ IR gözü sayımı |

**Kopma kuralı (şartname: en fazla 2 s):** uygulama 2 s yeni `seq` almazsa ekranda "bağlantı yok" göstermeli ve
yeniden bağlanmalı.

## Komut (telefon → robot)

| Metin | Etki |
|---|---|
| `task=0` | Statik denge (eldiven ve yanaşma kapalı) |
| `task=1` | Yönlendirme (eldiven açık, yanaşma kapalı) |
| `task=2` | Şarj (robot 1 s sonra istasyonu aramaya başlar) |
| `task=3` | Bütünleşik görev (eldiven açık; eldiven 6 s boşta kalınca ve işaret görülünce yanaşır) |
| `stat` | Teşhis bilgisi seri porta yazılır |

Uygulama robotu **sürmez**; yalnız görevi seçer. Testte "Start Test" anı uygulamanın kendi saatidir; robotun `t`
alanı yalnız eşleştirme içindir.
