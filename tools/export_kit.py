"""Export Kenney kit GLBs (single colormap atlas) to MODELPACK indexed groups.
usage: python3 -I export_kit.py -- <out.json> <prefix> <file.glb> ...
Each triangle's colour = colormap sampled at its UV centroid; vertices merged per colour group; ints = coords*1000"""
import bpy,sys,os,json
from PIL import Image
a=sys.argv[sys.argv.index('--')+1:];out,prefix,files=a[0],a[1],a[2:]
res={};cache={}
def img(m):
    if not m or not m.use_nodes:return None
    for n in m.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image:
            p=bpy.path.abspath(n.image.filepath)
            if p not in cache:
                try:cache[p]=Image.open(p).convert('RGB')
                except Exception:
                    im=n.image;W,H=im.size;px=im.pixels[:];pi=Image.new('RGB',(W,H))
                    pi.putdata([tuple(int(255*px[(y*W+x)*4+c]**(1/2.2)) for c in range(3)) for y in range(H-1,-1,-1) for x in range(W)]);cache[p]=pi
            return cache[p]
    return None
for f in files:
    name=prefix+os.path.splitext(os.path.basename(f))[0].replace('-','_').replace('building_','')
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=f)
    dg=bpy.context.evaluated_depsgraph_get();groups={}
    for o in [o for o in bpy.data.objects if o.type=='MESH']:
        oe=o.evaluated_get(dg);me=oe.to_mesh();me.transform(o.matrix_world);me.calc_loop_triangles()
        uv=me.uv_layers.active.data if me.uv_layers.active else None
        for lt in me.loop_triangles:
            m=me.materials[lt.material_index] if me.materials else None;pi=img(m)
            if pi and uv:
                W,H=pi.size;u=sum(uv[l].uv[0] for l in lt.loops)/3;v=sum(uv[l].uv[1] for l in lt.loops)/3
                c=pi.getpixel((min(W-1,max(0,int((u%1)*W))),min(H-1,max(0,int((1-(v%1))*H)))))
            elif m:
                bc=m.diffuse_color;c=tuple(int(255*x**(1/2.2)) for x in bc[:3])
            else:c=(180,180,180)
            q=lambda x:min(255,(x+2)//4*4);k='%02x%02x%02x'%(q(c[0]),q(c[1]),q(c[2]))
            g=groups.setdefault(k,{'v':{},'p':[],'i':[]})
            for l in lt.loops:
                co=me.vertices[me.loops[l].vertex_index].co;t=(round(co.x*1000),round(co.z*1000),round(-co.y*1000))
                if t not in g['v']:g['v'][t]=len(g['v']);g['p']+=t
                g['i'].append(g['v'][t])
        oe.to_mesh_clear()
    allp=[x for g in groups.values() for x in g['p']]
    b=[min(allp[0::3]),min(allp[1::3]),min(allp[2::3]),max(allp[0::3]),max(allp[1::3]),max(allp[2::3])]
    res[name]={'b':[x/1000 for x in b],'q':1,'g':[{'c':c,'p':g['p'],'i':g['i']} for c,g in groups.items()]}
    print(name,'tris',sum(len(g['i'])//3 for g in groups.values()),'groups',len(groups),'size',[(b[3]-b[0])/1000,(b[4]-b[1])/1000,(b[5]-b[2])/1000])
json.dump(res,open(out,'w'),separators=(',',':'))
