"""公司机器上的整人换人（H3 Ref2VA + Character Swap LoRA）：原片 576×1024 当 <Video 1>，形象图当 <Picture 1>，
设计声当 <Audio 1>，台词写进提示词由 H3 自己配音并对口型（不另跑 TTS）。
用法：python3 做换人_公司.py <1|2|3> [xw|wj]   环境变量：GEN_TURBO=1（4 步草稿）、GEN_STEPS、SEED、TAG、GEN_SIZE（默认 576x1024）
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE)
S = os.environ.get("H3_SCRIPTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))  # 技能仓库的 scripts/ 目录
i = int(sys.argv[1]); m = sys.argv[2] if len(sys.argv) > 2 else None
W, H = map(int, os.environ.get("GEN_SIZE", "576x1024").split("x"))
turbo = bool(os.environ.get("GEN_TURBO")); steps = int(os.environ.get("GEN_STEPS", 4 if turbo else 20))
seed = int(os.environ.get("SEED", 5200 + i)); tag = os.environ.get("TAG", "草稿4步" if turbo else "正式20步")
# 参考图默认用长边 896 的小图（角色候选/小图）：三张 1504×2672 原图会把 24 GB 显存撑爆，20 步要跑 29 小时；REF_FULL=1 才用原图
REF_DIR = os.path.join(V, "角色候选") if os.environ.get("REF_FULL") else os.path.join(V, "角色候选", "小图")
PIC = os.path.join(REF_DIR, f"woman_v{i}_s400{i}_00001_.png")
VOICE = {1: "A2_温柔低_s503_00001.flac", 2: "B2_爽朗低_s503_00001.flac", 3: "C_知性_s502_00001.flac"}[i]
AUD = os.path.join(V, "声音候选", "设计", VOICE)
# 参考音默认用裁掉后半句的版本：三段设计音都念了这条股评，H3 会把 <Audio 1> 里的词（「宁可错过也不想再站岗」）漏进生成语音，五次出片全在同一处念乱；REF_AUDIO=full 才用整段
if not os.environ.get("REF_AUDIO") == "full":
    AUD = os.path.join(V, "声音候选", "设计", "裁剪", {1: "A2_前半.flac", 2: "B2_前半.flac", 3: "C_前半.flac"}[i])
SRC = os.path.join(HERE, f"src15_{W}x{H}.mp4")
if not os.path.exists(SRC):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(HERE, "openjutsu", "oj_video_clean.mp4"), "-vf", f"scale={W}:{H}", "-r", "24", "-an", SRC], check=True)
for f in (PIC, AUD, SRC): assert os.path.exists(f), f
TEETH = [p for p in (os.path.join(REF_DIR, f"teeth_v{i}_talk_s410{i}_00001_.png"), os.path.join(REF_DIR, f"teeth_v{i}_smile_s410{i}_00001_.png")) if os.path.exists(p)]
if not os.environ.get("NO_TEETH"): assert len(TEETH) == 2, "缺露齿参考照，先跑 出露齿参考.py"
else: TEETH = []
LINE = os.environ.get("LINE") or "今天上午指数走得很稳，成交比昨天放大了一些，我的仓位没动，还是按计划拿着。追高这件事我已经戒了，不想再站岗。行情天天有，心态稳住了，比什么都重要。"  # 63 字。79 字版 H3 会掉字/乱序（形象1 掉「宁可错过」，形象2 变成「也不想再站岗，宁可撑」），15 秒以 ≤70 字为限
TEETH_DEF = " <Picture 2> shows the same woman mid-sentence with her mouth open and her natural upper teeth visible; <Picture 3> shows her smiling with her teeth showing. Whenever her mouth opens while speaking or smiling, the inside of her mouth and her teeth look exactly as in <Picture 2> and <Picture 3>, the same real teeth in every frame; between phrases her lips rest closed and relaxed." if TEETH else ""
# REF_MODE=talk（默认）：只用一张「说话露齿」半身照当 <Picture 1>，它本身带着深 V 衣服、同一背景和牙齿；三张图（全身+两张露齿）哪怕缩到 896 也会把显存撑爆（17:13 那轮 20 分钟没走完第 1 步）
REF_MODE = os.environ.get("REF_MODE", "talk")
if REF_MODE == "talk":
    PIC = os.path.join(REF_DIR, f"teeth_v{i}_talk_s410{i}_00001_.png"); assert os.path.exists(PIC), PIC; TEETH = []
    TEETH_DEF = " <Picture 1> shows her mid-sentence with her mouth open and her natural upper teeth visible. Whenever her mouth opens while speaking or smiling, the inside of her mouth and her teeth look exactly as in <Picture 1>, the same real teeth in every frame; between phrases her lips rest closed and relaxed."
prompt = f"""body_swap: <Video 1> is the source performance. <Picture 1> is the character reference. <Audio 1> is the voice reference.{TEETH_DEF}
Replace the man in <Video 1> with the young woman in <Picture 1>, from the very first frame. She keeps her face, hair, skin tone, full figure and her own clothes from <Picture 1>: the deep V-neck top with her cleavage visible exactly as in the picture; no cap, no vest, no plaid shirt, no glasses. Nothing of the original man remains.
She walks and talks to the handheld phone camera exactly like the source performance, following its position in the frame, head movement, gaze, hand gestures, timing and camera motion frame by frame. Whenever the man in <Video 1> turns, tilts or lowers his head, she turns, tilts or lowers her head the same way at the same moment; she never stares rigidly into the lens.
Her face stays alive like a real person in a phone video: eyebrows lift and drop slightly with the words, cheeks and jaw move naturally with each syllable, small nods and tilts, a blink every few seconds, a relaxed expression with no fixed grin; her mouth opens only as much as speaking needs.
The background, the path, the field, the houses, the overcast hazy light, the muted colours and the handheld shake are exactly those of <Video 1>. Realistic phone footage: natural skin texture, slight sensor noise, no beauty filter. No text, subtitles, logo or watermark anywhere.
She speaks in the voice of <Audio 1>, calmly and naturally, with her lips in sync: <d>[Chinese] {LINE}</d> The soundtrack is her voice and the quiet outdoor ambience of the source only, no music."""
job = {"prompt": prompt, "width": W, "height": H, "length": 362, "steps": steps, "turbo": turbo, "seed": seed, "prefix": f"swap/woman{i}_{tag}",
       "images": [PIC] + TEETH, "anchor_frames": [], "guides": [], "audios": [AUD], "videos": [SRC], "loras": [[os.environ.get("SWAP_LORA", "minimax_h3_character_swap_v1.1_ref2va_fro.safetensors"), float(os.environ.get("SWAP_STRENGTH", 1.0))]]}
os.makedirs(os.path.join(HERE, "jobs"), exist_ok=True); jp = os.path.join(HERE, "jobs", f"换人{i}_{tag}.json")
json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1); print("写好", jp, f"{W}x{H} {steps}步 turbo={turbo} seed={seed}")
if m:
    env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[m])
    out = os.path.join(V, "生成", f"woman{i}_{tag}"); os.makedirs(out, exist_ok=True)
    subprocess.run(["python3", f"{S}/h3_ref2va.py", jp, "--wait", out], env=env)
