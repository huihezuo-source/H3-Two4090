"""其他角色的动漫头像候选：用法 角色母版.py <wj|xw> <角色名>...   每个角色 3 个种子，2048×2048，存 角色/候选/<名>_s<seed>.png"""
import os, sys, subprocess, glob, shutil
HERE=os.path.dirname(os.path.abspath(__file__)); V=os.path.dirname(HERE)
S=os.environ.get("H3_SCRIPTS", os.path.join(HERE, "..", "..", "..", "scripts"))
URL={"wj":"http://127.0.0.1:18188","xw":"http://127.0.0.1:18189"}
STYLE="drawn as a character from a Japanese theatrical action anime (cel-shaded flat colours, hard-edged shadows, clean bold black line art), head-and-shoulders portrait facing the camera, on a plain cool-cyan background"
CAST={
 "主力":("the masked young man","a lean young man with a sharp jaw and a thin mouth curled in a smirk, short messy black hair swept up; he wears a red-and-gold opera mask with two curved horns and yellow ring-and-spiral patterns that covers his forehead, eyes and the bridge of his nose, leaving his mouth and chin bare; an open black suit jacket over a white T-shirt; red gloves"),
 "游资":("the masked young woman","a young woman with long wet dark hair plastered to her cheeks, a wide grin showing white teeth and red lipstick, a slim pointed chin; she wears a green sequined domino half-mask with olive-gold trim over her eyes and nose; a purple leather jacket with small silver star pins; the same delighted grin as the photo"),
 "量化":("the man in the full-face mask","a man whose whole face is hidden by a painted full-face mask: blue base, two white-ringed round eye holes, green-blue cheeks, a painted red mouth - no real mouth or eyes are visible; long shaggy dark wavy hair hangs over the mask and a short dark beard shows below its chin; a tan canvas jacket over a dark T-shirt; blue gloves"),
 "神秘机构":("the laughing young man","a slim young man laughing with his mouth wide open and head tilted back, shoulder-length messy light-brown hair, a translucent red visor across his eyes like tinted goggles, a yellow-green hooded jacket over a dark T-shirt; the same hearty laugh as the photo"),
 "空头":("the masked gunman","a young man with spiky dyed orange-red hair; the upper half of his face is covered by an orange-and-yellow painted cat-face mask with two big white eye patches and a pink nose, his mouth open below it; a pink-red hooded jacket"),
 "CPO":("the injured young hostage","a young man with thick messy black hair, a pale face smeared with blood on the forehead and cheek, eyes closed and mouth slack in pain, a dark police vest over a blue shirt; drawn lying as in the photo"),
 "商业航天":("the hanging hostage","a young man with short black hair, blood on his forehead and cheek, eyes narrowed in pain, mouth open, a dark police uniform; drawn upright as a portrait even though the photo is upside down"),
}
m=sys.argv[1]; out=os.path.join(V,"角色","候选"); os.makedirs(out,exist_ok=True); tmp=os.path.join(HERE,"_cast_"+m); os.makedirs(tmp,exist_ok=True)
env=dict(os.environ,COMFY_URL=URL[m],COMFY_CLIENT_ID="mac-claude")
for name in sys.argv[2:]:
    who,feat=CAST[name]
    prompt=(f"{who.capitalize()} in <Picture 1> is <Subject 1>. The target image is <Subject 1> {STYLE}, with the same expression as <Picture 1>. "
            f"<Subject 1> is partially preserved: {feat}. The likeness to the person in <Picture 1> is the top priority: the mask design and colours, hairstyle, hair colour, face shape and clothing match the photo exactly, so anyone who saw the film recognizes this character at once; it is a faithful anime caricature of this exact person, not a generic anime character. All burned-in text and watermarks from <Picture 1> are removed. Soft light from above.")
    src=os.path.join(V,"角色","原片脸",f"{name}.png")
    r=subprocess.run(["python3",f"{S}/h3_image.py",prompt,"--img",src,"--size","2048x2048","--seeds","1,2,3","--prefix",f"dmv2/cast/{name}","--wait",tmp],env=env,capture_output=True,text=True)
    for f in glob.glob(os.path.join(tmp,f"{name}_s*_*.png")):
        seed=os.path.basename(f).split("_s")[1].split("_")[0]; shutil.copy(f,os.path.join(out,f"{name}_s{seed}.png"))
    print(m,name,"done",r.stderr[-120:].strip(),flush=True)
