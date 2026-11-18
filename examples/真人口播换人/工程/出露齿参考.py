"""给每位形象出两张露齿参考照（H3 Image，在定稿全身照上改）：说话中露上齿 / 自然微笑露齿。
用法：python3 出露齿参考.py <机器 xw|wj> <形象编号,...>   输出 ../角色候选/teeth_v{i}_{talk|smile}.png
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE)
S = os.environ.get("H3_SCRIPTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))  # 技能仓库的 scripts/ 目录
OUT = os.path.join(V, "角色候选"); m, ids = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[m])
P = {
 "talk": "<Picture 1> shows <Subject 1>, a young woman standing on a path by a field. The target image is a close-up portrait of exactly the same woman, same face, same hair, same deep V-neck top, same overcast outdoor light and background, framed from the chest up, caught mid-sentence while talking to the phone camera: her mouth is naturally open as in speech, showing her real upper teeth, which are ordinary, slightly uneven, natural off-white human teeth, lips soft and relaxed, eyes looking at the lens. <Subject 1> is fully preserved. Photorealistic phone photo, natural skin texture, no beauty filter, no text.",
 "smile": "<Picture 1> shows <Subject 1>, a young woman standing on a path by a field. The target image is a close-up portrait of exactly the same woman, same face, same hair, same deep V-neck top, same overcast outdoor light and background, framed from the chest up, giving a warm natural smile with her lips parted so her upper teeth show, ordinary natural human teeth, slight laugh lines, eyes looking at the lens. <Subject 1> is fully preserved. Photorealistic phone photo, natural skin texture, no beauty filter, no text.",
}
for i in ids:
    pic = os.path.join(OUT, f"woman_v{i}_s400{i}_00001_.png")
    for k, prompt in P.items():
        r = subprocess.run(["python3", f"{S}/h3_image.py", prompt, "--img", pic, "--size", "1504x2672", "--seeds", str(4100 + i), "--prefix", f"swap/teeth_v{i}_{k}", "--wait", OUT], env=env, capture_output=True, text=True)
        print(f"v{i} {k}", (r.stdout.strip().splitlines() or [r.stderr[-200:]])[-1], flush=True)
