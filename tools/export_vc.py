"""Export low-poly textured/material models to Metro Builder's MODELPACK format with per-group flat colours.
usage: python export_vc.py -- <out.json> <mode> <file> [<file> ...]
mode 'car': colours sampled from the palette texture per triangle, quantised; the body colour becomes class 'paint' (tintable)
mode 'bld': colours from each material (texture average or base colour); interior/fake-interior materials dropped"""
import bpy,sys,os,json,colorsys,math
from PIL import Image
a=sys.argv[sys.argv.index('--')+1:];out,mode,files=a[0],a[1],a[2:]
res={}
imgcache={}
def avgcol(im):
    p=bpy.path.abspath(im.filepath,library=im.library)
    if p not in imgcache:
        try:
            pi=Image.open(p).convert('RGB');imgcache[p]=(pi,pi.resize((1,1),Image.BOX).getpixel((0,0)))
        except Exception:
            px=list(im.pixels[:]);n=len(px)//4 or 1;imgcache[p]=(None,tuple(int(255*sum(px[i::4])/n) for i in range(3)))
    return imgcache[p]
def matinfo(m):
    if not m or not m.use_nodes:return None,(180,180,180)
    b=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not b:return None,(180,180,180)
    inp=b.inputs['Base Color'];st=[inp]
    while st:
        s=st.pop()
        for l in s.links:
            n=l.from_node
            if n.type=='TEX_IMAGE' and n.image:
                pi,c=avgcol(n.image);return pi,c
            st+=[i for i in n.inputs if i.is_linked]
    c=inp.default_value;g=lambda x:int(255*(x**(1/2.2)));return None,(g(c[0]),g(c[1]),g(c[2]))
for f in files:
    name=os.path.splitext(os.path.basename(f))[0].replace('-','_')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext=f.lower().rsplit('.',1)[1]
    if ext in('glb','gltf'):bpy.ops.import_scene.gltf(filepath=f)
    elif ext=='fbx':bpy.ops.import_scene.fbx(filepath=f)
    elif ext=='obj':bpy.ops.wm.obj_import(filepath=f)
    if mode=='bld':
        import bmesh
        for o in [o for o in bpy.data.objects if o.type=='MESH']:
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.01)
            bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(3),verts=bm.verts,edges=bm.edges,delimit={'MATERIAL'})
            small=[f for f in bm.faces if f.calc_area()<.03];bmesh.ops.delete(bm,geom=small,context='FACES')
            bm.to_mesh(o.data);bm.free()
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    tris=[]  # (col, area, verts)
    for o in [o for o in bpy.data.objects if o.type=='MESH']:
        oe=o.evaluated_get(dg);me=oe.to_mesh();me.transform(o.matrix_world);me.calc_loop_triangles()
        uv=me.uv_layers.active.data if me.uv_layers.active else None
        mi={}
        for lt in me.loop_triangles:
            m=me.materials[lt.material_index] if me.materials else None;mn=m.name if m else ''
            if mode=='bld' and any(k in mn for k in('Interior','FakeInterior')):continue
            if mn not in mi:mi[mn]=matinfo(m)
            pi,c=mi[mn]
            if mode=='car' and pi is not None and uv:
                W,H=pi.size;u=sum(uv[l].uv[0] for l in lt.loops)/3;v=sum(uv[l].uv[1] for l in lt.loops)/3
                c=pi.getpixel((min(W-1,max(0,int((u%1)*W))),min(H-1,max(0,int((1-(v%1))*H)))))
            if mode=='bld' and 'Glass' in mn:c=(52,62,74)
            if mode=='bld' and 'Asphalt' in mn:c=(78,80,84)
            vs=[me.vertices[me.loops[l].vertex_index].co for l in lt.loops]
            tris.append((tuple(c),lt.area,[(v.x,v.z,-v.y) for v in vs],mn))
        oe.to_mesh_clear()
    # body colour (cars): the most common saturated hue
    body=None
    if mode=='car':
        acc={}
        for c,ar,_,_ in tris:
            h,s,v=colorsys.rgb_to_hsv(*[x/255 for x in c])
            if s>.32 and v>.45:k=round(h*24)%24;acc[k]=acc.get(k,0)+ar
        if acc:body=max(acc,key=acc.get)
    groups={}
    for c,ar,vs,mn in tris:
        k='det';cc=c
        if body is not None:
            h,s,v=colorsys.rgb_to_hsv(*[x/255 for x in c])
            if s>.32 and v>.45 and min(abs(round(h*24)%24-body),24-abs(round(h*24)%24-body))<=1:
                k='paint';l=max(.45,min(1.1,v/.95));cc=(int(255*l),)*3
        q=lambda x:min(255,(x+4)//8*8)
        key=(k,'%02x%02x%02x'%(q(cc[0]),q(cc[1]),q(cc[2])))
        g=groups.setdefault(key,[])
        for p in vs:g+=[round(p[0],3),round(p[1],3),round(p[2],3)]
    allp=[x for g in groups.values() for x in g]
    b=[min(allp[0::3]),min(allp[1::3]),min(allp[2::3]),max(allp[0::3]),max(allp[1::3]),max(allp[2::3])]
    res[name]={'b':[round(x,3) for x in b],'g':[{'c':c,'k':k,'p':p} for (k,c),p in groups.items()]}
    print(name,'tris',len(tris),'groups',len(groups),'size',[round(b[3]-b[0],2),round(b[4]-b[1],2),round(b[5]-b[2],2)],'body',body)
json.dump(res,open(out,'w'),separators=(',',':'))
