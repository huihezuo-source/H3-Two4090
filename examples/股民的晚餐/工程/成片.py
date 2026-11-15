"""股民的晚餐 后期：放大 → 压标题 → 响度 → 拼对比版。
用法：python3 成片.py upscale A|B <生成mp4> [xw|wj]   → 成片/<版本>_2K.mp4（ReCaVSR 2.5×，432×768 → 1080×1920）
      python3 成片.py title A|B                      → 成片/买A股的晚餐.mp4 / 买美股的晚餐.mp4（白字标题 + 响度 -16 LUFS）
      python3 成片.py compare                        → 成片/对比版_先A股后美股.mp4
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE); OUT = os.path.join(V, "成片")
S = os.environ.get("H3_SCRIPTS", os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))  # 技能仓库的 scripts/ 目录
NAME = {"A": "A股", "B": "美股"}; TITLE = {"A": "买A股股民的晚餐", "B": "买美股股民的晚餐"}
REF_AUDIO = {"A": os.path.join(V, "参考", "买A股科技股民的晚餐_豆包.mp4")}   # A 股版音轨直接用参考片的（用户要求）
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
os.makedirs(OUT, exist_ok=True)
cmd = sys.argv[1]
if cmd == "upscale":
    ver, src = sys.argv[2], sys.argv[3]; m = sys.argv[4] if len(sys.argv) > 4 else "xw"
    env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[m])
    tmp = os.path.join(V, "生成", f"{NAME[ver]}_2K")
    subprocess.run(["python3", f"{S}/recavsr_upscale.py", src, tmp, "--scale", "2.5", "--color-fix", "wavelet", "--encoder", "h264", "--prefix", f"dinner_{ver}_2k"], env=env, check=True)
    mp4 = sorted(f for f in os.listdir(tmp) if f.endswith(".mp4"))[-1]
    # 放大结果可能没带音轨：从原生成片把声音复制回来
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(tmp, mp4), "-i", src, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", os.path.join(OUT, f"{NAME[ver]}_2K.mp4")], check=True)
    print("放大完成", os.path.join(OUT, f"{NAME[ver]}_2K.mp4"))
elif cmd == "title":
    ver = sys.argv[2]; src = os.path.join(OUT, f"{NAME[ver]}_2K.mp4"); dst = os.path.join(OUT, f"{TITLE[ver]}.mp4")
    draw = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,drawtext=fontfile='{FONT}':text='{TITLE[ver]}':fontsize=66:fontcolor=white:borderw=4:bordercolor=black@0.85:"
            f"shadowx=3:shadowy=3:shadowcolor=black@0.6:x=(w-text_w)/2:y=h*0.21")
    ins, maps = ["-i", src], ["-map", "0:v", "-map", "0:a"]
    if ver in REF_AUDIO:                      # 换成参考片音轨，按本片时长截断
        ins += ["-i", REF_AUDIO[ver]]; maps = ["-map", "0:v", "-map", "1:a", "-shortest"]
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + maps + ["-vf", draw, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], check=True)
    print("成片", dst)
elif cmd == "compare":
    a, b = os.path.join(OUT, f"{TITLE['A']}.mp4"), os.path.join(OUT, f"{TITLE['B']}.mp4"); dst = os.path.join(OUT, "对比版_先A股后美股.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-i", b, "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], check=True)
    print("对比版", dst)
