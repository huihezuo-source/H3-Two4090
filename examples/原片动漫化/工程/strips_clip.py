"""对一段生成视频做嘴部条带：用法 strips_clip.py <mp4> <段起始绝对秒> <输出目录>  （8 fps，按 shots.tsv 分镜头，YuNet 跟踪）"""
import os, sys, cv2, numpy as np, subprocess, glob
mp4, off, OUT = sys.argv[1], float(sys.argv[2]), sys.argv[3]
os.makedirs(OUT, exist_ok=True); FR=os.path.join(OUT,"f8"); os.makedirs(FR, exist_ok=True)
for f in glob.glob(FR+"/*.png"): os.remove(f)
subprocess.run(["ffmpeg","-v","error","-y","-i",mp4,"-vf","fps=8",FR+"/f_%05d.png"],check=True)
n_frames=len(glob.glob(FR+"/*.png")); dur=n_frames/8
FPS=8; CROP=112
shots=[]
for ln in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "全片", "shots.tsv")):
    n,a,b,d=ln.split(); a=float(a); b=float(b)
    if b>off+0.01 and a<off+dur-0.01: shots.append((int(n),max(a,off)-off,min(b,off+dur)-off))
det=cv2.FaceDetectorYN.create(os.environ.get("YUNET", os.path.expanduser("~/models/face/yunet.onnx")),"",(1056,448),score_threshold=0.45); det.setInputSize((1056,448))
all_rows=[]
for n,a,b in shots:
    i0=int(round(a*FPS)); i1=int(round(b*FPS)); bpf=[]
    for i in range(i0,i1):
        p=f"{FR}/f_{i+1:05d}.png"
        if not os.path.exists(p): break
        img=cv2.imread(p); _,faces=det.detect(img)
        bpf.append((i,img,[] if faces is None else [tuple(int(v) for v in f[:4]) for f in faces if f[3]>=18]))
    tracks=[]
    for i,img,fb in bpf:
        for (x,y,w,h) in fb:
            cx,cy=x+w/2,y+h/2; best=None
            for t in tracks:
                lx,ly,lw,lh=t["last"]; d=np.hypot(cx-(lx+lw/2),cy-(ly+lh/2))
                if d<max(lw,lh)*0.9 and (best is None or d<best[0]): best=(d,t)
            if best: best[1]["boxes"][i]=(x,y,w,h); best[1]["last"]=(x,y,w,h)
            else: tracks.append({"boxes":{i:(x,y,w,h)},"last":(x,y,w,h)})
    tracks=[t for t in tracks if len(t["boxes"])>=max(2,(i1-i0)//6)]
    for ti,t in enumerate(tracks):
        row=[]; last=None
        for i,img,_ in bpf:
            bx=t["boxes"].get(i,last); last=bx if bx else last
            if bx is None: row.append(np.zeros((CROP,CROP,3),np.uint8)); continue
            x,y,w,h=bx; cx,cy=x+w/2,y+h*0.6; s=max(w,h)*1.25
            x0=int(max(0,cx-s/2)); y0=int(max(0,cy-s/2)); x1=int(min(1056,cx+s/2)); y1=int(min(448,cy+s/2))
            c=img[y0:y1,x0:x1]
            if c.size==0: row.append(np.zeros((CROP,CROP,3),np.uint8)); continue
            c=cv2.resize(c,(CROP,CROP),interpolation=cv2.INTER_AREA)
            cv2.putText(c,f"{off+i/FPS:.1f}",(2,14),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255),1)
            if i in t["boxes"]: cv2.circle(c,(CROP-8,8),4,(0,255,0),-1)
            row.append(c)
        ncol=16; lines=[]
        for k in range(0,len(row),ncol):
            ch=row[k:k+ncol]
            while len(ch)<ncol: ch.append(np.zeros((CROP,CROP,3),np.uint8))
            lines.append(np.hstack(ch))
        strip=np.vstack(lines); cv2.putText(strip,f"c{n:02d} face{ti+1}",(4,strip.shape[0]-6),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,255),1)
        all_rows.append(strip)
if all_rows:
    cv2.imwrite(os.path.join(OUT,"strips.jpg"),np.vstack(all_rows),[cv2.IMWRITE_JPEG_QUALITY,85])
print("shots",[s[0] for s in shots],"rows",len(all_rows),"dur",dur)
