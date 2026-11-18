"""年轻女性角色候选：用盖了脸的原片帧（openjutsu/outfit_ref_f12.png）当 <Picture 1>，让 H3 Image 把人换成年轻女性，
光线、色调、背景、手机实拍质感全部跟原片走。用法：python3 出形象.py xw 1,2,3 | python3 出形象.py wj 4,5,6
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE)
S = os.environ.get("H3_SCRIPTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))  # 技能仓库的 scripts/ 目录
REF = os.path.join(HERE, "openjutsu", "outfit_ref_f12.png"); OUT = os.path.join(V, "角色候选"); os.makedirs(OUT, exist_ok=True)
BASE = ("<Picture 1> is a vertical handheld phone video frame: a person standing on a concrete path beside a ploughed field on an overcast, hazy day, "
        "a grey house and trees in the distance, the face covered by a grey oval. The target image keeps the exact same background, camera framing, lens perspective, "
        "overcast flat daylight, washed-out hazy sky, muted colours and cheap phone-camera look of <Picture 1>, but the person is replaced entirely by a different person: "
        "a Chinese woman in her mid-20s, full-figured and curvy with an ample bust and soft rounded shoulders, wearing {outfit}, with a deep V neckline that shows her cleavage, "
        "{hair}, natural light makeup, no glasses, no hat, a relaxed friendly expression with lips closed, standing in the same spot and looking at the camera. "
        "Her skin and clothes are lit by the same soft overcast light as the scene, with the same slightly cool, low-saturation colour grading, so she looks like she was filmed "
        "in this footage; no studio lighting, no beauty filter, no grey oval, no cap, no vest, no plaid shirt. No text or watermark.")
VARS = {
    1: dict(outfit="a fitted black deep V-neck knit top and light-wash jeans", hair="long straight black hair falling over her shoulders"),
    2: dict(outfit="a white deep V-neck wrap blouse", hair="shoulder-length wavy dark-brown hair"),
    3: dict(outfit="a burgundy deep V-neck sweater dress", hair="long black hair tied in a loose low ponytail"),
    4: dict(outfit="an emerald-green deep V-neck satin top and a black skirt", hair="long black hair with soft bangs"),
    5: dict(outfit="a beige deep V-neck knit cardigan worn with nothing underneath it", hair="a high ponytail"),
    6: dict(outfit="a black deep V-neck bodycon dress", hair="long loose wavy black hair"),
}
m, ids = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[m])
for i in ids:
    r = subprocess.run(["python3", f"{S}/h3_image.py", BASE.format(**VARS[i]), "--img", REF, "--size", "1504x2672", "--seeds", str(4000 + i),
                        "--prefix", f"swap/woman_v{i}", "--wait", OUT], env=env, capture_output=True, text=True)
    print(f"v{i}", (r.stdout.strip().splitlines() or [r.stderr[-200:]])[-1], flush=True)
