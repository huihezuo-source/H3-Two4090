"""自动找"嘴在动但没人声"的时段：YuNet 逐帧（8 fps）找脸 + 嘴角关键点，裁嘴部算相邻帧差；
和 工程/voice_grid12.npy（12 格/秒的人声开关）对照，连续 ≥0.5 秒嘴动而无人声的报出来。
用法：嘴动对人声.py <整片mp4> [起始绝对秒=0]   输出：工程/嘴动无声_报告.txt"""
import os, sys, cv2, numpy as np, subprocess, glob, tempfile
HERE=os.path.dirname(os.path.abspath(__file__)); V=os.path.dirname(HERE)
mp4=sys.argv[1]; off=float(sys.argv[2]) if len(sys.argv)>2 else 0.0
FPS=8
tmp=tempfile.mkdtemp(prefix="lipv_")
subprocess.run(["ffmpeg","-v","error","-y","-i",mp4,"-vf","fps=8,scale=1056:448",f"{tmp}/f_%05d.png"],check=True)
frames=sorted(glob.glob(f"{tmp}/f_*.png")); n=len(frames)
# 允许嘴动的时段：台词（成片v2.py 的 SUBS）+ 原片里无词的喊叫/大笑/喘气
import importlib.util
spec=importlib.util.spec_from_file_location("cp", os.path.join(HERE,"成片v2.py")); cp=importlib.util.module_from_spec(spec)
_argv=sys.argv; sys.argv=[sys.argv[0],"none"]
try: spec.loader.exec_module(cp)
except SystemExit: pass
sys.argv=_argv
ALLOWED=[(a-0.3,b+0.3) for a,b,_ in cp.SUBS]
ALLOWED+=[(15.3,16.3),(19.6,24.9),(26.0,27.3),(44.8,48.2),(54.2,55.3),(55.3,56.8),(62.0,63.2),(70.4,72.0),(77.3,80.5),(112.8,113.6),(113.4,114.7),(115.6,117.0),(125.3,126.9),(138.5,142.8)]
def voiced(t):
    return any(a<=t<=b for a,b in ALLOWED)
det=cv2.FaceDetectorYN.create(os.environ.get("YUNET", os.path.expanduser("~/models/face/yunet.onnx")),"",(1056,448),score_threshold=0.5); det.setInputSize((1056,448))
shots=[]
for ln in open(os.path.join(os.path.dirname(V),"全片","shots.tsv")):
    k,a,b,d=ln.split(); shots.append((int(k),float(a),float(b)))
def shot_of(t):
    for k,a,b in shots:
        if a<=t<b: return k
    return 0
prev={}  # track key -> (mouth crop gray)
events=[]  # (t, shot, score)
for i,p in enumerate(frames):
    t=off+i/FPS; img=cv2.imread(p); _,faces=det.detect(img)
    cur={}
    if faces is not None:
        for f in faces:
            x,y,w,h=[int(v) for v in f[:4]]
            if h<40: continue
            rmx,rmy,lmx,lmy=f[10],f[11],f[12],f[13]
            cx=(rmx+lmx)/2; cy=(rmy+lmy)/2; mw=max(abs(lmx-rmx)*1.6, w*0.45); mh=mw*0.7
            x0=int(max(0,cx-mw/2)); y0=int(max(0,cy-mh/2)); x1=int(min(1056,cx+mw/2)); y1=int(min(448,cy+mh/2))
            crop=img[y0:y1,x0:x1]
            if crop.size==0: continue
            g=cv2.resize(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),(48,32)).astype(np.float32)
            fx0=max(0,x); fy0=max(0,y); fcrop=img[fy0:min(448,y+h), fx0:min(1056,x+w)]
            fg=cv2.resize(cv2.cvtColor(fcrop,cv2.COLOR_BGR2GRAY),(48,48)).astype(np.float32)
            key=(round(x/120),round(y/120))  # 粗略按位置归类
            cur[key]=(g,(x,y,w,h),fg)
            if key in prev:
                d=float(np.abs(g-prev[key][0]).mean()); fd=float(np.abs(fg-prev[key][2]).mean())
                if not voiced(t) and d>8.0 and d>1.6*fd:
                    events.append((t,shot_of(t),d,key))
    prev=cur
# 合并成区间
events.sort(); runs=[]
for t,s,d,key in events:
    if runs and t-runs[-1][1]<=0.3 and runs[-1][2]==s: runs[-1][1]=t; runs[-1][3]=max(runs[-1][3],d); runs[-1][4]+=1
    else: runs.append([t,t,s,d,1])
bad=[r for r in runs if r[1]-r[0]>=0.25]
out=os.path.join(HERE,"嘴动无声_报告.txt")
with open(out,"w") as f:
    f.write(f"{mp4}\n嘴在动但台词表里没人说话（≥0.25 秒）：{len(bad)} 处\n")
    for a,b,s,d,c in bad: f.write(f"  c{s:02d} {a:.2f}-{b:.2f}s  峰值差 {d:.1f}  帧数 {c}\n")
print(open(out).read())
import shutil; shutil.rmtree(tmp)
