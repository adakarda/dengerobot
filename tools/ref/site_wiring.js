const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export const WIRE_KINDS = {
  p12: { color: '#ff5a5a', width: 2.6, label: '12 V güç' },
  mot: { color: '#ff8f6b', width: 2.6, label: 'Motor çıkışı' },
  p5: { color: '#ffa94d', width: 2, label: '5 V' },
  p33: { color: '#ffd43b', width: 1.6, label: '3,3 V' },
  gnd: { color: '#7d8696', width: 1.4, label: 'GND (hepsi ortak)' },
  pwm: { color: '#b48cff', width: 1.6, label: 'PWM / enable' },
  enc: { color: '#3fb950', width: 1.6, label: 'Enkoder A/B' },
  i2c: { color: '#2bb3a3', width: 1.6, label: 'I2C' },
  an: { color: '#5b8def', width: 1.6, label: 'Giriş (analog / sayısal)' },
  ctl: { color: '#9aa4b2', width: 1.5, label: 'Sinyal / veri' },
  chg: { color: '#ff5a5a', width: 2.6, dash: '8 5', label: 'Şarj teması' },
  ir: { color: '#ff7b7b', width: 1.8, dash: '2 5', label: 'IR ışık' },
  rf: { color: '#e06c8a', width: 1.8, dash: '8 6', label: 'Kablosuz' },
};

const NODE_COLORS = { r: '#5b8def', e: '#e0a030', g: '#2bb3a3', p: '#9b7cf0', n: '#9aa4b2', b: '#f85149' };

function markers(id, kinds) {
  return `<defs>${kinds
    .map((k) => `<marker id="${id}-${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${WIRE_KINDS[k].color}"/></marker>`)
    .join('')}</defs>`;
}

function lines(texts, x, y, step, cls, anchor = 'start') {
  return texts.map((t, i) => `<text x="${x}" y="${y + i * step}" class="${cls}" text-anchor="${anchor}">${esc(t)}</text>`).join('');
}

