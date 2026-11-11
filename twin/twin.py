"""MuJoCo dijital ikizi.

C++ simulasyonundan (sim/plant.h) bagimsiz ikinci bir model:
  * Govde tools/mass_budget.py'deki her parcadan ayri kutu olarak kurulur (kutle, konum, atalet MuJoCo hesaplar).
  * Teker-zemin temasi, kayma, ilac kutusunun cepte durmasi, V-yuvanin direge oturmasi gercek temasla cozulur.
  * Sensorler fiziksel kurallarla uretilir: MPU6050 (X ileri, Y sol, Z yukari) MuJoCo'nun ivme/jiroskop
    sensorunden; enkoder teker ile govde arasindaki BAGIL acidan (gercek enkoder gibi).
  * Karar mantigi: robot firmware'indeki RobotLogic, build/twin_bridge.exe uzerinden (ayni C++ kodu).
Calistir:  <venv>/python twin/twin.py   ->  twin/results/*.csv ve summary.tsv
"""
import math
import pathlib
import subprocess
import sys

import mujoco
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mass_budget  # noqa: E402

OUT = ROOT / "twin/results"
OUT.mkdir(parents=True, exist_ok=True)
BRIDGE = ROOT / "build/twin_bridge.exe"

# ---- fiziksel parametreler (lqr_design.py ile ayni kaynaklar; motor degerleri veri sayfasi tahmini) ----
R_WHEEL, TRACK = 0.0325, 0.27
KE, RA = 0.216, 4.5
J_ROTOR, GEAR = 5.0e-7, 19.0
B_VISC, TAU_C = 0.002, 0.02
CPR = 836
VOC, RINT = 12.0, 0.15
MAGNET_N, MAGNET_RANGE = 10.0, 0.006  # V-yuvadaki miknatis ile direkteki celik serit: temasta ~10 N, 6 mm'de sifir
KX, KY = 0.016, 0.027  # ilac kutusu cebinin konumu (on, sol)
PHYS_DT, CTRL_EVERY = 0.0005, 10  # 2 kHz fizik, 200 Hz kontrol
TASKS = {"statik": 0, "yonlendirme": 1, "sarj": 2, "butunlesik": 3}
CMD = {"yok": 0, "ileri": 1, "geri": 2, "sol": 3, "sag": 4, "dur": 5}

# parca boyutlari (yari olcu, m) mass_budget isimlerine gore
SIZES = {
    "Kat": (0.055, 0.075, 0.002),
    "BTS": (0.025, 0.030, 0.015),
    "3x18650": (0.035, 0.040, 0.012),
    "Ana kart": (0.025, 0.050, 0.008),
    "Acil": (0.020, 0.020, 0.020),
    "Kutu yuvasi": (0.038, 0.025, 0.003),
    "LM2596": (0.020, 0.030, 0.010),
    "MPU": (0.010, 0.010, 0.002),
    "IR": (0.008, 0.020, 0.010),
    "16x": (0.050, 0.070, 0.004),
}


def size_for(name):
    for k, v in SIZES.items():
        if name.startswith(k):
            return v
    return (0.02, 0.02, 0.02)


