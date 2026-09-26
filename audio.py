"""Beat-synced soundtrack for the reel (120 BPM, stdlib only). Usage: python3 audio.py out.wav"""
import math
import random
import struct
import sys
import wave

SR = 44100
DUR = 15.0
N = int(SR * DUR)
BEAT = 0.5
TAU = math.tau
rng = random.Random(7)

L = [0.0] * N
R = [0.0] * N
SL = [0.0] * N  # reverb send
SR_ = [0.0] * N


def add(t0, samples, gain=1.0, pan=0.0, send=0.0):
    i0 = int(t0 * SR)
    gl, gr = gain * math.cos((pan + 1) * math.pi / 4) * 1.414, gain * math.sin((pan + 1) * math.pi / 4) * 1.414
    for k, v in enumerate(samples):
        i = i0 + k
        if 0 <= i < N:
            L[i] += v * gl
            R[i] += v * gr
            if send:
                SL[i] += v * gl * send
                SR_[i] += v * gr * send


def noise(n):
    return [rng.uniform(-1, 1) for _ in range(n)]


def onepole(x, a):
    y, out = 0.0, []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def hp(x, a):
    lo = onepole(x, a)
    return [v - l for v, l in zip(x, lo)]


# ---------------------------------------------------------------- instruments

def kick(amp=1.0, f0=160, f1=42, dec=7.0, n=0.45):
    out, ph = [], 0.0
    for k in range(int(n * SR)):
        t = k / SR
        f = f1 + (f0 - f1) * math.exp(-t * 28)
        ph += TAU * f / SR
        out.append(math.sin(ph) * math.exp(-t * dec) * amp + (0.4 * amp * math.exp(-t * 400) if k < 200 else 0))
    return out


def clap(amp=0.5):
    nz = hp(noise(int(0.22 * SR)), 0.25)
    out = []
    for k, v in enumerate(nz):
        t = k / SR
        env = sum(math.exp(-(t - d) * 90) for d in (0, 0.009, 0.018) if t >= d) * 0.5 + 0.5 * math.exp(-t * 16)
        out.append(v * env * amp)
    return out


def hat(amp=0.2, dec=70, n=0.06):
    nz = hp(hp(noise(int(n * SR)), 0.5), 0.5)
    return [v * math.exp(-k / SR * dec) * amp for k, v in enumerate(nz)]


def sine_blip(f, amp=0.2, dec=40, n=0.08, f_end=None):
    out, ph = [], 0.0
    for k in range(int(n * SR)):
        t = k / SR
        ff = f if f_end is None else f * (f_end / f) ** (t / n)
        ph += TAU * ff / SR
        out.append(math.sin(ph) * math.exp(-t * dec) * amp * min(1, k / 40))
    return out


def pluck(f, amp=0.25, dec=6.0, n=0.7):
    out, ph = [], 0.0
    for k in range(int(n * SR)):
        t = k / SR
        ph += TAU * f / SR
        v = math.sin(ph) + 0.5 * math.sin(2 * ph) * math.exp(-t * 20) + 0.25 * math.sin(3 * ph) * math.exp(-t * 30)
        out.append(v * math.exp(-t * dec) * amp * min(1, k / 30))
    return out


def impact(amp=0.9, n=1.6):
    boom = kick(amp, 120, 32, 2.6, n)
    nz = onepole(noise(int(n * SR)), 0.08)
    return [b + v * math.exp(-k / SR * 4.5) * amp * 1.6 for k, (b, v) in enumerate(zip(boom, nz))]


def whoosh(dur, amp=0.35):
    nz = noise(int(dur * SR))
    out, y = [], 0.0
    for k, v in enumerate(nz):
        p = k / len(nz)
        a = 0.01 + 0.5 * p ** 2.2
        y += a * (v - y)
        out.append(y * amp * p ** 1.6 * 2.2)
    return out


def riser(dur, f0, f1, amp=0.12):
    out, ph = [], 0.0
    for k in range(int(dur * SR)):
        p = k / (dur * SR)
        f = f0 * (f1 / f0) ** (p ** 1.5)
        ph += TAU * f / SR
        out.append((math.sin(ph) + 0.3 * math.sin(ph * 2.01)) * amp * p ** 1.5)
    return out


