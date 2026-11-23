"""Generates Metro Builder's material textures (all original, procedural, tileable).
Output: <out>/<name>.jpg  (colour maps sRGB, data maps linear)."""
import sys, os, numpy as np
from PIL import Image
rng = np.random.default_rng(7)
OUT = sys.argv[1] if len(sys.argv) > 1 else 'tex'
os.makedirs(OUT, exist_ok=True)

def pnoise(n, beta, seed=None):
    """periodic fractal noise via spectral synthesis (tileable), normalised 0..1"""
    r = np.random.default_rng(seed) if seed is not None else rng
    f = np.fft.fftfreq(n)[:, None]**2 + np.fft.fftfreq(n)[None, :]**2
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j*r.normal(size=(n, n))) / f**(beta/2)
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec))
    a -= a.min(); a /= a.max()
    return a

def band(n, lo, hi, beta, seed=None):
    """noise limited to a frequency band (cycles per tile)"""
    r = np.random.default_rng(seed) if seed is not None else rng
    fx = np.fft.fftfreq(n)*n
    f = np.sqrt(fx[:, None]**2 + fx[None, :]**2)
    m = (f >= lo) & (f <= hi)
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j*r.normal(size=(n, n))) * m / f**(beta/2)
    a = np.real(np.fft.ifft2(spec)); a -= a.min(); a /= (a.max() or 1)
    return a

def normal_from_height(h, strength):
    dx = (np.roll(h, 1, 1) - np.roll(h, -1, 1)) * strength
    dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * strength
    l = np.sqrt(dx*dx + dy*dy + 1)
    n = np.stack([dx/l, -dy/l, 1/l], -1)  # OpenGL convention (green up)
    return ((n*.5+.5)*255).clip(0, 255).astype(np.uint8)