def build_xml(post_xy=None, box=True):
    geoms = []
    for name, m, z, x, _ in mass_budget.PARTS:
        if name.startswith("2x JGB37"):
            # iki motor teker ekseninde, y boyunca
            for s in (1, -1):
                geoms.append(f'<geom type="cylinder" size="0.0185 0.035" pos="0 {s*0.045} -0.007" euler="90 0 0" mass="{m/2}" rgba=".3 .5 .5 1"/>')
            continue
        sx, sy, sz = size_for(name)
        # yalniz katlar carpisir (yere dusme, direk); diger parcalar kutle/atalet tasir, kutu cebine girmez
        coll = "" if name.startswith("Kat") else ' contype="0" conaffinity="0"'
        geoms.append(f'<geom type="box" size="{sx} {sy} {sz}" pos="{x} 0 {z}" mass="{m}" rgba=".6 .7 .8 1"{coll}/>')
    # kutu cebi (kat 3 ustunde, 4 duvar, kutle kutu yuvasi parcasinda sayildi)
    pocket = []
    # cad/robot_cad.py ile ayni: kat 3 ustu z=0.194, cep ici 72x47 mm, merkez y=+0.027 (sagda acil stop)
    zc = 0.194 + 0.0125
    for px, py, hx, hy in ((KX + 0.0372, KY, 0.0012, 0.0259), (KX - 0.0372, KY, 0.0012, 0.0259),
                           (KX, KY + 0.0247, 0.0384, 0.0012), (KX, KY - 0.0247, 0.0384, 0.0012)):
        pocket.append(f'<geom type="box" size="{hx} {hy} 0.0125" pos="{px} {py} {zc}" mass="0.0001" rgba=".8 .8 .9 .5"/>')
    # V-yuva (belgedeki gibi): arkada 20 mm genis dikey serit (pimler burada, x=0.058), iki yanda 45 derece kanat
    vee = ['<geom type="box" size="0.0015 0.010 0.025" pos="0.0575 0 0.06" mass="0.0001" rgba=".2 .3 .9 1"/>']
    for s_ in (1, -1):
        # kanat (0.058, +-0.010) noktasindan 45 derece disa, 42 mm
        cx, cy = 0.058 + 0.0148, s_ * (0.010 + 0.0148)
        vee.append(f'<geom type="box" size="0.021 0.0015 0.025" pos="{cx} {cy} 0.06" euler="0 0 {s_*45}" mass="0.0001" rgba=".2 .3 .9 1"/>')
    post = ""
    if post_xy is not None:
        post = (f'<body name="post" pos="{post_xy[0]} {post_xy[1]} 0.1"><geom type="cylinder" size="0.02 0.1" '
                f'rgba=".5 .5 .5 1"/></body>')
    box_body = ""
    if box:
        box_body = (f'<body name="pillbox" pos="{KX} {KY} {R_WHEEL + zc + 0.001}"><freejoint/>'
                    f'<geom type="box" size="0.035 0.0225 0.0125" mass="0.06" rgba=".9 .3 .3 1" friction="0.6 0.005 0.0001"/></body>')
    arm = J_ROTOR * GEAR**2
    xml = f"""
<mujoco model="cdtp_twin">
  <option timestep="{PHYS_DT}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <default><geom friction="1.0 0.01 0.001" condim="3"/></default>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1" rgba=".9 .9 .9 1"/>
    {post}
    <body name="chassis" pos="0 0 {R_WHEEL}">
      <freejoint name="root"/>
      {''.join(geoms)}
      {''.join(pocket)}
      {''.join(vee)}
      <site name="imu" pos="0 0 0.030"/>
      <site name="pin" pos="0.062 0 0.07"/>
      <body name="wheel_L" pos="0 {TRACK/2} 0">
        <joint name="wl" type="hinge" axis="0 1 0" armature="{arm}" damping="{B_VISC}" frictionloss="{TAU_C}"/>
        <geom type="cylinder" size="{R_WHEEL} 0.0125" euler="90 0 0" mass="0.07" rgba=".1 .1 .1 1"/>
      </body>
      <body name="wheel_R" pos="0 {-TRACK/2} 0">
        <joint name="wr" type="hinge" axis="0 1 0" armature="{arm}" damping="{B_VISC}" frictionloss="{TAU_C}"/>
        <geom type="cylinder" size="{R_WHEEL} 0.0125" euler="90 0 0" mass="0.07" rgba=".1 .1 .1 1"/>
      </body>
    </body>
    {box_body}
  </worldbody>
  <actuator>
    <motor name="ml" joint="wl" gear="1" ctrllimited="false"/>
    <motor name="mr" joint="wr" gear="1" ctrllimited="false"/>
  </actuator>
  <sensor>
    <accelerometer name="acc" site="imu"/>
    <gyro name="gyro" site="imu"/>
  </sensor>
</mujoco>"""
    return xml


