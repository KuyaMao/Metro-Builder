"""Packs game/tex/*.jpg|png into game/texpack.js (data URLs, so the game stays a single offline file).
Procedural textures that a Poly Haven texture replaces are left out."""
import base64, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
src = root / 'game/tex'
have = {f.stem for f in src.iterdir()}
REPLACED = {'asphalt_': 'ph_road_col', 'paving_': 'ph_walk_col', 'grass_': 'ph_grass_col', 'sand_': 'ph_sand_col',
            'fac_res_': 'ph_fac_res_col', 'fac_glass_': 'ph_fac_glass_col', 'fac_ind_': 'ph_fac_ind_col'}
items = []
for f in sorted(list(src.glob('*.jpg')) + list(src.glob('*.png'))):
    if any(f.stem.startswith(p) and r in have for p, r in REPLACED.items()):
        continue
    mime = 'image/png' if f.suffix == '.png' else 'image/jpeg'
    items.append(f'"{f.stem}":"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"')
(root / 'game/texpack.js').write_text('/* Metro Builder textures: original procedural ones (tools/gen_textures.py) and CC0 ones from Poly Haven (tools/convert_polyhaven.py) */\nwindow.TEXPACK={' + ',\n'.join(items) + '};\n')
print('texpack', (root / 'game/texpack.js').stat().st_size // 1024, 'KB,', len(items), 'textures')