def bell(f, amp=0.3, n=2.5):
    out = []
    for k in range(int(n * SR)):
        t = k / SR
        v = sum(a * math.sin(TAU * f * m * t) * math.exp(-t * d) for m, a, d in
                ((1, 1, 1.6), (2.76, 0.5, 3.5), (5.4, 0.25, 7), (8.93, 0.12, 11)))
        out.append(v * amp * min(1, k / 60))
    return out


# ---------------------------------------------------------------- arrangement

A1, F1, C2, G1 = 55.0, 43.65, 65.41, 49.0
ROOTS = [A1, F1, C2, G1]
CHORDS = [[220.0, 261.63, 329.63, 493.88], [174.61, 220.0, 261.63, 392.0], [130.81, 196.0, 261.63, 329.63],
          [196.0, 246.94, 293.66, 392.0]]


def chord_at(t):
    return int(t / 2) % 4


kicks = []
# intro: dot pop, line zip, weight-ramp ticks, full stop pop
add(0.0, sine_blip(660, 0.35, 18, 0.25, 990), send=0.4)
add(0.28, riser(0.52, 300, 1400, 0.06), pan=-0.2, send=0.3)
for k in range(9):
    add(1.0 + k * 0.047, sine_blip(1200 + k * 180, 0.07, 90, 0.03), pan=(k - 4) / 6)
add(1.3, sine_blip(880, 0.28, 22, 0.2, 440), send=0.5)
for k, tt in enumerate((0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05)):
    add(tt, hat(0.05, 200, 0.02), pan=-0.5)
add(1.5, whoosh(0.5, 0.45), send=0.3)
add(0.0, kick(0.35, 90, 40, 9))
add(1.0, kick(0.35, 90, 40, 9))

# groove 2.0 -> 11.5
t = 2.0
while t < 11.5 - 1e-6:
    b = round((t - 2.0) / BEAT)
    half_time = 7.0 <= t < 9.5
    if not half_time or b % 2 == 0:
        add(t, kick(1.0))
        kicks.append(t)
    if b % 2 == 1:
        add(t, clap(0.42), send=0.35)
    for s in range(4):
        st = t + s * BEAT / 4
        if s == 2:
            add(st, hat(0.16, 45, 0.09), pan=0.3)
        elif (t >= 4.5 and s in (1, 3)) or t >= 9.5:
            add(st, hat(0.07, 90), pan=-0.3 if s == 1 else 0.4)
    root = ROOTS[chord_at(t)]
    for e in range(2):
        f = root * (2 if (b + e) % 4 == 3 else 1)
        add(t + e * BEAT / 2 + 0.01, pluck(f, 0.32, 9, 0.24), send=0.0)
    t += BEAT

# accents
for tt in (2.0, 4.5, 7.0, 9.5):
    add(tt, impact(0.75), send=0.5)
add(2.75, whoosh(0.25, 0.3), pan=0.4)
add(3.0, riser(0.48, 200, 800, 0.05), send=0.3)
for tt, f in ((3.5, 880), (3.75, 988), (4.0, 1046), (4.25, 1318)):
    add(tt, clap(0.35), send=0.4)
    add(tt, sine_blip(f, 0.12, 25, 0.2), send=0.6, pan=0.3)
for k, tt in enumerate((5.0, 5.5, 6.0, 6.5)):
    for j, f in enumerate(CHORDS[chord_at(tt)]):
        add(tt + j * 0.028, pluck(f * 2, 0.07, 7, 0.6), pan=(j - 1.5) / 2, send=0.6)
for k in range(12):
    add(5.5 + k * 1.0 / 12, sine_blip(2000, 0.02, 200, 0.015), pan=0.6)
add(6.6, whoosh(0.4, 0.55), send=0.3)
add(6.65, riser(0.35, 120, 900, 0.1))
for tt in (7.75, 8.55):
    add(tt, whoosh(0.35, 0.25), pan=-0.4, send=0.4)
add(9.05, riser(0.45, 150, 2400, 0.1), send=0.3)
add(9.1, whoosh(0.4, 0.5))
for tt in (10.0, 10.5, 11.0):
    add(tt - 0.02, whoosh(0.1, 0.35), pan=0.5)
    add(tt, kick(0.5, 200, 60, 12))
