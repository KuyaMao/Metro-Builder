"""Export vehicle models (glTF/FBX) to Metro Builder MODELPACK groups with classes for the car materials.
usage: python export_car.py -- <out.json> name=file[:fixed] ...
classes: paint (the body; luminance only so each car can be tinted, or original colour when :fixed), det, chrome, glass, head, tail.
Front is turned to +z (headlights ahead of tail lights)."""
import bpy,sys,os,json,colorsys,math
from PIL import Image
a=sys.argv[sys.argv.index('--')+1:];out=a[0];res={}
def tex_of(m):
    if not m or not m.use_nodes:return None
    b=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not b:return None
    st=[b.inputs['Base Color']]
    while st:
        s=st.pop()
        for l in s.links:
            n=l.from_node
            if n.type=='TEX_IMAGE' and n.image:
                im=n.image;W,H=im.size;px=list(im.pixels[:]);return (W,H,px)
            st+=[i for i in n.inputs if i.is_linked]
    return None
def base(m):
    if not m:return (.6,.6,.6)
    if m.use_nodes:
        b=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if b:c=b.inputs['Base Color'].default_value;return (c[0],c[1],c[2])
    c=m.diffuse_color;return (c[0],c[1],c[2])
g2s=lambda x:max(0,min(255,int(255*(max(0,x)**(1/2.2)))))
for spec in a[1:]:
    name,f=spec.split('=',1);allmetal=f.endswith(':allpaint');f=f[:-9] if allmetal else f;fixed=f.endswith(':fixed');f=f[:-6] if fixed else f
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if f.lower().endswith(('glb','gltf')):bpy.ops.import_scene.gltf(filepath=f)
    else:bpy.ops.import_scene.fbx(filepath=f)
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    tris=[];texc={}
    for o in [o for o in bpy.data.objects if o.type=='MESH']:
        oe=o.evaluated_get(dg);me=oe.to_mesh();me.transform(o.matrix_world);me.calc_loop_triangles()
        uv=me.uv_layers.active.data if me.uv_layers.active else None
        for lt in me.loop_triangles:
            m=me.materials[lt.material_index] if me.materials else None;mn=(m.name if m else '').lower()
            if mn not in texc:texc[mn]=tex_of(m)
            t=texc[mn]
            if t and uv:
                W,H,px=t;u=sum(uv[l].uv[0] for l in lt.loops)/3%1;v=sum(uv[l].uv[1] for l in lt.loops)/3%1
                i=(min(H-1,int(v*H))*W+min(W-1,int(u*W)))*4;c=(px[i],px[i+1],px[i+2])
            else:c=base(m)
            c=tuple(g2s(x) for x in c)
            vs=[me.vertices[me.loops[l].vertex_index].co for l in lt.loops]
            tris.append([c,lt.area,[(p.x,p.z,-p.y) for p in vs],mn])
        oe.to_mesh_clear()
    # classify
    def cls(c,mn):
        if 'glass' in mn or 'window' in mn:return 'glass'
        if 'rear' in mn and 'light' in mn:return 'tail'
        if 'light' in mn:
            h,s,v=colorsys.rgb_to_hsv(*[x/255 for x in c]);return 'tail' if (s>.4 and (h<.06 or h>.9)) else 'head'
        if mn=='wheels':return 'chrome'
        if 'texture' in mn:
            h,s,v=colorsys.rgb_to_hsv(*[x/255 for x in c])
            if s>.5 and v>.35 and (h<.04 or h>.94):return 'tail'
        return None
    # body: largest-area colour among 'texture' / 'body*' materials
    acc={}
    for c,ar,vs,mn in tris:
        if cls(c,mn) is None and (mn.startswith('metallic') or mn.startswith('body')) and sum(c)/3>35:
            k=mn;acc[k]=acc.get(k,0)+ar
    bk=max(acc,key=acc.get) if acc else None
    bodyc=None
    for t in tris:
        c,ar,vs,mn=t;k=cls(c,mn)
        if k is None:
            isb=bk is not None and (mn==bk or (allmetal and mn.startswith('metallic')))
            k='paint' if isb else 'det'
            if isb and bodyc is None:bodyc=c
        t.append(k)
    nh=sum(1 for t in tris if t[4]=='head')
    if nh>.15*len(tris):
        for t in tris:
            if t[4]=='head':t[4]='det'
    # front = side with headlights
    hz=[sum(p[2] for p in t[2])/3 for t in tris if t[4]=='head'];tz=[sum(p[2] for p in t[2])/3 for t in tris if t[4]=='tail']
    flip=bool(hz and tz and sum(hz)/len(hz)<sum(tz)/len(tz))
    Lz=max(abs(p[2]) for t in tris for p in t[2])
    for t in tris:
        if t[4]=='head':
            z=sum(p[2] for p in t[2])/3*(-1 if flip else 1)
            if z<-.3*Lz:t[4]='tail'
    groups={}
    bl=max(1,max(bodyc) if bodyc else 1)
    for c,ar,vs,mn,k in tris:
        cc=c
        if k=='paint' and not fixed:l=max(.55,min(1.0,(sum(c)/3)/max(1,sum(bodyc)/3)*.92)) if bodyc else .9;cc=(int(255*l),)*3
        q=lambda x:min(255,(x+4)//8*8);key=(k,'%02x%02x%02x'%(q(cc[0]),q(cc[1]),q(cc[2])))
        g=groups.setdefault(key,[])
        for p in vs:x,y,z=p;x,z=(-x,-z) if flip else (x,z);g+=[round(x,3),round(y,3),round(z,3)]
    allp=[x for g in groups.values() for x in g]
    b=[min(allp[0::3]),min(allp[1::3]),min(allp[2::3]),max(allp[0::3]),max(allp[1::3]),max(allp[2::3])]
    res[name]={'b':[round(x,3) for x in b],'g':[{'c':c,'k':k,'p':p} for (k,c),p in groups.items()]}
    cnt={};[cnt.__setitem__(t[4],cnt.get(t[4],0)+1) for t in tris]
    print(name,'tris',len(tris),'classes',cnt,'flip',flip,'size',[round(b[3]-b[0],2),round(b[4]-b[1],2),round(b[5]-b[2],2)],'body',bk)
json.dump(res,open(out,'w'),separators=(',',':'))