def save(name, a, q=88):
    if a.ndim == 2:
        a = (a.clip(0, 1)*255).astype(np.uint8)
    elif a.dtype != np.uint8:
        a = (a.clip(0, 1)*255).astype(np.uint8)
    Image.fromarray(a).save(os.path.join(OUT, name + '.jpg'), quality=q, optimize=True, progressive=True)
    print(name, os.path.getsize(os.path.join(OUT, name + '.jpg'))//1024, 'KB')

def stamp_cracks(h, n, count, depth, rr):
    """random-walk cracks carved into height h (wrapping)"""
    for _ in range(count):
        x, y = rr.uniform(0, n, 2); ang = rr.uniform(0, 6.28)
        for _ in range(int(rr.uniform(60, 220))):
            ang += rr.normal(0, .35); x = (x + np.cos(ang)*1.6) % n; y = (y + np.sin(ang)*1.6) % n
            h[int(y), int(x)] -= depth
            h[int(y), int((x+1) % n)] -= depth*.5
            if rr.random() < .03:  # branch
                bx, by, ba = x, y, ang + rr.choice([-1, 1])*rr.uniform(.6, 1.2)
                for _ in range(int(rr.uniform(10, 50))):
                    ba += rr.normal(0, .4); bx = (bx+np.cos(ba)*1.5) % n; by = (by+np.sin(ba)*1.5) % n
                    h[int(by), int(bx)] -= depth*.7

# ---------- asphalt (neutral; road vertex colours give the tone) ----------
def asphalt(n=1024):
    rr = np.random.default_rng(11)
    grain = rr.random((n, n))
    stones = (grain > .93).astype(float)*rr.uniform(.3, 1, (n, n))
    fine = band(n, 120, 512, 0, 12)
    macro = pnoise(n, 3.2, 13)
    mid = band(n, 8, 40, 1.5, 14)
    h = .45*fine + .9*stones + .25*mid
    stamp_cracks(h, n, 14, .9, rr)
    alb = .80 + .10*(fine-.5) + .14*(macro-.5) + .06*(mid-.5) + .10*stones*(rr.random((n, n)) - .3)
    # sealed crack lines and darker repair patches
    crack = (h < .05).astype(float)
    alb -= crack*.18
    for _ in range(2):
        cx, cy = rr.integers(0, n, 2); w, hh = rr.integers(90, 220, 2)
        ys = (np.arange(cy, cy+hh) % n)[:, None]; xs = (np.arange(cx, cx+w) % n)[None, :]
        alb[ys, xs] -= .02 + rr.random()*.015
    # oil stains
    for _ in range(9):
        cx, cy = rr.integers(0, n, 2); r = rr.uniform(14, 46)
        yy, xx = np.ogrid[:n, :n]
        d = np.minimum(abs(xx-cx), n-abs(xx-cx))**2 + np.minimum(abs(yy-cy), n-abs(yy-cy))**2
        alb -= .09*np.exp(-d/(r*r))*(.6+.4*fine)
    rough = .88 + .07*(fine-.5) - .12*np.clip(macro-.6, 0, 1) - crack*.2
    col = np.stack([alb, alb, alb*1.01], -1)
    save('asphalt_col', col); save('asphalt_nrm', normal_from_height(h, 2.4)); save('asphalt_rgh', rough)

# ---------- concrete paving slabs (sidewalks, plazas) ----------
def paving(n=1024):
    rr = np.random.default_rng(21)
    k = 4; s = n//k
    fine = band(n, 100, 512, 0, 22); macro = pnoise(n, 3, 23); mid = band(n, 6, 30, 1.2, 24)
    alb = .86 + .05*(fine-.5) + .08*(macro-.5) + .04*(mid-.5)
    h = .3*fine + .2*mid
    yy, xx = np.mgrid[:n, :n]
    for j in range(k):
        for i in range(k):
            tone = rr.normal(0, .025)
            alb[j*s:(j+1)*s, i*s:(i+1)*s] += tone
    gx = np.minimum(xx % s, s - xx % s); gy = np.minimum(yy % s, s - yy % s); g = np.minimum(gx, gy)
    joint = np.clip(1 - g/3.0, 0, 1)
    bevel = np.clip(1 - g/9.0, 0, 1)
    h = h - joint*1.2 - bevel*.25
    alb = alb - joint*.22 - bevel*.03
    stamp_cracks(h, n, 4, .6, rr)
    alb -= (h < -.2).astype(float)*.05
    # gum spots
    for _ in range(40):
        cx, cy = rr.integers(0, n, 2); alb[cy:cy+4, cx:cx+4] -= .12
    rough = .9 + .05*(fine-.5) + joint*.05
    col = np.stack([alb*1.0, alb*.985, alb*.96], -1)
    save('paving_col', col); save('paving_nrm', normal_from_height(h, 3.0)); save('paving_rgh', rough)

# ---------- grass / meadow (real colours) ----------
def grass(n=1024):
    rr = np.random.default_rng(31)
    macro = pnoise(n, 3.4, 32); mid = band(n, 10, 60, 1.0, 33); fine = band(n, 150, 512, 0, 34)
    blades = np.zeros((n, n))
    for _ in range(160000):
        x, y = rr.integers(0, n, 2); L = rr.integers(3, 9); dx = rr.normal(0, .35)
        v = rr.uniform(.4, 1)
        for t in range(L):
            blades[(y - t) % n, int(x + dx*t) % n] = max(blades[(y - t) % n, int(x + dx*t) % n], v*(1 - t/(L+1)*.4))
    h = .7*blades + .3*fine + .3*mid
    # colour: green-yellow hue variation, darker shadows between blades
    g0 = np.array([.30, .42, .17]); g1 = np.array([.44, .52, .22]); g2 = np.array([.24, .36, .14]); dry = np.array([.55, .52, .30])
    m = macro[..., None]; md = mid[..., None]
    col = g0*(1-m) + g1*m
    col = col*(1-.35*md) + g2*.35*md
    dryness = np.clip((pnoise(n, 3.0, 35)-.62)*3, 0, 1)[..., None]
    col = col*(1-.6*dryness) + dry*.6*dryness
    col *= (.62 + .5*blades[..., None])
    soil = np.clip((pnoise(n, 2.6, 36)-.8)*5, 0, 1)[..., None]*np.clip(1-blades[..., None]*1.4, 0, 1)
    col = col*(1-soil) + np.array([.33, .27, .19])*soil
    # sRGB-ish brighten
    col = np.clip(col, 0, 1)**(1/1.15)
    save('grass_col', col); save('grass_nrm', normal_from_height(h, 2.0))

# ---------- sand ----------
def sand(n=512):
    fine = band(n, 80, 256, 0, 41); rip = pnoise(n, 3.6, 42); mid = band(n, 6, 30, 1, 43)
    yy, xx = np.mgrid[:n, :n]
    ripples = np.sin((xx*2*np.pi/n)*18 + rip*14)*.5+.5
    h = .5*fine + .35*ripples + .3*mid
    a = .84 + .06*(fine-.5) + .06*(mid-.5)
    col = np.stack([a*.93, a*.84, a*.66], -1)
    save('sand_col', col); save('sand_nrm', normal_from_height(h, 1.6))

# ---------- sea surface normal (tileable waves) ----------
def waves(n=512):
    h = pnoise(n, 3.0, 51)*.6 + band(n, 10, 60, 1.5, 52)*.5 + band(n, 40, 160, 0.8, 53)*.15
    save('water_nrm', normal_from_height(h, 6.0))

# ---------- facade backgrounds (behind the procedural window grid, 1024 tile = 8 floors × 8 bays) ----------
def facades(n=1024):
    rr = np.random.default_rng(61)
    # stucco / render: soft grain, faint trowel marks, rain streaks under every window row
    fine = band(n, 150, 512, 0, 62); mid = band(n, 20, 90, 1, 63); macro = pnoise(n, 3, 64)
    yy, xx = np.mgrid[:n, :n]
    streak = np.zeros((n, n))
    for _ in range(140):
        x = rr.integers(0, n); y0 = rr.integers(0, n); L = rr.integers(30, 160); w = rr.integers(2, 7)
        for t in range(L):
            streak[(y0+t) % n, x:x+w] += (1 - t/L)*.6
    a = .93 + .035*(fine-.5) + .04*(mid-.5) + .04*(macro-.5) - .05*np.clip(streak, 0, 1)
    h = .5*fine + .4*mid
    save('fac_res_col', np.stack([a, a*.99, a*.97], -1)); save('fac_res_hgt', .5 + .25*(h-.5))
    # brick (very light, so building colour tints it)
    bh, bw = 10, 30
    row = yy//bh; off = (row % 2)*(bw//2)
    bx = (xx + off) % bw; by = yy % bh
    mortar = ((bx < 3) | (by < 3)).astype(float)
    brick_id = ((xx + off)//bw) + row*97
    tone = (np.sin(brick_id*12.9898)*43758.5453) % 1
    a = .86 + .09*(tone-.5) + .04*(fine-.5) + .03*(macro-.5) - mortar*.12
    h2 = .62 - mortar*.4 + .15*(fine-.5)
    save('fac_brick_col', np.stack([a, a*.97, a*.95], -1)); save('fac_brick_hgt', h2)
    # industrial corrugated cladding
    ridge = (np.sin(xx*2*np.pi/8)*.5+.5)
    a = .9 + .05*(ridge-.5) + .03*(fine-.5) + .05*(macro-.5) - .06*np.clip(streak*1.4, 0, 1)
    save('fac_ind_col', np.stack([a, a, a*1.005], -1)); save('fac_ind_hgt', .5 + .35*(ridge-.5) + .05*(fine-.5))
    # glass curtain wall: subtle per-panel tint variation (window drawing stays in the game)
    a = .88 + .04*(macro-.5) + .015*(fine-.5)
    save('fac_glass_col', np.stack([a*.97, a, a*1.02], -1))

# ---------- roofs: gravel / membrane ----------
def roof(n=512):
    rr = np.random.default_rng(71)
    g = rr.random((n, n)); fine = band(n, 60, 256, 0, 72); macro = pnoise(n, 3, 73)
    h = .6*fine + .4*(g > .6)*g
    a = .78 + .12*(fine-.5) + .08*(macro-.5) + .08*(g-.5)
    save('roof_col', np.stack([a, a, a*.98], -1)); save('roof_nrm', normal_from_height(h, 1.8))

for f in (asphalt, paving, grass, sand, waves, facades, roof):
    f()