class Twin:
    def __init__(self, x=0.0, y=0.0, yaw=0.0, post=None, task="statik", seed=1, box=True, bridge=True):
        self.m = mujoco.MjModel.from_xml_string(build_xml(post, box))
        self.d = mujoco.MjData(self.m)
        self.rng = np.random.default_rng(seed)
        self.post = post
        self.task = TASKS[task]
        q = self.d.qpos
        q[0:3] = [x, y, R_WHEEL]
        q[3:7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        if box:
            bj = self.m.joint(self.m.body("pillbox").jntadr[0])
            a = bj.qposadr[0]
            q[a:a + 3] = [x + KX * math.cos(yaw) - KY * math.sin(yaw), y + KX * math.sin(yaw) + KY * math.cos(yaw), q[a + 2]]
            q[a + 3:a + 7] = q[3:7]
            self.box_adr = a
        self.has_box = box
        self.jl, self.jr = self.m.joint("wl"), self.m.joint("wr")
        mujoco.mj_forward(self.m, self.d)
        self.t = 0.0
        self.duty = (0.0, 0.0)
        self.en = False
        self.mode, self.dock, self.theta_logic = 0, 0, 0.0
        self.filt = None
        self.ir = [0, 0]
        self.frame, self.burst = 0, 0
        self.glove = []        # [(t, cmd)]
        self.glove_next = 0.0
        self.motor_power = True
        self.hold = True       # elle dik tutuluyor
        self.magnet = True     # V-yuva miknatisi
        self.vbat = VOC
        self.trace = []
        self.proc = subprocess.Popen([str(BRIDGE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                     bufsize=1) if bridge else None

    # ---- durum ----
    def rot(self):
        return self.d.xmat[self.m.body("chassis").id].reshape(3, 3)

    def pitch(self):
        R = self.rot()
        zb, xb = R[:, 2], R[:, 0]
        h = np.array([xb[0], xb[1], 0.0])
        h /= np.linalg.norm(h) + 1e-12
        return math.atan2(zb @ h, zb[2])

    def yaw(self):
        R = self.rot()
        return math.atan2(R[1, 0], R[0, 0])

    def pos(self):
        return self.d.qpos[0], self.d.qpos[1]

    def fwd_dist(self, x0, y0, yaw0):
        x, y = self.pos()
        return (x - x0) * math.cos(yaw0) + (y - y0) * math.sin(yaw0)

    def charging(self):
        if self.post is None:
            return False
        p = self.d.site("pin").xpos
        dist = math.hypot(p[0] - self.post[0], p[1] - self.post[1])
        return dist < 0.02 + 0.0015  # pim ucu seritten 3 mm disarida, yay yolu ~1,5 mm

    def box_ok(self):
        if not self.has_box:
            return True
        bp = self.d.qpos[self.box_adr:self.box_adr + 3]
        cid = self.m.body("chassis").id
        local = self.rot().T @ (bp - self.d.xpos[cid])
        return abs(local[0] - KX) < 0.03 and abs(local[1] - KY) < 0.03 and local[2] > 0.18

    # ---- sensorler ----
    def sensors(self):
        acc = self.d.sensor("acc").data.copy()
        gyro = self.d.sensor("gyro").data.copy()
        i_mot = abs(self.cur[0]) + abs(self.cur[1]) if hasattr(self, "cur") else 0
        vib = 0.3 * (0.3 + i_mot / 2) if self.en else 0
        acc += self.rng.normal(0, 0.03 + vib, 3)
        gyro += self.rng.normal(0, math.radians(0.05), 3)
        a = 1 - math.exp(-2 * math.pi * 42 / 200)  # MPU6050 DLPF
        raw = np.concatenate([acc, gyro])
        self.filt = raw if self.filt is None else self.filt + a * (raw - self.filt)
        return self.filt

    def enc(self):
        # gercek enkoder: teker ile govde (motor) arasindaki bagil aci
        mpc = 2 * math.pi / CPR
        cl = math.floor(self.d.qpos[self.jl.qposadr[0]] / mpc)
        cr = math.floor(self.d.qpos[self.jr.qposadr[0]] / mpc)
        return cl, -cr  # sag enkoder ayna takili

    def eye_gain(self, eye):
        if self.post is None:
            return 0.0
        R = self.rot()
        cid = self.m.body("chassis").id
        front = self.d.xpos[cid] + R @ np.array([0.06, 0, 0])
        dx, dy = self.post[0] - front[0], self.post[1] - front[1]
        dist = math.hypot(dx, dy)
        if dist > 1.2 or dist < 0.01:
            return 0.0
        gamma = math.atan2(-dy, -dx)  # direk normaline (+X) gore robotun acisi
        emit = max(0.0, 1 - (gamma / math.radians(70)) ** 2)
        bearing = math.atan2(dy, dx) - self.yaw()
        bearing = (bearing + math.pi) % (2 * math.pi) - math.pi
        axis = math.radians(15 if eye == 0 else -15)
        acc = max(0.0, 1 - ((bearing - axis) / math.radians(30)) ** 2)
        g = emit * acc
        return 0.0 if g < 0.12 else min(1.0, 1.4 * g)

    def beacon(self):
        # 78 ms cerceve: ilk 45 ms'de 1,012 ms arayla 44 patlama, sonra 33 ms sessizlik (tamsayi sayacla)
        while True:
            tb = self.frame * 0.078 + self.burst * 0.0010122
            if tb > self.t:
                return
            for e in (0, 1):
                if self.rng.random() < self.eye_gain(e):
                    self.ir[e] += 1
            self.burst += 1
            if self.burst >= 44:
                self.burst = 0
                self.frame += 1

    def glove_cmd(self):
        c = "dur"
        for t, cmd in self.glove:
            if t <= self.t:
                c = cmd
        return CMD[c]

    # ---- adim ----
    def control(self):
        s = self.sensors()
        el, er = self.enc()
        gnew = 0
        if self.glove and self.t >= self.glove_next:
            self.glove_next = self.t + 0.05
            gnew = 1 if self.rng.random() > 0.05 else 0
        vchg = 12.4 if self.charging() else 0.0
        line = (f"{self.t:.4f} {s[0]:.5f} {s[1]:.5f} {s[2]:.5f} {s[3]:.6f} {s[4]:.6f} {s[5]:.6f} {el} {er} "
                f"{self.vbat:.3f} {vchg:.2f} {self.ir[0]} {self.ir[1]} {int(self.motor_power)} {gnew} {self.glove_cmd()} {self.task}\n")
        self.proc.stdin.write(line)
        out = self.proc.stdout.readline().split()
        self.en = out[0] == "1"
        dl, dr = float(out[1]), float(out[2])
        self.duty = (round(dl * 1023) / 1023, -round(dr * 1023) / 1023)  # sag motor ayna
        self.mode, self.dock, self.theta_logic = int(out[3]), int(out[4]), float(out[5])

    def physics(self):
        # DC motor: tork = Ke*(V - Ke*w)/R ; kuru/viskoz surtunme eklem parametrelerinde
        wl = self.d.qvel[self.jl.dofadr[0]]
        wr = self.d.qvel[self.jr.dofadr[0]]
        on = self.en and self.motor_power
        il = (self.duty[0] * self.vbat - KE * wl) / RA if on else 0.0
        ir = (self.duty[1] * self.vbat - KE * wr) / RA if on else 0.0
        self.cur = (il, ir)
        self.vbat = VOC - RINT * (abs(il) + abs(ir))
        self.d.ctrl[0] = KE * il
        self.d.ctrl[1] = KE * ir
        self.d.qfrc_applied[:] = 0
        if self.post is not None and self.magnet:
            p = self.d.site("pin").xpos
            dx, dy = self.post[0] - p[0], self.post[1] - p[1]
            dist = math.hypot(dx, dy)
            gap = dist - 0.02
            if gap < MAGNET_RANGE and dist > 1e-6:
                f = MAGNET_N * (1 - max(gap, 0) / MAGNET_RANGE)
                force = np.array([dx / dist * f, dy / dist * f, 0.0])
                mujoco.mj_applyFT(self.m, self.d, force, np.zeros(3), p, self.m.body("chassis").id, self.d.qfrc_applied)
        if self.hold:  # elle dik tutma: govdeyi dik ve hareketsiz tut
            yaw = self.yaw()
            self.d.qpos[3:7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
            self.d.qvel[0:6] = 0
        mujoco.mj_step(self.m, self.d)
        self.t += PHYS_DT
        self.beacon()

    def run(self, dur, each=None):
        n = int(round(dur / PHYS_DT))
        for i in range(n):
            if i % CTRL_EVERY == 0:
                self.control()
                if self.hold and self.mode == 1:  # DENGE'ye girdi: birak
                    self.hold = False
                x, y = self.pos()
                self.trace.append((self.t, x, y, math.degrees(self.pitch()), math.degrees(self.yaw()), self.duty[0],
                                   self.duty[1], self.mode, self.dock))
                if each:
                    each(self)
            self.physics()

    def arm(self):
        self.run(1.0)

    def tilt(self, deg):
        # govdeyi teker ekseni etrafinda egerek birak (elle egip birakma)
        R = self.rot()
        yb = R[:, 1]
        q = np.zeros(4)
        mujoco.mju_axisAngle2Quat(q, yb, math.radians(deg))
        q0 = self.d.qpos[3:7].copy()
        qn = np.zeros(4)
        mujoco.mju_mulQuat(qn, q, q0)
        cid = self.m.body("chassis").id
        axle = self.d.xpos[cid].copy()
        if self.has_box:  # kutu govdeyle birlikte egilir (elde tutulan robot)
            a = self.box_adr
            Rq = np.zeros(9)
            mujoco.mju_quat2Mat(Rq, q)
            rel = self.d.qpos[a:a + 3] - axle
            self.d.qpos[a:a + 3] = axle + Rq.reshape(3, 3) @ rel
            qb = np.zeros(4)
            mujoco.mju_mulQuat(qb, q, self.d.qpos[a + 3:a + 7].copy())
            self.d.qpos[a + 3:a + 7] = qb
            self.d.qvel[6:12] = 0
        self.d.qpos[3:7] = qn
        self.d.qpos[0:3] = axle
        self.d.qvel[0:6] = 0
        mujoco.mj_forward(self.m, self.d)

    def lying(self):
        return abs(self.pitch()) > math.radians(40)  # govde ~45-50 derecede plakayla yere degiyor

    def close(self):
        if self.proc:
            self.proc.stdin.write("quit\n")
            self.proc.stdin.close()
            self.proc.wait()

    def csv(self, name):
        with open(OUT / name, "w", encoding="utf-8") as f:
            f.write("t,x,y,theta_deg,yaw_deg,dutyL,dutyR,mode,dock\n")
            for r in self.trace:
                f.write(",".join(f"{v:.5f}" if isinstance(v, float) else str(v) for v in r) + "\n")


# ======================= senaryolar =======================
RESULTS = []


def report(tid, name, ok, detail):
    RESULTS.append((tid, name, "GECTI" if ok else "KALDI", detail))
    print(f"[{'GECTI' if ok else 'KALDI'}] {tid:7s} {name:44s} {detail}", flush=True)


class Watch:
    def __init__(self):
        self.max_th, self.fell, self.box = 0.0, False, True

    def __call__(self, tw):
        if not tw.hold:
            self.max_th = max(self.max_th, abs(tw.pitch()))
        self.fell |= tw.lying() or tw.mode == 4
        self.box &= tw.box_ok()


def t_passive():
    worst = 0.0
    ok = True
    for deg in (10, -10):
        tw = Twin(bridge=False)
        tw.hold = False
        tw.tilt(deg)
        t = 0.0
        while t < 5 and not tw.lying():
            mujoco.mj_step(tw.m, tw.d)
            t += PHYS_DT
        ok &= t < 5
        worst = max(worst, t)
    report("ON", "Enerjisiz +-10 deg'den dik kalmamali", ok, f"40 deg'ye en gec {worst:.2f} s'de dustu")


def t_static():
    tw = Twin(task="statik", seed=1)
    tw.arm()
    w = Watch()
    x0, y0 = tw.pos()
    maxd = [0.0]

    def each(t):
        w(t)
        maxd[0] = max(maxd[0], math.hypot(t.pos()[0] - x0, t.pos()[1] - y0))
    tw.run(30, each)
    tw.csv("ikiz_statik.csv")
    tw.close()
    ok = not w.fell and w.box and w.max_th < math.radians(5) and maxd[0] < 0.15
    report("C1.1", "30 s statik denge (kutulu)", ok,
           f"en buyuk egim {math.degrees(w.max_th):.2f} deg, kayma {maxd[0]*100:.1f} cm, kutu {'yerinde' if w.box else 'DUSTU'}")


def t_move(forward=True):
    c = "ileri" if forward else "geri"
    tw = Twin(task="yonlendirme", seed=2 if forward else 3)
    tw.glove = [(0, "dur"), (6.0, c), (6.4, "dur"), (9.5, c), (9.9, "dur")]
    tw.arm()
    w = Watch()
    tw.run(4.9, w)  # 5 s dengede bekleme
    yaw0 = tw.yaw()
    x0, y0 = tw.pos()
    tw.run(8.1, w)  # C++ testiyle ayni: durma penceresi t=14 s'de baslar
    d0 = tw.fwd_dist(x0, y0, yaw0)
    maxdx = [0.0]

    def each(t):
        w(t)
        maxdx[0] = max(maxdx[0], abs(t.fwd_dist(x0, y0, yaw0) - d0))
    tw.run(3.0, each)
    d = abs(tw.fwd_dist(x0, y0, yaw0))
    tw.csv("ikiz_ileri.csv" if forward else "ikiz_geri.csv")
    tw.close()
    ok = not w.fell and w.box and 0.9 < d < 1.1 and maxdx[0] < 0.03
    report("C1.2" if forward else "C1.3", f"1 m {c} + 3 s dur", ok,
           f"yol {d:.3f} m, 3 s durmada kayma {maxdx[0]*1000:.1f} mm, egim tepe {math.degrees(w.max_th):.1f} deg, kutu {'yerinde' if w.box else 'DUSTU'}")


def t_recovery():
    res = []
    for deg in (10, -10):
        tw = Twin(task="statik", seed=4)
        tw.arm()
        tw.tilt(deg)
        t0 = tw.t
        rec = [None]
        after = [0.0]
        w = Watch()

        # toparlanma: |theta| < 3 deg ve |v| < 0,1 m/s'ye ilk varis; sonrasinda egim 5 deg'yi hic asmamali (C++ testiyle ayni olcut)
        def each(t):
            w(t)
            th = abs(t.pitch())
            v = np.linalg.norm(t.d.qvel[0:2])
            if rec[0] is None and th < math.radians(3) and v < 0.1:
                rec[0] = t.t - t0
            if rec[0] is not None:
                after[0] = max(after[0], th)
        tw.run(10, each)
        if after[0] > math.radians(5):
            rec[0] = None
        tw.close()
        res.append((deg, rec[0], w.fell, w.box))
    ok = all(r[1] is not None and r[1] < 10 and not r[2] and r[3] for r in res)
    report("C1.4", "+10 ve -10 deg'den 10 s icinde toparlanma", ok,
           ", ".join(f"{r[0]:+d}: {r[1]:.2f} s" if r[1] is not None else f"{r[0]:+d}: TOPARLANMADI" for r in res))


def t_turn():
    out = []
    for c, sgn in (("sol", 1), ("sag", -1)):
        tw = Twin(task="yonlendirme", seed=5)
        tw.glove = [(0, "dur"), (1.5, c), (1.9, "dur")]
        tw.arm()
        y0 = tw.yaw()
        w = Watch()
        tw.run(5, w)
        dy = math.degrees((tw.yaw() - y0 + math.pi) % (2 * math.pi) - math.pi)
        tw.close()
        out.append((c, dy, not w.fell and w.box and abs(dy - 90 * sgn) < 15))
    report("C2.3-4", "Eldiven: sola / saga ~90 deg", all(o[2] for o in out),
           ", ".join(f"{o[0]} {o[1]:+.1f} deg" for o in out))


def t_estop():
    tw = Twin(task="statik", seed=6)
    tw.arm()
    tw.motor_power = False
    tw.run(0.05)
    ok = tw.mode == 0 and not tw.en
    tw.close()
    report("GUV.2", "Acil stop: denge birakilir, motorlar kapanir", ok, f"mod={['BEKLE','DENGE','YANASMA','SARJ','DUSTU'][tw.mode]}")


def dock_once(rho, alpha_deg, head_deg, seed, record=False):
    # direk dunya orijininde; yaklasma bolgesi direk normali (+X) etrafinda
    a = math.radians(alpha_deg)
    x, y = rho * math.cos(a), rho * math.sin(a)
    yaw = math.atan2(-y, -x) + math.radians(head_deg)
    tw = Twin(x=x, y=y, yaw=yaw, post=(0.0, 0.0), task="sarj", seed=seed)
    tw.arm()
    t0 = tw.t
    w = Watch()
    st = {"contact": None, "charge": None}

    def each(t):
        w(t)
        if st["contact"] is None and t.charging():
            st["contact"] = t.t
        if st["charge"] is None and t.mode == 3:
            st["charge"] = t.t
    tw.run(45, each)
    if record:
        tw.csv("ikiz_yanasma.csv")
    tw.close()
    ok = st["charge"] is not None and tw.charging() and not w.box is False
    return ok, (st["contact"] - t0) if st["contact"] else None, (st["charge"] - st["contact"]) if st["charge"] and st["contact"] else None


def t_dock():
    cases = [(r, a, h) for r in (0.18, 0.30) for a in (-45, -20, 0, 20, 45) for h in (-25, 0, 25)]
    good, worst, wc = 0, 0.0, 0.0
    fails = []
    for i, (r, a, h) in enumerate(cases):
        ok, tc, tchg = dock_once(r, a, h, 100 + i, record=(i == len(cases) - 2))
        if ok:
            good += 1
            worst = max(worst, tc)
            wc = max(wc, tchg)
        else:
            fails.append(f"({r:.2f} m, {a} deg, bakis {h:+d})")
    report("C3", f"IR ile yanasma, V-yuva + direk ({len(cases)} baslangic)", good == len(cases),
           f"{good}/{len(cases)} basarili, en uzun temas {worst:.1f} s, temas->sarj modu {wc:.2f} s " + " ".join(fails))


def t_undock():
    """Sarjdayken eldivenle 'geri': robot miknatistan kopup dengeye girer ve 0,5 m geri gider."""
    tw = Twin(x=0.25, y=0.0, yaw=math.pi, post=(0.0, 0.0), task="sarj", seed=8)
    tw.arm()
    tw.run(15)
    docked = tw.mode == 3 and tw.charging()
    tw.glove = [(0, "dur"), (tw.t + 0.5, "geri"), (tw.t + 0.9, "dur")]
    w = Watch()
    tw.run(8, w)
    p = tw.d.site("pin").xpos
    gap = math.hypot(p[0], p[1]) - 0.02
    ok = docked and tw.mode == 1 and gap > 0.25 and not w.fell
    tw.close()
    report("C3.5", "Eldivenle 'geri': miknatistan kopup istasyondan ayrilir", ok,
           f"once {'SARJ' if docked else 'sarjda degil'}, sonra mod {['BEKLE','DENGE','YANASMA','SARJ','DUSTU'][tw.mode]}, direge uzaklik {gap*100:.0f} cm")


def t_integrated():
    # direk (0,0); robot (0.27,-1.0)'dan +Y'ye bakarak baslar: 2 x ileri, 5 s bekle, sola don, otonom yanasma
    tw = Twin(x=0.27, y=-1.0, yaw=math.pi / 2, post=(0.0, 0.0), task="butunlesik", seed=7)
    tw.glove = [(0, "dur"), (5.0, "ileri"), (5.4, "dur"), (8.6, "ileri"), (9.0, "dur"), (17.0, "sol"), (17.4, "dur")]
    tw.arm()
    w = Watch()
    early = [False]

    def each(t):
        w(t)
        if t.t < 17 and t.mode == 2:
            early[0] = True
    tw.run(60, each)
    tw.csv("ikiz_butunlesik.csv")
    ok = tw.mode == 3 and tw.charging() and not early[0] and w.box
    tw.close()
    report("C5", "Butunlesik gorev (kutu, eldiven, yanasma)", ok,
           f"son mod {['BEKLE','DENGE','YANASMA','SARJ','DUSTU'][tw.mode]}, erken yanasma {'VAR' if early[0] else 'yok'}, kutu {'yerinde' if w.box else 'DUSTU'}")


def t_reference_gains():
    """GitHub: suelioalencar/Two-Wheels-Inverted-Pendulum... gercek robotta calisan LQI kazanclari
    (k1 = [-100.5, -69.9, -83.6, -9.31] V, 65 mm teker, enkoderli DC motor). Bu kazanclari ikizde, kendi
    durum olcumleriyle (dogrudan fizikten) kosup modelin gercekci bir bolgede oldugunu kontrol eder."""
    K = np.array([-100.493, -69.900, -83.636, -9.314])
    res = []
    for deg in (0, 8):
        tw = Twin(task="statik", seed=9, bridge=False)
        tw.hold = False
        tw.en = True
        if deg:
            tw.tilt(deg)
        x0 = tw.d.qpos[0]
        ok = True
        prev = tw.pitch()
        for i in range(int(8 / PHYS_DT)):
            if i % CTRL_EVERY == 0:
                th = tw.pitch()
                om = tw.d.sensor("gyro").data[1]
                wl = tw.d.qpos[tw.jl.qposadr[0]]
                wr = tw.d.qpos[tw.jr.qposadr[0]]
                x = R_WHEEL * ((wl + wr) / 2 + th) - 0  # teker yolu
                v = R_WHEEL * ((tw.d.qvel[tw.jl.dofadr[0]] + tw.d.qvel[tw.jr.dofadr[0]]) / 2 + om)
                u = -(K @ np.array([x, v, th, om]))
                u = max(-11.0, min(11.0, u))
                tw.duty = (u / tw.vbat, u / tw.vbat)
            tw.physics()
            if tw.lying():
                ok = False
                break
        res.append((deg, ok, math.degrees(tw.pitch())))
    report("REF", "GitHub referans LQI kazanclari ikizde dengeliyor", all(r[1] for r in res),
           ", ".join(f"baslangic {r[0]} deg: {'dengede' if r[1] else 'DUSTU'} (son {r[2]:+.1f} deg)" for r in res))


if __name__ == "__main__":
    which = sys.argv[1:] or ["passive", "static", "move", "recovery", "turn", "estop", "ref", "dock", "undock", "integrated"]
    if "passive" in which: t_passive()
    if "static" in which: t_static()
    if "move" in which: t_move(True); t_move(False)
    if "recovery" in which: t_recovery()
    if "turn" in which: t_turn()
    if "estop" in which: t_estop()
    if "ref" in which: t_reference_gains()
    if "dock" in which: t_dock()
    if "undock" in which: t_undock()
    if "integrated" in which: t_integrated()
    with open(OUT / "summary.tsv", "w", encoding="utf-8") as f:
        for r in RESULTS:
            f.write("\t".join(r) + "\n")
    n = sum(r[2] == "GECTI" for r in RESULTS)
    print(f"\nIKIZ OZET: {n}/{len(RESULTS)} gecti")
