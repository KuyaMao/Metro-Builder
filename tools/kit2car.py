"""Convert export_kit.py output for Kenney Car Kit vehicles into MODELPACK car format (classes paint/det).
usage: python3 -I kit2car.py in.json out.json name[:fixed] ..."""
import sys,json,colorsys,math
d=json.load(open(sys.argv[1]));res={}
for arg in sys.argv[3:]:
    name,_,fx=arg.partition(':');m=d[name];acc={};gs=[]
    for g in m['g']:
        p=[x/1000 for x in g['p']];flat=[]
        for i in g['i']:flat+=p[i*3:i*3+3]
        ar=0
        for t in range(0,len(flat),9):
            a=flat[t:t+3];b=flat[t+3:t+6];c=flat[t+6:t+9];u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
            cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];ar+=math.sqrt(sum(x*x for x in cr))/2
        col=tuple(int(g['c'][k:k+2],16)/255 for k in (0,2,4));h,s,vv=colorsys.rgb_to_hsv(*col)
        if s>.35 and vv>.35:acc[round(h*24)%24]=acc.get(round(h*24)%24,0)+ar
        gs.append((g['c'],h,s,vv,[round(x,3) for x in flat]))
    body=max(acc,key=acc.get) if acc else None;out={}
    for c,h,s,vv,flat in gs:
        k='det';cc=c
        if body is not None and s>.35 and vv>.35 and min(abs(round(h*24)%24-body),24-abs(round(h*24)%24-body))<=1:
            k='paint'
            if fx!='fixed':l=int(255*min(1,vv/.9));cc='%02x%02x%02x'%(l,l,l)
        out.setdefault((k,cc),[]).extend(flat)
    allp=[x for f in out.values() for x in f]
    b=[min(allp[0::3]),min(allp[1::3]),min(allp[2::3]),max(allp[0::3]),max(allp[1::3]),max(allp[2::3])]
    res[name]={'b':b,'g':[{'c':c,'k':k,'p':f} for (k,c),f in out.items()]}
    print(name,'body hue',body,'paint tris',sum(len(f)//9 for (k,c),f in out.items() if k=='paint'),'size',[round(b[3]-b[0],2),round(b[4]-b[1],2),round(b[5]-b[2],2)])
json.dump(res,open(sys.argv[2],'w'),separators=(',',':'))
