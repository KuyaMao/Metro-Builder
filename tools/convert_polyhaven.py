"""Converts Poly Haven downloads (CC0) into Metro Builder textures.
usage: python tools/convert_polyhaven.py <folder with *_blend.zip / *.zip / *.exr> <out dir>
Writes ph_<slot>_{col,nrm,rgh}.jpg for surfaces, ph_fac_<kind>_{col,hgt}.jpg for facades and env_<slot>.bin for skies."""
import sys, os, io, zipfile, glob, numpy as np
from PIL import Image
import OpenEXR

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

# which download feeds which game surface. Each slot: (asset, size, target mean brightness or None, desaturate 0..1)
SURF = {  # slot: (asset, colour size, normal size, target mean brightness or None, desaturate 0..1)
    'road':  ('clean_asphalt', 2048, 2048, .80, .7),
    'walk':  ('brushed_concrete_04', 2048, 1024, .80, .6),
    'plaza': ('pavement_06', 1024, 1024, None, 0),
    'grass': ('rocky_terrain_02', 2048, 1024, None, 0),
    'grass2':('grass_ground', 1024, 512, None, 0),
    'sand':  ('coast_sand_01', 1024, 512, None, 0),
}
FAC = {  # facade backgrounds (multiplied by the building colour, so near-white and neutral), tiled into one 1024 square
    'res':   ('concrete_wall_009', .93, .85, 6),
    'glass': ('concrete_wall_007', .9, .85, 6),
    'ind':   ('corrugated_iron_02', .9, .9, 8),
}
SKY = {'day': ('kloppenheim_06_puresky', 2048), 'dusk': ('highway_bridge_sunset', 1024)}

def find_maps(asset):
    """returns dict kind->image bytes reader, from a zip or loose files"""
    for z in glob.glob(os.path.join(SRC, asset + '_*.zip')):
        zf = zipfile.ZipFile(z); m = {}
        for n in zf.namelist():
            b = os.path.basename(n)
            for k in ('diff', 'nor_gl', 'rough', 'disp', 'arm', 'ao'):
                if b.startswith(asset + '_' + k + '_'):
                    m[k] = (b, zf.read(n))
        return m
    return None

def load(name_bytes, gray=False):
    name, data = name_bytes
    if name.endswith('.exr'):
        f = OpenEXR.File(io.BytesIO(data)) if hasattr(OpenEXR.File, '__init__') else None
        ch = f.channels(); key = 'RGB' if 'RGB' in ch else 'RGBA' if 'RGBA' in ch else list(ch)[0]
        a = np.asarray(ch[key].pixels, dtype=np.float32)
        if a.ndim == 3: a = a[..., :3]
        if gray and a.ndim == 3: a = a.mean(-1)
        return np.clip(a, 0, 1)          # PH data maps in EXR are already 0..1 (linear data)
    im = Image.open(io.BytesIO(data))
    if im.mode.startswith('I'):      # 16-bit greyscale (height maps)
        a = np.asarray(im, dtype=np.float32) / 65535.
        return a if gray or a.ndim == 3 else np.repeat(a[..., None], 3, -1)
    return np.asarray(im.convert('L' if gray else 'RGB'), dtype=np.float32) / 255.

def resize(a, n):
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), 'F').resize((n, n), Image.LANCZOS))
    return np.stack([resize(a[..., i], n) for i in range(a.shape[-1])], -1)

def save(a, name, q=88):
    a = (np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)
    Image.fromarray(a).save(os.path.join(OUT, name + '.jpg'), quality=q, optimize=True, progressive=True)
    print(name, os.path.getsize(os.path.join(OUT, name + '.jpg')) // 1024, 'KB')

def srgb2lin(c): return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
def lin2srgb(c): return np.where(c <= .0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - .055)

def neutral(col, target, desat):
    """grey-balance and set the mean brightness so the game's own colours tint it (works in linear light)"""
    lin = srgb2lin(col)
    lum = lin @ np.array([.2126, .7152, .0722])
    lin = lin * (1 - desat) + lum[..., None] * desat
    lin = lin / lin.reshape(-1, 3).mean(0) * srgb2lin(np.array(target))   # per-channel balance to grey
    return lin2srgb(np.clip(lin, 0, 1))

def cavity(disp, n):
    """darkens crevices a little using the height map (cheap baked occlusion)"""
    d = resize(disp, n)
    from scipy.ndimage import gaussian_filter
    hp = d - gaussian_filter(d, n / 128, mode='wrap')
    return np.clip(1 + hp / (np.abs(hp).std() * 6 + 1e-6) * .18, .75, 1.08)

for slot, (asset, n, nn, target, desat) in SURF.items():
    m = find_maps(asset)
    if not m or 'diff' not in m:
        print('missing', asset); continue
    col = resize(load(m['diff']), n)
    if 'disp' in m: col = col * cavity(load(m['disp'], True), n)[..., None]
    if target:
        col = neutral(col, target, desat)
        mu = col.mean((0, 1)); col = mu + (col - mu) * 1.9   # the game sees these from far away: keep the grain readable
    save(col, f'ph_{slot}_col')
    if 'nor_gl' in m: save(resize(load(m['nor_gl']), nn), f'ph_{slot}_nrm', 90)
    if 'rough' in m: save(resize(load(m['rough'], True), n // 2), f'ph_{slot}_rgh')

for kind, (asset, target, desat, k) in FAC.items():
    m = find_maps(asset)
    if not m: print('missing', asset); continue
    t = -(-1024 // k)
    col = neutral(resize(load(m['diff']), t), target, desat)
    if 'disp' in m: h = resize(load(m['disp'], True), t)
    else: h = np.full((t, t), .5)
    h = .5 + (h - h.mean()) / (h.std() * 4 + 1e-6) * .25
    til = lambda a: np.tile(a, (k, k) + ((1,) if a.ndim == 3 else ()))[:1024, :1024]
    save(til(col), f'ph_fac_{kind}_col'); save(til(h), f'ph_fac_{kind}_hgt')

# skies: equirect HDR stored as RGBE in a PNG (rows top-down), decoded by the game into a float texture
for slot, (asset, W) in SKY.items():
    f = glob.glob(os.path.join(SRC, '*' + asset + '*.exr'))
    if not f: print('missing', asset); continue
    ch = OpenEXR.File(f[0]).channels(); key = 'RGB' if 'RGB' in ch else 'RGBA'
    a = np.asarray(ch[key].pixels, dtype=np.float32)[..., :3]
    a = np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(a[..., i]), 'F').resize((W, W // 2), Image.BOX)) for i in range(3)], -1)
    a = np.clip(a, 0, 1500)   # tame the sun disc: the game has its own sun light
    mx = a.max(-1); e = np.ceil(np.log2(np.maximum(mx, 1e-32))); sc = np.where(mx > 1e-32, 256. / np.exp2(e), 0)
    # RGB mantissa and the shared exponent in two PNGs (an alpha channel would be mangled by canvas premultiplication)
    Image.fromarray(np.clip(a * sc[..., None], 0, 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, f'env_{slot}_rgb.png'), optimize=True)
    Image.fromarray(np.where(mx > 1e-32, e + 128, 0).astype(np.uint8), 'L').save(os.path.join(OUT, f'env_{slot}_exp.png'), optimize=True)
    print('env', slot, (os.path.getsize(os.path.join(OUT, f'env_{slot}_rgb.png')) + os.path.getsize(os.path.join(OUT, f'env_{slot}_exp.png'))) // 1024, 'KB')
