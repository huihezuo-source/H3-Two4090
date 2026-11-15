"""H3 Fun ControlNet 测试：原片 67.8–77.925 秒（c34–c40，含原来最差的 c37–c39）用 Canny 控制视频逐帧锁结构，
参考图只放头像母版 + 一张动漫首帧当画风参考，不再锚定首帧（首帧本身构图就不准，会和控制信号打架），原声锁第 0 帧。

用法：python3 控制测试.py            → 只写 jobs/控制测试.json
      python3 控制测试.py xw         → 写好并提交到 XW 等结果，输出到 ../生成/ctrl_test/
环境变量：CTRL_TAG 变体名（加在输出名后）、GEN_TURBO=1 用 4 步加速 LoRA 快速试参、CTRL_VIDEO 控制视频路径、CTRL_STRENGTH（默认 1.0）、GEN_STEPS（默认 20）、SEED_BASE（默认 700）、CTRL_PATCH 模型文件名
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
S = os.environ.get("H3_SCRIPTS", os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
M = os.path.join(V, "角色")
SCRATCH = os.path.join(V, "_scratch", "ctrl")
A0, LEN = 67.8, 243                      # 起点秒、帧数（17k+5）
CTRL = os.environ.get("CTRL_VIDEO", os.path.join(SCRATCH, "ctrl_canny.mp4"))
AUDIO = os.path.join(SCRATCH, "seg_audio.wav")

def ts(x):
    return f"{int(x) // 60:02d}:{x % 60:06.3f}"

imgs = [os.path.join(M, "散户_头像_A2.png"), os.path.join(M, "主力_头像.png"), os.path.join(M, "游资_头像.png"),
        os.path.join(M, "空头_头像.png"), os.path.join(V, "首帧", "生成尺寸", "c35.png")]
for f in imgs:
    assert os.path.exists(f), f
SH, ZL, YZ, KT = "<Subject 1>", "<Subject 2>", "<Subject 3>", "<Subject 4>"
defs = [
    f"{SH} is the police officer: a middle-aged man with tousled black hair, a light-blue long-sleeve shirt, a dark tie and a dark-blue police tactical vest lettered POLICE; his face, hair and features exactly as in the head portrait <Picture 1>.",
    f"{ZL} is the gang leader: a young man in an open black suit jacket over a white T-shirt, a red-and-gold horned opera mask covering the upper half of his face, red gloves; face and mask exactly as in <Picture 2>.",
    f"{YZ} is the masked woman: long dark hair, a green-and-gold half mask over her eyes, a purple leather jacket, holding a rifle; as in <Picture 3>.",
    f"{KT} is the masked gunman: a man in a red jacket wearing an orange painted mask, holding a pistol; as in <Picture 4>.",
    "<Subject 5> is the abandoned warehouse: a vast cold-cyan industrial hall with skylights casting slanted teal light beams, steel trusses and beams from which hostages in dark police uniforms hang upside down by their bound ankles, metal grating floors, stacks of old tyres, and an upper steel catwalk with railings.",
    "<Picture 5> is the art-style reference: every frame of the target video is drawn in exactly this flat cel-shaded Japanese theatrical action anime style with clean black outlines.",
]
shots = [
    (0.000, f"a low-angle shot: hostages drop from the beams one after another as the ropes go slack."),
    (0.633, f"a medium shot of {SH} thrown down sitting on the metal grating, both hands on the floor, looking up in despair, lips closed."),
    (1.567, f"a low-angle shot of the grating ceiling and beams, only the bound feet of hanging hostages visible."),
    (2.633, f"an extreme close-up of {SH} screaming in agony, eyes squeezed shut, tears and sweat flying, mouth wide open but no words."),
    (4.167, f"a medium shot of {ZL} in front of a corrugated steel wall, spreading his arms and pointing with a smug taunting grin; he is the one who speaks here."),
    (5.667, f"an extreme close-up of {SH} sobbing, face crumpled, tears streaming, lips trembling, no words."),
    (7.967, f"a high-angle medium shot of {YZ} and {KT} standing on the high catwalk looking down over the railing; neither speaks."),
    (9.700, f"a medium shot of {SH} standing bent forward with his hands on his knees, head lifted, face twisted in grief, lips closed."),
]
desc = []
for i, (t, d) in enumerate(shots):
    desc.append(f"[Shot {i + 1}] " + ("The video begins with " if i == 0 else f"At {ts(t)}, the shot cuts to ") + d)
prompt = "\n".join([
    "subject_definitions:", *defs, "",
    "summary:",
    f"[reference generation] A live-action warehouse hostage scene redrawn shot for shot as Japanese theatrical action anime: {SH} collapses and screams, {ZL} taunts him, the masked gang watches from the catwalk. Eight shots cut at the listed times. The soundtrack is locked to the original audio; only {ZL} speaks his line and everyone else keeps their lips closed.", "",
    "retention_analysis:",
    f"{SH} (appears in Shots 2, 4, 6, 8): fully_preserved - the face, hair, clothing and colours of <Picture 1> are kept in every shot, including extreme close-ups.",
    f"{ZL} (appears in Shot 5): fully_preserved - face, mask, suit and red gloves as in <Picture 2>.",
    f"{YZ} and {KT} (appear in Shot 7): fully_preserved - as in <Picture 3> and <Picture 4>.",
    "<Subject 5> (all shots): fully_preserved - the location, lighting and cold cyan colours are kept.", "",
    "detailed_description:",
    "The target video is Japanese theatrical action anime matching <Picture 5>: cel shading, hard shadows, clean black outlines, expressive faces, cold cyan-teal light falling from the skylights. There is no on-screen text, subtitle, logo or watermark anywhere.",
    *desc,
    f"At {ts(4.70)}, {ZL} says <d>[Chinese] 你又被套！</d> Only {ZL}'s mouth moves, in sync with the words.", "",
    "overall_soundscape:", "Locked to the original soundtrack.", "",
    "non_diegetic_music:", "N/A",
])
job = {"prompt": prompt, "width": 1056, "height": 448, "length": LEN, "steps": int(os.environ.get("GEN_STEPS", 4 if os.environ.get("GEN_TURBO") else 20)), "turbo": bool(os.environ.get("GEN_TURBO")),
       "seed": int(os.environ.get("SEED_BASE", 700)), "prefix": "dmv2/ctrl_test" + os.environ.get("CTRL_TAG", ""), "images": imgs, "anchor_frames": [],
       "guides": [{"audio": AUDIO, "frame": 0}], "audios": [], "videos": [],
       "controlnet": {"video": CTRL, "patch": os.environ.get("CTRL_PATCH", "minimax_h3_fun_controlnet_union_2.0_pruned_int8_convrot.safetensors"),
                      "strength": float(os.environ.get("CTRL_STRENGTH", 1.0)), "start": 0.0, "end": 1.0}}
os.makedirs(os.path.join(HERE, "jobs"), exist_ok=True)
jp = os.path.join(HERE, "jobs", "控制测试" + os.environ.get("CTRL_TAG", "") + ".json")
json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
print("写好", jp, "帧数", LEN)
if len(sys.argv) > 1:
    env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[sys.argv[1]])
    out = os.path.join(V, "生成", "ctrl_test" + os.environ.get("CTRL_TAG", ""))
    os.makedirs(out, exist_ok=True)
    subprocess.run(["python3", f"{S}/h3_ref2va.py", jp, "--wait", out], env=env)
