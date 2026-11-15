"""股民的晚餐：按挑好的首帧写 H3 任务并提交。
首帧放在 ../首帧/定稿/ 下：A1.png A2.png A3.png A4.png（A4 = 关灯版）、B1.png B2.png B3.png B4.png（B4 = 烟花版）。
用法：python3 做视频.py A|B [xw|wj]        → 写 jobs/A股.json 或 jobs/美股.json；给了机器就提交并等结果到 ../生成/<版本>_<标签>/
环境变量：GEN_TURBO=1（4 步草稿）、GEN_STEPS、SEED、TAG（输出目录后缀）
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE)
S = os.environ.get("H3_SCRIPTS", os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))  # 技能仓库的 scripts/ 目录
W, H, LEN = 448, 800, 362                      # 宽高必须是 32 的倍数（432 报 shape 错）；9:16，放大 2.5 倍后裁成 1080×1920
CUTS = {"A": {"2": 134, "3": 221, "5": 292, "4": 300},   # 5.583 s / 9.208 s / 12.17 s 手抓拉绳灯还亮 / 12.5 s 全黑
        "B": {"2": 134, "3": 221, "4": 300}}           # 5.583 s / 9.208 s / 12.5 s 管家换盘
ver = sys.argv[1]
name = {"A": "A股", "B": "美股"}[ver]
turbo = bool(os.environ.get("GEN_TURBO"))
steps = int(os.environ.get("GEN_STEPS", 4 if turbo else 20))
seed = int(os.environ.get("SEED", 1115 if ver == "A" else 2115))
tag = os.environ.get("TAG", "草稿4步" if turbo else "正式20步")

src = os.path.join(V, "首帧", "定稿"); gen = os.path.join(V, "首帧", "生成尺寸"); os.makedirs(gen, exist_ok=True)
imgs = {}
for k in ["1"] + list(CUTS[ver]):
    f = os.path.join(src, f"{ver}{k}.png"); assert os.path.exists(f), f
    g = os.path.join(gen, f"{ver}{k}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", g], check=True)
    imgs[k] = g

PA = """For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, vertical 9:16, dim cold tones. The shot begins exactly as <Picture 1>: a close-up of a blackened iron wok on a rough brick stove inside a crumbling mud-walled hut, wood fire flickering under the wok, plain white noodles rolling in boiling water, steam rising, a single dim bare bulb overhead. The camera holds nearly still with a tiny handheld drift. The ordinary hand of a middle-aged man, normal healthy skin, holds a pair of old wooden chopsticks and an iron skimmer, dips them into the pot, lifts a dripping tangle of noodles out of the water and holds it up as water streams back into the wok. [Shot 2] At 00:05.583, the shot cuts to a high-angle close-up of a chipped white enamel bowl with a blue rim on a greasy, stained wooden table, filled with clear broth and plain white noodles, nothing else in the bowl. The same ordinary hand enters from above, pinches a small handful of chopped scallions and sprinkles them slowly onto the noodles; the camera is static. [Shot 3] At 00:09.208, the shot cuts to a medium close-up: a bare incandescent bulb hangs on a black cord from the upper left with a thin pull-string beside it, and a gaunt, deeply wrinkled middle-aged man in a worn, faded grey padded jacket sits at the right, bent over the bowl of noodles on the table. He lifts a bundle of noodles with wooden chopsticks, puts them in his mouth and slurps them loudly, chewing slowly with a numb, exhausted expression, eyes down on the bowl. At 00:11.000 he stops chewing, looks up at the bulb, raises his left hand and takes hold of the thin pull-string hanging beside the bulb; at 00:12.300 he tugs the string downward and the bulb clicks off instantly, in a single frame, with no gradual dimming: the room drops into near-total darkness with only a faint cold blue glow outlining his face, the chopsticks and the bowl. He lowers his hand, picks the chopsticks back up and keeps slurping noodles in the dark until the end of the video. There is no dialogue; nobody speaks.

overall_soundscape: Wood crackles and pops under the wok while water boils with a steady rolling bubble; the skimmer scrapes the iron wok and water drips back into the pot. Scallions patter softly into the broth. Loud wet slurping and chewing, then a sharp click of the pull-string switch at 00:12.300, and slurping continues in the dark over a faint room tone.

non_diegetic_music: A clearly audible, slow, melancholy solo cello melody with long sustained low notes, moderate volume, beginning as the noodles reach the bowl at 00:05.583 and continuing unchanged through the darkness to the end of the video."""

PB = """For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, vertical 9:16, warm bright golden tones. The shot begins exactly as <Picture 1>: a close-up of a gleaming copper pan on a white marble counter in a bright luxury kitchen, two large lobster tails sizzling in golden butter, a burst of orange flame licking up the side of the pan, blurred crystal chandelier and champagne glasses in the background. The camera holds nearly still with a slow, tiny push-in. A chef's hand in a white glove holds a long spoon, scoops the foaming butter and bastes it over the lobster tails again and again; the flame flares once more and settles. [Shot 2] At 00:05.583, the shot cuts to a high-angle close-up of a large gold-rimmed bone-china plate on a white tablecloth with a whole grilled lobster split open, its white meat glistening with melted butter, a flute of champagne bubbling beside silver cutlery. A white-gloved hand enters from above with a small mother-of-pearl spoon and sprinkles black caviar slowly over the lobster meat; the camera is static. [Shot 3] At 00:09.208, the shot cuts to a medium close-up: a huge crystal chandelier hangs from the upper left, and a relaxed, rosy-cheeked middle-aged man in a white silk bathrobe sits at the right at a long dining table in a mansion, floor-to-ceiling windows behind him showing a swimming pool under an orange sunset. He spears a big chunk of white lobster meat with a golden fork, puts it in his mouth and chews with a satisfied, carefree smile. At 00:12.500, after only two bites, he pushes the plate away with the back of his hand and leans back; a butler's white-gloved hands enter from the left, lift the barely touched lobster plate out of frame and set down a fresh gold-rimmed plate with a whole new grilled lobster in front of him, and he grins and picks up the golden fork again until the end of the video. There is no dialogue; nobody speaks.

overall_soundscape: Butter sizzles and spits in the copper pan with a soft whoosh of flame; the spoon clinks against copper. Caviar pats gently onto the lobster while champagne fizzes. The golden fork taps porcelain, contented chewing, the soft slide of a plate pushed across the tablecloth, the butler's quiet footsteps and the clink of a new plate set down.

non_diegetic_music: A clearly audible, light, bouncy, cheerful tune at a brisk tempo on ukulele with carefree whistling and a walking upright bass, playful and relaxed, moderate volume, playing from the very first second and continuing to the end of the video."""

job = {"prompt": PA if ver == "A" else PB, "width": W, "height": H, "length": LEN, "steps": steps, "turbo": turbo, "seed": seed,
       "prefix": f"dinner/{ver}_{tag}", "images": [imgs["1"]], "anchor_frames": [0],
       "guides": [{"image": imgs[k], "frame": fr} for k, fr in CUTS[ver].items()], "audios": [], "videos": []}
jp = os.path.join(HERE, "jobs", f"{name}_{tag}.json"); os.makedirs(os.path.dirname(jp), exist_ok=True)
json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
print("写好", jp, f"{W}x{H} {LEN}帧 {steps}步 turbo={turbo} seed={seed}")
if len(sys.argv) > 2:
    env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[sys.argv[2]])
    out = os.path.join(V, "生成", f"{name}_{tag}"); os.makedirs(out, exist_ok=True)
    subprocess.run(["python3", f"{S}/h3_ref2va.py", jp, "--wait", out], env=env)