for k in range(8):
    add(11.0 + k * 0.0625, clap(0.12 + k * 0.03), pan=(k % 2 - 0.5) * 0.6, send=0.3)

# signature: silence swell, big hit, sustained chord, ticks, final ting
add(11.5, whoosh(0.5, 0.6), send=0.5)
add(11.5, riser(0.5, 90, 700, 0.12), send=0.3)
add(12.0, impact(1.0, 2.6), send=0.8)
add(12.0, kick(1.0, 170, 38, 3.0, 1.2))
add(12.0, whoosh(0.3, 0.2), pan=-0.6)
add(12.3, whoosh(0.5, 0.25), pan=0.6)
for j, f in enumerate((220.0, 329.63, 493.88, 659.25)):
    add(12.8 + j * 0.06, pluck(f, 0.08, 2.2, 2.0), pan=(j - 1.5) / 2, send=0.8)
for k in range(44):
    add(13.25 + k / 60, sine_blip(1800 + (k % 5) * 120, 0.018, 160, 0.02), pan=(k % 7 - 3) / 5)
add(14.0, bell(1318.5, 0.05, 1.5), send=0.8, pan=0.2)
add(14.3, whoosh(0.15, 0.2), pan=0.5)
add(14.45, whoosh(0.3, 0.3), pan=-0.5)
add(14.88, sine_blip(1320, 0.22, 34, 0.1, 660), send=0.9)
add(14.9, kick(0.6, 110, 36, 5, 0.6))

# pad (sidechained), silent during the 11.5 gap
ph = [0.0] * 4
lp_l = lp_r = 0.0
kick_idx = 0
for i in range(N):
    t = i / SR
    while kick_idx + 1 < len(kicks) and kicks[kick_idx + 1] <= t:
        kick_idx += 1
    duck = 1.0
    if kicks and t >= kicks[kick_idx]:
        duck = 1 - 0.7 * math.exp(-(t - kicks[kick_idx]) * 7)
    if t < 2:
        g = 0.05 * min(1, t / 1.2)
    elif t < 11.5:
        g = 0.07
    elif t < 12:
        g = 0.0
    else:
        g = 0.09 * math.exp(-max(0, t - 13.2) * 0.8)
    chord = CHORDS[0] if t >= 12 else CHORDS[chord_at(t)]
    vl = vr = 0.0
    for v in range(4):
        f = chord[v]
        ph[v] = (ph[v] + f * (1.003 if v % 2 else 0.997) / SR) % 1.0
        saw = 2 * ph[v] - 1
        if v % 2:
            vr += saw
        else:
            vl += saw
    lp_l += 0.035 * (vl - lp_l)
    lp_r += 0.035 * (vr - lp_r)
    L[i] += lp_l * g * duck
    R[i] += lp_r * g * duck
    SL[i] += lp_l * g * 0.3
    SR_[i] += lp_r * g * 0.3


# Schroeder reverb on the send bus
def reverb(x, combs, aps, fb=0.8, damp=0.3):
    out = [0.0] * len(x)
    for d in combs:
        buf, idx, lp = [0.0] * d, 0, 0.0
        for i, v in enumerate(x):
            y = buf[idx]
            lp = y * (1 - damp) + lp * damp
            buf[idx] = v + lp * fb
            idx = (idx + 1) % d
            out[i] += y
    for d in aps:
        buf, idx = [0.0] * d, 0
        for i, v in enumerate(out):
            y = buf[idx]
            buf[idx] = v + y * 0.5
            out[i] = y - v * 0.5
            idx = (idx + 1) % d
    return out


wl = reverb(SL, (1557, 1617, 1491, 1422), (225, 556))
wr = reverb(SR_, (1580, 1640, 1514, 1445), (248, 579))
fade = int(0.06 * SR)
peak = 0.0
mix = []
for i in range(N):
    g = min(1.0, (N - i) / fade)
    l = math.tanh((L[i] + wl[i] * 0.09) * 1.1) * g
    r = math.tanh((R[i] + wr[i] * 0.09) * 1.1) * g
    peak = max(peak, abs(l), abs(r))
    mix.append((l, r))
norm = 0.89 / peak
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "soundtrack.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b"".join(struct.pack("<hh", int(l * norm * 32767), int(r * norm * 32767)) for l, r in mix))
