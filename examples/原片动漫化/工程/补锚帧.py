"""补锚定帧：shots.tsv 漏掉的切点和长镜头中段，从原片抽帧转成动漫（用首帧v2 的表情/母版规则）。
ANCHORS: (绝对秒, 所属镜头号, 类型 cut/mid, 额外描述)。输出 首帧/原始/cNN_<秒>.png。用法：补锚帧.py <wj|xw> [秒...]（不给=全部缺的）"""
import os, sys, subprocess, glob, shutil, importlib.util, time
HERE=os.path.dirname(os.path.abspath(__file__)); V=os.path.dirname(HERE)
spec=importlib.util.spec_from_file_location("ff", os.path.join(HERE,"首帧v2.py")); ff=importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
REF=os.path.join(V,"原片.mp4")
ANCHORS=[
 (8.70, 2, "cut", " This is an extreme high-angle shot looking straight down: the police officer is small, walking across the concrete floor past the tyre stacks, his long shadow beside him; nobody else is in the picture; no face detail is needed."),
 (22.30, 8, "mid", ""),
 (49.33, 20, "cut", " A low-angle wide shot looking up at the catwalk with diagonal steel trusses and many thick ropes hanging from the railing; the masked man in the tan jacket is small, walking along the railing; he is the only person."),
 (51.80, 22, "cut", " A wide shot of the warehouse floor: the police officer stands in the middle distance looking toward the gang leader, who stands farther away near the back wall; both are small; nobody is lying on the floor."),
 (57.50, 27, "mid", ""),
 (58.80, 28, "cut", " A medium close-up of the gang leader in his red-and-gold horned mask, mouth slightly open as he speaks, black jacket over white T-shirt; he is the only person in the picture."),
 (86.50, 42, "mid", ""),
 (97.50, 44, "mid", ""),
 (128.00, 62, "midx", " The police officer has turned around to face the camera, bracing with both hands on the metal railing, his face fully lit by the orange fire behind him: eyes narrowed, teeth clenched, hair blown by the blast; his face is a normal drawn anime face with clear eyes, nose and mouth, not a blank plate. The fireball fills the background."),
 (136.60, 65, "cut", " A wide shot of the warehouse interior with a huge orange fireball erupting in the centre and debris flying; there are NO people in the picture."),
 (142.20, 66, "cut", ""),
]
REFS_OVERRIDE={58.80:["ZL"], 57.50:["SH"], 128.00:["SH"], 8.70:[], 49.33:[], 51.80:[], 136.60:[], 22.30:["SH"], 86.50:["ZL"], 97.50:["ZL"], 142.20:["SH"]}
m=sys.argv[1]; want=[float(x) for x in sys.argv[2:]] or [a[0] for a in ANCHORS]
env=dict(os.environ, COMFY_URL=ff.URL[m], COMFY_CLIENT_ID="mac-claude"); tmp=os.path.join(HERE,"_anc_"+m); os.makedirs(tmp,exist_ok=True)
src_dir=os.path.join(V,"首帧","补锚原片帧"); os.makedirs(src_dir,exist_ok=True)
for t,n,kind,extra in ANCHORS:
    if all(abs(t-w)>0.01 for w in want): continue
    dst=os.path.join(ff.OUT, f"c{n:02d}_{t:.2f}.png")
    if os.path.exists(dst): continue
    src=os.path.join(src_dir, f"c{n:02d}_{t:.2f}.png")
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{t:.3f}","-i",REF,"-frames:v","1","-vf","crop=1280:544:0:88",src],check=True)
    l1,l2=ff.LIGHT[ff.light_of(n)]
    ex=ff.EXTRA.get(n,"") if kind=="mid" else extra
    if n in ff.EXPR and (kind=="mid" or n in (66,)): ex+=" What <Subject 1> shows, to be drawn exactly as described and nothing more: "+ff.EXPR[n]
    imgs=[src]
    for i,c in enumerate(REFS_OVERRIDE.get(t, ff.REFS.get(n,[]))):
        f,_,sent=ff.MASTER[c]; imgs.append(os.path.join(V,"角色",f)); ex+=" "+sent.format(k=i+2,s=i+2)
    prompt=ff.BASE.format(light=l1,extra=ex,lamp=l2)
    if t==136.60:   # 空镜：不能出现"人物"字样，否则 H3 Image 会凭空画人
        prompt=("<Picture 1> is an empty wide shot with no people in it: the inside of the warehouse being torn apart by a huge orange fireball in the centre, debris and sparks flying, steel structures silhouetted against the blast. "
                "The target image is the same picture repainted as a background painting from a Japanese theatrical action anime film: cel-shaded flat colours with hard-edged shadows, clean bold line art, painted anime background. "
                "The composition, structures, fire and debris stay exactly where they are in <Picture 1>. It is a pure scenery painting: no person, no face, no figure, no silhouette anywhere in the picture. All burned-in text and credits are removed. "
                "Lighting comes from the flames: warm orange light with hard dark shadows and flying embers.")
    args=[]
    for im in imgs: args+=["--img",im]
    t0=time.time()
    r=subprocess.run(["python3",f"{ff.S}/h3_image.py",prompt,*args,"--size","3072x1312","--seeds","1","--prefix",f"dmv2/anc_c{n:02d}_{int(t*100)}","--wait",tmp],env=env,capture_output=True,text=True)
    fs=sorted(glob.glob(os.path.join(tmp,f"anc_c{n:02d}_{int(t*100)}_s*_*.png")),key=os.path.getmtime)
    if fs: shutil.copy(fs[-1],dst)
    print(m, f"c{n:02d}_{t:.2f}", "ok" if fs else "FAIL", f"{time.time()-t0:.0f}s", r.stderr[-120:].strip(), flush=True)
