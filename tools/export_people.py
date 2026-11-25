# Export Quaternius Ultimate Modular Men/Women (CC0) as segment-skinned people for Metro Builder.
# usage: python3 -I export_people.py <blend> <prefix> <out.json> Name1 Name2 ...
# Each character: arms posed down, decimated, vertices with up to two rig segments + weight,
# per-vertex colour class (0 fixed, 1 skin, 2 hair, 3 top, 4 bottom, 6 darker skin), joint pivots.
import bpy,sys,json,math,base64,struct
from mathutils import Matrix,Vector,Quaternion
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,prefix,out=args[0],args[1],args[2];names=args[3:]
bpy.ops.wm.open_mainfile(filepath=blend)
def unhide(lc):
    lc.exclude=False;lc.hide_viewport=False;lc.collection.hide_viewport=False
    for c in lc.children:unhide(c)
unhide(bpy.context.view_layer.layer_collection)
for o in bpy.data.objects:
    o.hide_viewport=False
    try:o.hide_set(False)
    except Exception:pass
arm=bpy.data.objects['CharacterArmature']
if arm.animation_data:arm.animation_data.action=None
for pb in arm.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(1,0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
def pose_world(bn,R):
    b=arm.data.bones[bn];B=b.matrix_local.to_3x3()
    arm.pose.bones[bn].rotation_quaternion=(B.inverted()@R@B).to_quaternion()
AB=math.radians(84)
pose_world('UpperArm.L',Matrix.Rotation(AB,3,'Y'));pose_world('UpperArm.R',Matrix.Rotation(-AB,3,'Y'))
# relax the hands a little (fingers curl is tiny at this size, skip)
bpy.context.view_layer.update()
S=.0733
def g(v):return (v.x*S, v.z*S, -v.y*S)
def gn(n):return (n.x, n.z, -n.y)
SEG={'Root':0,'Body':0,'Hips':0,'Abdomen':1,'Torso':1,'Chest':1,'Neck':1,'Head':1,'Shoulder.L':1,'Shoulder.R':1,
     'UpperLeg.L':2,'LowerLeg.L':3,'Foot.L':4,'UpperLeg.R':5,'LowerLeg.R':6,'Foot.R':7,'UpperArm.L':8,'UpperArm.R':10}
def segof(n):
    if n in SEG:return SEG[n]
    if n.endswith('.L'):return 9
    if n.endswith('.R'):return 11
    return None
pb=arm.pose.bones
J={'hip':g(pb['UpperLeg.L'].head),'knee':g(pb['LowerLeg.L'].head),'ank':g(pb['Foot.L'].head),'sh':g(pb['UpperArm.L'].head),'el':g(pb['LowerArm.L'].head),'ty':pb['Abdomen'].head.z*S}
TRI={'Head':420,'Body':380,'Legs':170,'Pants':170,'Feet':90}
def lin(m):
    try:
        n=m.node_tree.nodes.get('Principled BSDF');return list(n.inputs[0].default_value[:3])
    except Exception:return list(m.diffuse_color[:3])
def mcls(name,kind=''):
    if kind=='Head' and name in('Brown','DarkBrown','Brown2'):return 2
    if name=='Skin':return 1
    if name=='Skin_Darker':return 6
    if name.startswith('Hair') or name in('Eyebrows','Moustache'):return 2
    return 0
res={}
dg=None
for nm in names:
    parts=[o for o in bpy.data.objects if o.type=='MESH' and (o.name.split('_')[0] in (nm,) or (nm=='Formal' and o.name=='Formad_Head')) and o.name.split('_',1)[-1] in TRI]
    V=[];I=[];vmap={};pal=[];palk={};mins=[9]*3;maxs=[-9]*3;rest_tris=0
    for o in parts:
        kind=o.name.split('_',1)[1]
        mod=o.modifiers.new('dec','DECIMATE');
        nf=len(o.data.polygons)*1.9;mod.ratio=min(1,TRI[kind]/max(1,nf))
        dg=bpy.context.evaluated_depsgraph_get()
        e=o.evaluated_get(dg);me=e.to_mesh();me.calc_loop_triangles()
        gn_=[vg.name for vg in o.vertex_groups]
        # material areas to find the main garment of this piece
        area={}
        for p in me.polygons:area[p.material_index]=area.get(p.material_index,0)+p.area
        mats=[me.materials[i] if i<len(me.materials) else None for i in range(max(1,len(me.materials)))]
        main=None
        if kind in('Body','Legs','Pants'):
            c=[(a,i) for i,a in area.items() if mats[i] and mcls(mats[i].name,kind)==0]
            if c:main=max(c)[1]
        for tri in me.loop_triangles:
            mi=tri.material_index;m=mats[mi] if mi<len(mats) else None;mn=m.name if m else 'none'
            cl=mcls(mn,kind)
            if mi==main and cl==0:cl=3 if kind=='Body' else 4
            col=lin(m) if m else [.5,.5,.5]
            pk=(mn,cl)
            if pk not in palk:palk[pk]=len(pal);pal.append([round(x,4) for x in col]+[cl])
            ci=palk[pk]
            for li in tri.loops:
                vi=me.loops[li].vertex_index;key=(o.name,vi,ci)
                if key not in vmap:
                    v=me.vertices[vi];w={}
                    for ge in v.groups:
                        s=segof(gn_[ge.group]) if ge.group<len(gn_) else None
                        if s is not None and ge.weight>0:w[s]=w.get(s,0)+ge.weight
                    if not w:w={1:1}
                    top=sorted(w.items(),key=lambda x:-x[1])[:2]
                    if len(top)==1:top.append((top[0][0],0))
                    sa,wa=top[0];sb,wb=top[1];wt=wa/(wa+wb) if wa+wb>0 else 1
                    p=g(e.matrix_world@v.co);n=gn((e.matrix_world.to_3x3()@me.loops[li].normal if False else e.matrix_world.to_3x3()@v.normal).normalized())
                    for k in range(3):mins[k]=min(mins[k],p[k]);maxs[k]=max(maxs[k],p[k])
                    vmap[key]=len(V);V.append((p,n,ci,sa,sb,wt))
                I.append(vmap[key])
        e.to_mesh_clear();o.modifiers.remove(mod)
    # pack: pos int16 over bounds, normal int8x3, pal u8, segA u8, segB u8, w u8
    b=bytearray()
    for p,n,ci,sa,sb,wt in V:
        q=[int(round((p[k]-mins[k])/max(1e-6,maxs[k]-mins[k])*65535))-32768 for k in range(3)]
        b+=struct.pack('<hhhbbbBBBBx',*q,*[max(-127,min(127,int(round(x*127)))) for x in n],ci,sa,sb,int(round(wt*255)))
    ib=struct.pack('<%dH'%len(I),*I)
    res[prefix+nm]={'n':len(V),'t':len(I)//3,'mn':[round(x,5) for x in mins],'mx':[round(x,5) for x in maxs],'pal':pal,'v':base64.b64encode(bytes(b)).decode(),'i':base64.b64encode(ib).decode()}
    print(nm,len(V),'verts',len(I)//3,'tris','h',round(maxs[1],4),'pal',[(p[3]) for p in pal])
out_d={'J':J,'c':res}
json.dump(out_d,open(out,'w'))
print('J',J)
