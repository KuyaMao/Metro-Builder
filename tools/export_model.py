"""Exports Poly Haven .blend models into Metro Builder's compact model format (run with the bpy module).
usage: python export_model.py -- <file.blend> <out.json> <name regex> <max triangles> [texture size]
Output JSON: {groups:[{mat, tex(base name), pos[], nrm[], uv[], idx[]}], bounds}. Positions are Y-up metres."""
import bpy, bmesh, sys, re, json, math, os
from PIL import Image
a = sys.argv[sys.argv.index('--') + 1:]
blend, out, rx, maxtri = a[0], a[1], re.compile(a[2]), int(a[3]); texsz = int(a[4]) if len(a) > 4 else 512
bpy.ops.wm.open_mainfile(filepath=blend)
objs = [o for o in bpy.data.objects if o.type == 'MESH' and rx.fullmatch(o.name)]
print('objects', len(objs))
dg = bpy.context.evaluated_depsgraph_get()
# merge into one bmesh per material, in world space
per = {}
tot = 0; small = set()
for o in objs:
    me = o.evaluated_get(dg).to_mesh(); me.transform(o.matrix_world)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:])
    nf = len(bm.faces); bm.free(); o.evaluated_get(dg).to_mesh_clear()
    if nf < 600: small.add(o.name); maxtri -= nf
    else: tot += nf
ratio = min(1, max(50, maxtri) / max(1, tot))   # small parts keep their shape, big ones are decimated
print('triangles', tot, 'ratio', ratio)
groups = {}
for o in objs:
    if ratio < 1 and o.name not in small:
        m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = ratio; m.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg); me = oe.to_mesh(); me.transform(o.matrix_world)
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data if me.uv_layers.active else None
    try: cn = me.corner_normals
    except AttributeError: cn = None
    for lt in me.loop_triangles:
        mat = me.materials[lt.material_index].name if me.materials and me.materials[lt.material_index] else 'none'
        g = groups.setdefault(mat, {'pos': [], 'nrm': [], 'uv': []})
        for li in lt.loops[::-1] if False else lt.loops:
            v = me.vertices[me.loops[li].vertex_index].co
            n = cn[li].vector if cn is not None else me.loops[li].normal
            g['pos'] += [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]
            nl = math.sqrt(n.x * n.x + n.y * n.y + n.z * n.z)
            g['nrm'] += [round(n.x / nl, 3), round(n.z / nl, 3), round(-n.y / nl, 3)] if nl > 1e-4 else [0, 1, 0]
            uv = uvl[li].uv if uvl else (0, 0)
            g['uv'] += [round(uv[0], 4), round(uv[1], 4)]
    oe.to_mesh_clear()
# textures: base colour image of each material, resized
res = {'groups': []}
os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
for mat, g in groups.items():
    m = bpy.data.materials.get(mat); tex = None; metal = 0; rough = .8; colhex = '808080'
    if m and m.use_nodes:
        bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        def img_of(inp):
            stack = [inp]
            while stack:
                s = stack.pop()
                for l in s.links:
                    n = l.from_node
                    if n.type == 'TEX_IMAGE' and n.image: return n.image
                    stack += [i for i in n.inputs if i.is_linked]
            return None
        if bsdf:
            im = img_of(bsdf.inputs['Base Color'])
            if im:
                p = bpy.path.abspath(im.filepath, library=im.library); p = os.path.normpath(p)
                if not os.path.exists(p): p = os.path.join(os.path.dirname(blend), 'textures', os.path.basename(p))
                pim = Image.open(p).convert('RGBA' if 'leaves' in mat else 'RGB')
                if 'leaves' in mat:   # alpha from the separate alpha map
                    ap = p.replace('_diff_', '_alpha_')
                    if os.path.exists(ap): pim.putalpha(Image.open(ap).convert('L'))
                pim = pim.resize((texsz, texsz), Image.LANCZOS)
                tex = os.path.splitext(os.path.basename(out))[0] + '_' + re.sub(r'\W', '', mat) + ('.png' if pim.mode == 'RGBA' else '.jpg')
                pim.save(os.path.join(os.path.dirname(out) or '.', tex), quality=85)
                rgb = pim.convert('RGB').resize((1, 1), Image.BOX).getpixel((0, 0)); colhex = '%02x%02x%02x' % rgb
            if not bsdf.inputs['Metallic'].is_linked: metal = bsdf.inputs['Metallic'].default_value
            if not bsdf.inputs['Roughness'].is_linked: rough = bsdf.inputs['Roughness'].default_value
    res['groups'].append({'mat': mat, 'tex': tex, 'col': colhex, 'metal': round(metal, 2), 'rough': round(rough, 2), **g})
    print('group', mat, len(g['pos']) // 9, 'triangles', tex)
allp = [c for g in res['groups'] for c in g['pos']]
res['bounds'] = [min(allp[0::3]), min(allp[1::3]), min(allp[2::3]), max(allp[0::3]), max(allp[1::3]), max(allp[2::3])]
json.dump(res, open(out, 'w'), separators=(',', ':'))
print('bounds', res['bounds'], os.path.getsize(out) // 1024, 'KB')