// Boxes on a column/row grid, wires routed orthogonally between box sides.
export function flowDiagram(id, { nodes, edges, colW = 210, rowH = 96, bw = 150, bh = 60 }) {
  const pad = 16;
  const by = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const cols = Math.max(...nodes.map((n) => n.c)) + 1;
  const rows = Math.max(...nodes.map((n) => n.r)) + 1;
  const W = pad * 2 + (cols - 1) * colW + bw;
  const H = pad * 2 + (rows - 1) * rowH + bh;
  const gap = colW - bw;
  const box = (n) => ({ x: pad + n.c * colW, y: pad + n.r * rowH, w: bw, h: bh });

  function route(e) {
    const A = by[e.from];
    const B = by[e.to];
    const a = box(A);
    const b = box(B);
    if (A.c === B.c) {
      const x = a.x + a.w / 2 + (e.dx ?? 0);
      const down = a.y < b.y;
      return [[x, down ? a.y + a.h : a.y], [x, down ? b.y : b.y + b.h]];
    }
    const right = a.x < b.x;
    const sx = right ? a.x + a.w : a.x;
    const ex = right ? b.x : b.x + b.w;
    const sy = a.y + a.h / 2 + (e.sy ?? 0);
    const ey = b.y + b.h / 2 + (e.ey ?? 0);
    if (Math.abs(sy - ey) < 1) return [[sx, sy], [ex, ey]];
    const mx = e.at === 'end' ? ex + (right ? -gap / 2 : gap / 2) : sx + (right ? gap / 2 : -gap / 2);
    return [[sx, sy], [mx, sy], [mx, ey], [ex, ey]];
  }

  const kinds = [...new Set(edges.map((e) => e.k))];
  const wires = edges
    .map((e) => {
      const k = WIRE_KINDS[e.k];
      const pts = route(e);
      const d = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ');
      let best = 0;
      let seg = [pts[0], pts[1]];
      for (let i = 0; i < pts.length - 1; i++) {
        const len = Math.abs(pts[i + 1][0] - pts[i][0]) + Math.abs(pts[i + 1][1] - pts[i][1]);
        if (len > best) {
          best = len;
          seg = [pts[i], pts[i + 1]];
        }
      }
      const [[x1, y1], [x2, y2]] = seg;
      const horizontal = Math.abs(y1 - y2) < 1;
      const label = e.label
        ? horizontal
          ? `<text x="${(x1 + x2) / 2}" y="${y1 - 7}" class="dw-l" text-anchor="middle">${esc(e.label)}</text>`
          : `<text x="${e.labelLeft ? x1 - 7 : x1 + 7}" y="${(y1 + y2) / 2 + 4}" class="dw-l" text-anchor="${e.labelLeft ? 'end' : 'start'}">${esc(e.label)}</text>`
        : '';
      return `<path d="${d}" fill="none" stroke="${k.color}" stroke-width="${k.width}" ${k.dash ? `stroke-dasharray="${k.dash}"` : ''} marker-end="url(#${id}-${e.k})" ${e.both ? `marker-start="url(#${id}-${e.k})"` : ''}/>${label}`;
    })
    .join('');

  const boxes = nodes
    .map((n) => {
      const { x, y, w, h } = box(n);
      const c = NODE_COLORS[n.k ?? 'n'];
      const sub = (n.s ?? '').split('\n').filter(Boolean);
      return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="#1b212c" stroke="${c}" stroke-width="1.4"/>
        <rect x="${x}" y="${y + 8}" width="3" height="${h - 16}" rx="1.5" fill="${c}"/>
        <text x="${x + 12}" y="${y + 21}" class="dn-t">${esc(n.t)}</text>
        ${lines(sub, x + 12, y + 37, 13, 'dn-s')}</g>`;
    })
    .join('');

  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" style="--w:${W}px" xmlns="http://www.w3.org/2000/svg">${markers(id, kinds)}${wires}${boxes}</svg>`;
}

// Microcontroller in the middle, connected modules on both sides, one straight wire per pin.
export function pinDiagram(id, { mcu, left, right }) {
  const rowH = 26;
  const pad = 16;
  const top = 52;
  const devW = 220;
  const wire = 132;
  const mcuW = 200;
  const layout = (groups) => {
    let y = 0;
    return groups.map((g) => {
      const rows = Math.max(g.pins.length, 2);
      const out = { ...g, y0: y, rows };
      y += rows * rowH + 14;
      return out;
    });
  };
  const L = layout(left);
  const R = layout(right);
  const height = (G) => (G.length ? G.at(-1).y0 + G.at(-1).rows * rowH : 0);
  const innerH = Math.max(height(L), height(R));
  const W = pad * 2 + devW * 2 + wire * 2 + mcuW;
  const H = top + pad + innerH + 12;
  const xMcu = pad + devW + wire;
  const kinds = new Set();

  function side(groups, isLeft) {
    const xDev = isLeft ? pad : xMcu + mcuW + wire;
    return groups
      .map((g) => {
        const y = top + g.y0;
        const h = g.rows * rowH;
        const c = NODE_COLORS[g.k ?? 'r'];
        const titleX = isLeft ? xDev + 12 : xDev + devW - 12;
        const anchor = isLeft ? 'start' : 'end';
        const head = `<rect x="${xDev}" y="${y}" width="${devW}" height="${h}" rx="8" fill="#1b212c" stroke="${c}" stroke-width="1.4"/>
          <text x="${titleX}" y="${y + 18}" class="dn-t" text-anchor="${anchor}">${esc(g.t)}</text>
          ${lines((g.s ?? '').split('\n').filter(Boolean), titleX, y + 33, 13, 'dn-s', anchor)}`;
        const pins = g.pins
          .map(([devPin, gpio, k, note], i) => {
            kinds.add(k);
            const py = y + i * rowH + rowH / 2;
            const K = WIRE_KINDS[k];
            const x1 = isLeft ? xDev + devW : xMcu + mcuW;
            const x2 = isLeft ? xMcu : xDev;
            const devX = isLeft ? xDev + devW - 8 : xDev + 8;
            const gpioX = isLeft ? xMcu + 8 : xMcu + mcuW - 8;
            return `<line x1="${x1}" y1="${py}" x2="${x2}" y2="${py}" stroke="${K.color}" stroke-width="${K.width}"/>
              <circle cx="${x1}" cy="${py}" r="2.6" fill="${K.color}"/><circle cx="${x2}" cy="${py}" r="2.6" fill="${K.color}"/>
              <text x="${devX}" y="${py + 4}" class="dp" text-anchor="${isLeft ? 'end' : 'start'}">${esc(devPin)}</text>
              <text x="${gpioX}" y="${py + 4}" class="dg" text-anchor="${isLeft ? 'start' : 'end'}">${esc(gpio)}</text>
              ${note ? `<text x="${(x1 + x2) / 2}" y="${py - 5}" class="dw-l" text-anchor="middle">${esc(note)}</text>` : ''}`;
          })
          .join('');
        return head + pins;
      })
      .join('');
  }

  const body = side(L, true) + side(R, false);
  const mcuBox = `<rect x="${xMcu}" y="${top - 8}" width="${mcuW}" height="${innerH + 16}" rx="10" fill="#18233a" stroke="#5b8def" stroke-width="1.8"/>
    <text x="${xMcu + mcuW / 2}" y="${top - 30}" class="dn-t" text-anchor="middle">${esc(mcu.t)}</text>
    <text x="${xMcu + mcuW / 2}" y="${top - 15}" class="dn-s" text-anchor="middle">${esc((mcu.s ?? '').replace(/\n/g, ' · '))}</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" style="--w:${W}px" xmlns="http://www.w3.org/2000/svg">${mcuBox}${body}</svg>`;
}

export function legend(kinds) {
  return `<div class="legend">${kinds
    .map((k) => {
      const K = WIRE_KINDS[k];
      return `<span><svg width="26" height="8"><line x1="0" y1="4" x2="26" y2="4" stroke="${K.color}" stroke-width="${K.width}" ${K.dash ? `stroke-dasharray="${K.dash}"` : ''}/></svg>${esc(K.label)}</span>`;
    })
    .join('')}</div>`;
}

// Content

export const BOARDS = [
  {
    name: 'Robot ESP32',
    part: 'ESP32-WROOM-32D geliştirme kartı',
    k: 'r',
    jobs: [
      'Tek beyin. Denge döngüsünü 200 Hz koşturur.',
      'Enkoderleri kendi donanım sayacıyla (PCNT) okur; ayrı kart gerekmez, işlemciyi meşgul etmez.',
      'İki BTS7960’a 20 kHz PWM verir.',
      'İki IR gözüyle istasyonu arar, yanaşmayı yönetir.',
      'Eldiven komutunu ESP-NOW ile alır, telefona BLE ile 1 Hz telemetri yollar.',
      'Pil gerilimini ve plakadaki şarj gerilimini ölçer.',
    ],
  },
  {
    name: 'Eldiven ESP32-C3',
    part: 'ESP32-C3 Mini (Super Mini) kartı',
    k: 'g',
    jobs: [
      'El sırtındaki MPU6050’den eğimi 50 Hz okur.',
      'Eğimi beş komuttan birine çevirir: ileri, geri, sola, sağa, dur.',
      'Komutu saniyede 20 kez ESP-NOW ile robota yollar.',
      'Küçük ve hafif; 1S LiPo ile doğrudan beslenir.',
    ],
  },
  {
    name: 'BTS7960 × 2',
    part: 'Motor sürücü, her motora bir tane',
    k: 'r',
    jobs: [
      'Karar vermez. ESP32’nin 3,3 V PWM sinyalini 12 V motor akımına çevirir.',
      'RPWM ileri, LPWM geri; iki enable ucu birlikte motoru açıp kapatır.',
    ],
  },
  {
    name: 'Şarj istasyonu',
    part: 'Mikrodenetleyici yok',
    k: 'e',
    jobs: [
      'Type-C dönüştürücü kart: adaptörün 5 V’unu şarj kartına ve işaret devresine dağıtır.',
      '3S şarj kartı: 5 V’tan 12,6 V sabit akım / sabit gerilim şarj.',
      'Şarj göstergesi kartın CHG LED’i. Şartname gereği yazılımla yakılamaz; bu yüzden istasyonda yazılım gerekmez.',
      'Üç NE555: 38 kHz’lik IR ışığı 1 kHz’lik patlamalar hâlinde yakar, her 78 ms’de 33 ms susar.',
    ],
  },
  {
    name: 'Telefon',
    part: 'Uygulama',
    k: 'p',
    jobs: [
      'Robota BLE ile bağlanır; şarj ve eğimi 1 Hz gösterir.',
      'Görevi seçer (denge, yönlendirme, şarj, tam görev) ve robota yazar.',
      'Kamerayla hareketi ve yönü kendisi tespit eder; robotu sürmez.',
    ],
  },
];

export const SYSTEM_FLOW = {
  colW: 340,
  bw: 170,
  rowH: 110,
  nodes: [
    { id: 'glove', c: 0, r: 0, t: 'Eldiven', s: 'ESP32-C3 + MPU6050\n1S LiPo', k: 'g' },
    { id: 'robot', c: 1, r: 0, t: 'Robot ESP32', s: 'denge · sürüş · yanaşma', k: 'r' },
    { id: 'phone', c: 2, r: 0, t: 'Telefon uygulaması', s: 'izleme · kamera · rapor', k: 'p' },
    { id: 'station', c: 1, r: 1, t: 'Şarj istasyonu', s: 'MCU yok, tamamen donanım', k: 'e' },
  ],
  edges: [
    { from: 'glove', to: 'robot', k: 'rf', label: 'ESP-NOW · 20 Hz komut' },
    { from: 'robot', to: 'phone', k: 'rf', label: 'BLE · telemetri ⇄ görev', both: true },
    { from: 'station', to: 'robot', k: 'ir', label: 'IR 38 kHz işaret', dx: -30, labelLeft: true },
    { from: 'station', to: 'robot', k: 'chg', label: 'pogo · 12,6 V', dx: 30 },
  ],
};

export const ROBOT_PINS = {
  mcu: { t: 'Robot ESP32 (WROOM-32D)', s: 'Çekirdek 1: denge 200 Hz\nÇekirdek 0: ESP-NOW, BLE, IR' },
  left: [
    { t: 'MPU6050 · gövde', s: 'Teker ekseni üstünde,\nortada', pins: [['SDA', 'GPIO21', 'i2c'], ['SCL', 'GPIO22', 'i2c'], ['INT', 'GPIO19', 'i2c', 'veri hazır']] },
    { t: 'IR alıcı · sol göz', s: 'VS1838B / TSOP1838', pins: [['OUT', 'GPIO36 (VP)', 'an', 'yalnız giriş']] },
    { t: 'IR alıcı · sağ göz', s: 'VS1838B / TSOP1838', pins: [['OUT', 'GPIO39 (VN)', 'an', 'yalnız giriş']] },
    { t: 'Pil gerilimi', s: '100 kΩ / 27 kΩ bölücü', pins: [['orta uç', 'GPIO35', 'an', 'ADC1']] },
    { t: 'Şarj algılama', s: 'Plaka +, 100k / 27k', pins: [['orta uç', 'GPIO34', 'an', '12 V gelince 1']] },
    { t: 'LM2596 · 5 V çıkışı', s: 'Kartın beslemesi', k: 'e', pins: [['OUT+', '5V / VIN', 'p5'], ['OUT−', 'GND', 'gnd']] },
  ],
  right: [
    { t: 'BTS7960 · sol motor', s: 'VCC = 3,3 V', pins: [['RPWM', 'GPIO27', 'pwm', 'ileri'], ['LPWM', 'GPIO14', 'pwm', 'geri'], ['R_EN + L_EN', 'GPIO4', 'pwm', 'enable · 10 kΩ GND']] },
    { t: 'BTS7960 · sağ motor', s: 'VCC = 3,3 V', pins: [['RPWM', 'GPIO16', 'pwm', 'ileri'], ['LPWM', 'GPIO17', 'pwm', 'geri'], ['R_EN + L_EN', 'GPIO4', 'pwm', 'aynı enable']] },
    { t: 'Sol motor enkoderi', s: 'Hall · VCC = 3,3 V', pins: [['C1 (A)', 'GPIO32', 'enc', 'PCNT'], ['C2 (B)', 'GPIO33', 'enc', 'PCNT']] },
    { t: 'Sağ motor enkoderi', s: 'Hall · VCC = 3,3 V', pins: [['C1 (A)', 'GPIO25', 'enc', 'PCNT'], ['C2 (B)', 'GPIO26', 'enc', 'PCNT']] },
    { t: '3,3 V dağıtım', s: 'IMU, IR, enkoder,\nBTS7960 VCC', k: 'e', pins: [['VCC', '3V3', 'p33'], ['GND', 'GND', 'gnd']] },
  ],
};

export const GLOVE_PINS = {
  mcu: { t: 'Eldiven ESP32-C3 Mini', s: '50 Hz oku\n20 Hz yolla' },
  left: [
    { t: 'MPU6050 · el sırtı', s: 'Bileğe yakın, düz', k: 'g', pins: [['SDA', 'GPIO6', 'i2c'], ['SCL', 'GPIO7', 'i2c'], ['VCC', '3V3', 'p33'], ['GND', 'GND', 'gnd']] },
  ],
  right: [
    { t: 'TP4056 + anahtar', s: '1S LiPo 3,7 V\nkorumalı, Type-C', k: 'e', pins: [['OUT+', '5V', 'p5', 'anahtardan'], ['OUT−', 'GND', 'gnd']] },
    { t: 'Pil ölçümü', s: 'isteğe bağlı\n100k / 100k bölücü', k: 'e', pins: [['orta uç', 'GPIO3', 'an', 'ADC1']] },
  ],
};

export const POWER_FLOW = {
  nodes: [
    { id: 'bat', c: 0, r: 0, t: '3S Li-ion paket', s: '3 × 18650 seri\n11,1 V · dolu 12,6 V', k: 'e' },
    { id: 'bms', c: 1, r: 0, t: '3S BMS', s: 'aşırı şarj, deşarj,\nkısa devre koruması', k: 'e' },
    { id: 'fuse', c: 2, r: 0, t: 'Sigorta 5 A', s: 'bıçak sigorta yuvası', k: 'e' },
    { id: 'stop', c: 3, r: 0, t: 'Acil stop', s: 'yalnız motor hattını\nkeser', k: 'b' },
    { id: 'btsl', c: 4, r: 0, t: 'BTS7960 sol', s: 'B+ / B− güç girişi', k: 'r' },
    { id: 'btsr', c: 4, r: 1, t: 'BTS7960 sağ', s: 'B+ / B− güç girişi', k: 'r' },
    { id: 'ml', c: 5, r: 0, t: 'Sol motor', s: 'M+ / M− ← sürücü', k: 'r' },
    { id: 'mr', c: 5, r: 1, t: 'Sağ motor', s: 'ayna takılı; yön\nyazılımda çevrilir', k: 'r' },
    { id: 'buck', c: 2, r: 2, t: 'LM2596 → 5 V', s: '12 V → 5 V, 3 A', k: 'e' },
    { id: 'esp', c: 3, r: 2, t: 'Robot ESP32', s: 'VIN 5 V\nacil stopta açık kalır', k: 'r' },
    { id: 'v33', c: 4, r: 2, t: '3,3 V çevre', s: 'IMU, IR, enkoder,\nBTS7960 mantık', k: 'r' },
    { id: 'plate', c: 0, r: 3, t: 'Şarj plakaları', s: 'istasyonun pogo\npinine değer', k: 'e' },
    { id: 'diode', c: 1, r: 3, t: 'Schottky diyot', s: 'SR5100 · plakada\npil gerilimi olmaz', k: 'e' },
  ],
  edges: [
    { from: 'bat', to: 'bms', k: 'p12', label: 'B+ / B−' },
    { from: 'bms', to: 'fuse', k: 'p12', label: 'P+' },
    { from: 'fuse', to: 'stop', k: 'p12' },
    { from: 'stop', to: 'btsl', k: 'p12', label: '12 V' },
    { from: 'stop', to: 'btsr', k: 'p12', sy: 10 },
    { from: 'btsl', to: 'ml', k: 'mot' },
    { from: 'btsr', to: 'mr', k: 'mot' },
    { from: 'fuse', to: 'buck', k: 'p12', label: 'acil stoptan önce' },
    { from: 'buck', to: 'esp', k: 'p5', label: '5 V' },
    { from: 'esp', to: 'v33', k: 'p33', label: '3V3' },
    { from: 'plate', to: 'diode', k: 'chg', label: '+' },
    { from: 'diode', to: 'bms', k: 'p12', label: 'P+ (şarj girişi)' },
  ],
};

export const STATION_FLOW = {
  colW: 200,
  bw: 160,
  bh: 64,
  nodes: [
    { id: 'ad', c: 0, r: 0, t: '5 V 3 A adaptör', s: '220 V → 5 V\nUSB kablo', k: 'e' },
    { id: 'usb', c: 1, r: 0, t: 'Type-C dönüştürücü', s: 'CC1, CC2: 5,1 kΩ\n470 µF + 100 nF', k: 'e' },
    { id: 'chg', c: 2, r: 0, t: '3S şarj kartı', s: 'IN+/IN− pedinden\nCHG LED = gösterge', k: 'e' },
    { id: 'pogo', c: 3, r: 0, t: 'Pogo pin 2 + 2', s: 'yaylı, sırtta', k: 'e' },
    { id: 'rob', c: 4, r: 0, t: 'Robot plakaları', s: '→ SR5100 → B+', k: 'r' },
    { id: 'u1', c: 1, r: 1, t: 'U1 · NE555', s: '13 Hz çerçeve\n45 ms açık, 33 ms sus', k: 'e' },
    { id: 'u2', c: 2, r: 1, t: 'U2 · NE555', s: '1 kHz patlama\nRESET ← U1', k: 'e' },
    { id: 'u3', c: 3, r: 1, t: 'U3 · NE555', s: '38 kHz taşıyıcı\nRESET ← U2', k: 'e' },
    { id: 'led', c: 4, r: 1, t: 'BC337 + 2 IR LED', s: 'seri, 47 Ω, ~48 mA\n±20° açılı', k: 'e' },
    { id: 'eyes', c: 4, r: 2, t: 'Robot IR gözleri', s: 'VS1838B sol / sağ', k: 'r' },
  ],
  edges: [
    { from: 'ad', to: 'usb', k: 'p5', label: '5 V' },
    { from: 'usb', to: 'chg', k: 'p5', label: '≤ 3 A' },
    { from: 'chg', to: 'pogo', k: 'p12', label: '12,6 V' },
    { from: 'pogo', to: 'rob', k: 'chg', label: 'temas' },
    { from: 'usb', to: 'u1', k: 'p5', label: '~25 mA' },
    { from: 'u1', to: 'u2', k: 'ctl', label: 'RESET' },
    { from: 'u2', to: 'u3', k: 'ctl', label: 'RESET' },
    { from: 'u3', to: 'led', k: 'ctl', label: '38 kHz' },
    { from: 'led', to: 'eyes', k: 'ir', label: 'IR ışık' },
  ],
};

export const GLOVE_FLOW = {
  nodes: [
    { id: 'lipo', c: 0, r: 0, t: '1S LiPo', s: '3,7 V 1000 mAh', k: 'e' },
    { id: 'tp', c: 1, r: 0, t: 'TP4056 (korumalı)', s: 'Type-C ile şarj', k: 'e' },
    { id: 'sw', c: 2, r: 0, t: 'Sürgü anahtar', s: 'aç / kapa', k: 'e' },
    { id: 'c3', c: 3, r: 0, t: 'ESP32-C3 Mini', s: 'jest → komut', k: 'g' },
    { id: 'robot', c: 4, r: 0, t: 'Robot ESP32', s: '0,3 s komut yoksa dur', k: 'r' },
    { id: 'imu', c: 3, r: 1, t: 'MPU6050', s: 'el sırtında', k: 'g' },
  ],
  edges: [
    { from: 'lipo', to: 'tp', k: 'p5', label: 'B+ / B−' },
    { from: 'tp', to: 'sw', k: 'p5', label: 'OUT+' },
    { from: 'sw', to: 'c3', k: 'p5', label: '5V pini' },
    { from: 'c3', to: 'robot', k: 'rf', label: 'ESP-NOW' },
    { from: 'imu', to: 'c3', k: 'i2c', label: 'I2C' },
  ],
};

export const CONTROL_FLOW = {
  colW: 200,
  bw: 160,
  bh: 64,
  rowH: 100,
  nodes: [
    { id: 'ref', c: 0, r: 0, t: 'Hedef hız v_ref', s: 'eldiven komutu ya da\nyanaşma durumu', k: 'n' },
    { id: 'vpi', c: 1, r: 0, t: 'Hız PI · 50 Hz', s: 'çıktı: hedef eğim θ_ref\n±6° ile sınırlı', k: 'r' },
    { id: 'apd', c: 2, r: 0, t: 'Açı PD · 200 Hz', s: 'çıktı: ortak PWM u', k: 'r' },
    { id: 'mix', c: 3, r: 0, t: 'Karıştırıcı', s: 'sol = u − Δu\nsağ = u + Δu', k: 'r' },
    { id: 'drv', c: 4, r: 0, t: 'BTS7960 × 2', s: 'PWM 20 kHz\n→ motorlar', k: 'r' },
    { id: 'enc', c: 1, r: 1, t: 'Enkoder (PCNT)', s: 'teker hızı v, yol s', k: 'r' },
    { id: 'imu', c: 2, r: 1, t: 'MPU6050 + filtre', s: 'θ = 0,98(θ + ω·dt)\n   + 0,02·θ_ivme', k: 'r' },
    { id: 'ypd', c: 3, r: 1, t: 'Yön PD', s: 'çıktı: dönüş farkı Δu', k: 'r' },
    { id: 'yref', c: 3, r: 2, t: 'Hedef dönüş ψ̇_ref', s: 'sola / sağa: ±60°/s\nyanaşma: IR farkı', k: 'n' },
  ],
  edges: [
    { from: 'ref', to: 'vpi', k: 'ctl', label: 'v_ref' },
    { from: 'vpi', to: 'apd', k: 'ctl', label: 'θ_ref' },
    { from: 'apd', to: 'mix', k: 'ctl', label: 'u' },
    { from: 'mix', to: 'drv', k: 'pwm', label: 'PWM' },
    { from: 'enc', to: 'vpi', k: 'enc', label: 'v' },
    { from: 'imu', to: 'apd', k: 'i2c', label: 'θ, ω' },
    { from: 'imu', to: 'ypd', k: 'i2c', label: 'ω_z' },
    { from: 'ypd', to: 'mix', k: 'ctl', label: 'Δu' },
    { from: 'yref', to: 'ypd', k: 'ctl', label: 'ψ̇_ref' },
  ],
};

export const MODE_FLOW = {
  colW: 265,
  bw: 170,
  nodes: [
    { id: 'idle', c: 0, r: 0, t: 'DENGE', s: 'açılışta; yerinde\ndengede durur', k: 'r' },
    { id: 'drive', c: 1, r: 0, t: 'ELDİVEN SÜRÜŞÜ', s: '5 komut; 0,3 s paket\ngelmezse dur', k: 'g' },
    { id: 'dock', c: 2, r: 0, t: 'OTONOM YANAŞMA', s: 'eldiven yok sayılır', k: 'e' },
    { id: 'chg', c: 3, r: 0, t: 'ŞARJ', s: 'motorlar kapalı,\nsırta yaslı', k: 'e' },
    { id: 'fall', c: 1, r: 1, t: 'DÜŞTÜ / ACİL', s: '|θ| > 40° ya da acil\nstop: motorlar kapalı', k: 'b' },
  ],
  edges: [
    { from: 'idle', to: 'drive', k: 'ctl', label: 'eldiven komutu' },
    { from: 'drive', to: 'dock', k: 'ctl', label: 'dur + IR 1 s' },
    { from: 'dock', to: 'chg', k: 'ctl', label: 'plakada 12 V' },
    { from: 'drive', to: 'fall', k: 'ctl', label: 'her durumdan' },
  ],
};

export const DOCK_FLOW = {
  colW: 265,
  bw: 170,
  bh: 64,
  nodes: [
    { id: 'ara', c: 0, r: 0, t: '1 · ARA', s: 'yerinde yavaş döner\n30°/s', k: 'e' },
    { id: 'hiz', c: 1, r: 0, t: '2 · HİZALAN', s: 'e = (nL − nR) / (nL + nR)\nsola dön: ψ̇ = k·e', k: 'e' },
    { id: 'yak', c: 2, r: 0, t: '3 · YAKLAŞ', s: 'v = 0,08 m/s, dengede;\nhizalama sürer', k: 'e' },
    { id: 'yer', c: 3, r: 0, t: '4 · YERLEŞ', s: 'v = 0; 0,1 s sonra\nEN = 0, motorlar durur', k: 'e' },
    { id: 'srj', c: 4, r: 0, t: '5 · ŞARJ', s: 'robot sırta yaslanır;\ngösterge donanımdan', k: 'e' },
  ],
  edges: [
    { from: 'ara', to: 'hiz', k: 'ctl', label: 'bir göz görür' },
    { from: 'hiz', to: 'yak', k: 'ctl', label: '|e| < 0,15' },
    { from: 'yak', to: 'yer', k: 'ctl', label: 'şarj algılandı' },
    { from: 'yer', to: 'srj', k: 'ctl', label: 'motor kapalı' },
  ],
};

export const GESTURES = [
  ['İleri', 'Eli öne eğ: pitch > +25°', 'v_ref = +0,2 m/s. 0,5 m yaklaşık 2,5 s.'],
  ['Geri', 'Eli geriye eğ: pitch < −25°', 'v_ref = −0,2 m/s.'],
  ['Sola', 'Eli sola yatır: roll < −25°', 'Yerinde sola döner, 60°/s. 90° yaklaşık 1,5 s.'],
  ['Sağa', 'Eli sağa yatır: roll > +25°', 'Yerinde sağa döner, 60°/s.'],
  ['Dur', 'Eli düz tut: iki açı da ±12° içinde, 0,2 s', 'v_ref = 0, yön sabit; enkoderle olduğu yerde kalır.'],
];

export const TASK_LOGIC = [
  {
    id: 'Ö1',
    name: 'Denge ve hareket',
    board: 'Robot ESP32',
    loop: 'MPU6050 → tümleyen filtre → açı PD (200 Hz); enkoder → hız PI (50 Hz)',
    logic: 'İç döngü gövdeyi dik tutar. Dış döngü hız hedefinden hedef eğim üretir: öne gitmek için gövde hafifçe öne eğilir, tekerler altına koşar. 1 m’yi enkoder sayar; 3 s durmada v_ref = 0 ve konum tutulur.',
  },
  {
    id: 'Ö2',
    name: 'Eldivenle komut',
    board: 'Eldiven ESP32-C3 + robot ESP32',
    loop: 'Eldiven: pitch/roll eşik + histerezis → komut; robot: v_ref ya da ψ̇_ref',
    logic: 'Eldiven komutu 20 Hz tekrar yollar, sıra numarasıyla. Robot 0,3 s paket alamazsa kendini durdurur. Tepki 2 s sınırının çok altında kalır (yaklaşık 0,1 s).',
  },
  {
    id: 'Ö3',
    name: 'Otomatik şarj',
    board: 'Robot ESP32 (istasyonda yazılım yok)',
    loop: 'İki IR gözünün patlama sayısı farkı → yön PD; plaka gerilimi → durum makinesi',
    logic: 'ARA → HİZALAN → YAKLAŞ → YERLEŞ → ŞARJ. Plakada 12 V görülünce motorlar kapanır, robot sırta yaslanır. Gösterge istasyondaki şarj kartının CHG LED’i: robot çekilince akım kesilir, LED kendiliğinden söner.',
  },
  {
    id: 'Ö4',
    name: 'Mobil ölçüm',
    board: 'Robot ESP32 + telefon',
    loop: 'BLE bildirim 1 Hz: sıra no, zaman, pil %, pil V, eğim °, mod, şarj',
    logic: 'Pil yüzdesi gerilimden: 9,9 V ≈ %0, 12,6 V ≈ %100. Telefon görevi seçip robota yazar; hareket ve yönü kendi kamerasıyla ölçer, raporu kendisi kilitler.',
  },
  {
    id: 'Ö5',
    name: 'Bütünleşik görev',
    board: 'Hepsi',
    loop: 'Robot mod makinesi: DENGE → ELDİVEN SÜRÜŞÜ → OTONOM YANAŞMA → ŞARJ',
    logic: 'Yaklaşma bölgesine gelip “dur” denince robot iki gözüyle işareti 1 s görürse yanaşmaya kendisi geçer; bundan sonra eldiven yok sayılır. Ayrı bir “istasyona git” jesti yok.',
  },
];

export const WIRING_NOTES = [
  'Tüm GND’ler ortak: pil −, BMS P−, LM2596 −, ESP32 GND, BTS7960 GND, enkoder ve sensör GND.',
  'BTS7960 kartının VCC’si 3,3 V’a bağlanır. 5 V’ta kart üstündeki 74HC244 tamponu ESP32’nin 3,3 V sinyalini güvenle “1” görmeyebilir.',
  'Enkoderleri 3,3 V ile besleyin; çıkışları ESP32 için güvenli olur. Dahili pull-up’ı açın. 5 V verirseniz bölücü gerekir.',
  'GPIO4 enable hattına 10 kΩ GND direnci: açılışta motorlar kapalı kalır. GPIO14 açılışta kısa bir sinyal üretir; enable kapalıyken zararsız.',
  'Kullanmayın: GPIO0, 2, 5, 12, 15 açılış ayar pinleri; GPIO6–11 flash belleğe ait. GPIO34–39 yalnız giriştir, IR ve ölçüm için uygundur.',
  'Ölçüm pinleri (GPIO34, 35) ADC1’de. ADC2 pinleri Wi-Fi/BLE açıkken okunamaz.',
  'Bölücü 100 kΩ / 27 kΩ: 12,6 V → 2,68 V. ESP32 pinine 3,3 V’tan fazlası gelmez.',
  'Sağ motor ayna takılı olduğundan ileri giderken ters döner; yazılımda işareti çevrilir.',
  'Şarj diyotu 0,4 V düşürür, paket yaklaşık %90 dolar. Bu test için sorun değil.',
  'Motor ve güç hattında 18 AWG silikon kablo, sinyalde jumper. Motor kablolarını enkoder ve I2C kablosundan uzak tutun.',
  'Jumper uçları denge sırasındaki titreşimle gevşer. İlk denemeden sonra ESP32 tarafında sıcak silikonla sabitleyin ya da lehimleyin.',
  'Ölçüm pinlerinin (GPIO34, 35) yanına GND’ye 100 nF koyun; ADC okuması titremez.',
  'Kod yüklerken ana karttaki JP1 köprüsünü çıkarın. ESP32 kartında USB ile VIN arasında diyot yoksa iki 5 V kaynağı çakışır.',
];

export const FIRMWARE_NOTES = [
  ['Enkoder çözünürlüğü', '11 darbe × dişli oranı × 4 (A/B kenarları). 530 RPM motorda teker turu başına yaklaşık 800–850 sayım. Teker çevresi 65 mm × π ≈ 204 mm. Tekeri elle 10 tur çevirip gerçek sayıyı ölçün.'],
  ['Kütüphaneler', 'ESP32Encoder (PCNT), MPU6050 (Electronic Cats ya da jrowberg), esp_now (çekirdekte), NimBLE-Arduino. PWM için Arduino-ESP32 3.x ledcAttach.'],
  ['Döngü süresi', '200 Hz = 5 ms. I2C 400 kHz’te MPU6050 okuması 0,5 ms’nin altında. Döngüyü INT pininden ya da donanım zamanlayıcısından tetikleyin, delay() kullanmayın.'],
  ['Ayar sırası', 'Önce yalnız açı döngüsü: Kp’yi salınıma kadar artırın, Kd ile sönümleyin. Sonra hız döngüsü, en son yön döngüsü. Kazançları telefondan BLE ile değiştirin, her seferinde yeniden yüklemeyin.'],
  ['Ölü bölge', 'Motor küçük PWM’de dönmez. Sıfır olmayan çıktıya sabit bir başlangıç PWM’i ekleyin.'],
  ['IR sayımı', 'Alıcı çıkışının düşen kenarlarını kesmeyle sayın. İşaret 45 ms yayın yapıp 33 ms susar; 10 ms’den uzun sessizlik çerçeve sonudur. nL ve nR o çerçevenin sayısıdır, tam görüşte yaklaşık 44. Böylece yön bilgisi 13 Hz’de yenilenir.'],
  ['Güvenlik', '|θ| > 40° ise motorlar kapanır. Eldiven 0,3 s sessizse dur. Acil stop motor hattını donanımla keser; ESP32 açık kalır, telemetri sürer.'],
];
