"""换人正式版后期：ReCaVSR 1.5× 放大（XW）→ 眼球微动 → 手机质感（缩到 720×1280）→ 响度 -14 → 成片/。
用法：python3 后期_公司.py <1|2|3> <生成mp4> [xw|wj]
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE)
S = os.environ.get("H3_SCRIPTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))  # 技能仓库的 scripts/ 目录; PY = os.path.expanduser("~/models/venv/bin/python")
NAME = {1: "形象1_温柔", 2: "形象2_爽朗", 3: "形象3_知性"}
i, src = int(sys.argv[1]), sys.argv[2]; m = sys.argv[3] if len(sys.argv) > 3 else "xw"
out = os.path.join(V, "成片"); os.makedirs(out, exist_ok=True); tmpd = os.path.join(V, "生成", f"woman{i}_后期"); os.makedirs(tmpd, exist_ok=True)
env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[m])
# 0. 闪回检测 + 光流补顺（跳变帧及其前后各 1 帧）
import re, ast
ORIG = os.path.join(HERE, "openjutsu", "oj_video_clean.mp4")   # 去字幕原片，用来对照
chk = subprocess.run([PY, os.path.join(HERE, "闪回检测.py"), src, "--src", ORIG], capture_output=True, text=True).stdout
big = ast.literal_eval(re.search(r"异常帧\(z>6\) \d+ 个: (\[.*?\])", chk).group(1))
bgcut = ast.literal_eval(re.search(r"背景跳切\(z>6\) \d+ 个: (\[.*?\])", chk).group(1))
print("闪回检测：\n" + chk.strip())
# 背景跳切（人没动、背景整个换掉）补帧救不了，原片此处连续就必须重出；FORCE=1 才硬做
if bgcut and "生成缺陷" in chk and not os.environ.get("FORCE"):
    sys.exit(f"背景跳切 {bgcut}：原片此处连续，属于生成缺陷，请重出这一条（FORCE=1 可强行继续）")
if big:
    fixed = os.path.join(tmpd, "0_补帧.mp4"); cur = src
    for n, i in enumerate(big):
        nxt = os.path.join(tmpd, f"0_补帧_{n}.mp4")
        subprocess.run([PY, os.path.join(HERE, "补帧.py"), cur, nxt, str(max(1, i - 1)), str(i + 1)], check=True); cur = nxt
    os.replace(cur, fixed); src = fixed
    chk2 = subprocess.run([PY, os.path.join(HERE, "闪回检测.py"), src], capture_output=True, text=True).stdout
    print("补帧后：", chk2.strip().splitlines()[-1])
# 1. 放大
subprocess.run(["python3", f"{S}/recavsr_upscale.py", src, tmpd, "--scale", "1.5", "--color-fix", "wavelet", "--encoder", "h264", "--prefix", f"swap_w{i}_up"], env=env, check=True)
up = sorted(f for f in os.listdir(tmpd) if f.endswith(".mp4") and "up" in f)[-1]; up_a = os.path.join(tmpd, "1_放大带声.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(tmpd, up), "-i", src, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", up_a], check=True)
# 2. 眼球微动 3. 手机质感 4. 响度
eye = os.path.join(tmpd, "2_眼球微动.mp4"); subprocess.run([PY, f"{S}/faceswap/eye_saccades.py", up_a, eye], check=True)
look = os.path.join(tmpd, "3_手机质感.mp4"); subprocess.run([PY, f"{S}/faceswap/phone_look.py", eye, look, "--bitrate", "1600k"], check=True)
dst = os.path.join(out, f"换人_{NAME[i]}.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", look, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dst], check=True)
print("成片", dst)
