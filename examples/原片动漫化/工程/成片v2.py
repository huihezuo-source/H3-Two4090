"""v2 成片三步：
  python3 成片v2.py join      各段按原片时间线拼成 1056×448/24fps 草稿（c59 倒计时用原片），配上换好新词的原片音轨 → 成片/拼接_草稿.mp4
  python3 成片v2.py upscale   ReCaVSR 2.5 倍（XW，COMFY_URL 默认 18189）→ 成片/拼接_2K.mp4
  python3 成片v2.py final [拼接_2K.mp4|拼接_草稿.mp4]   放进 1920×1080 宽银幕（上下黑边）、叠标签和字幕、片尾字、响度 -14 → 成片/散户动漫版v2_成片.mp4
"""
import glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
ROOT = os.path.dirname(V)
S = os.environ.get("H3_SCRIPTS", os.path.join(HERE, "..", "..", "..", "scripts"))   # 本仓库的 scripts 目录
G = os.path.join(V, "生成", os.environ.get("FARM_OUT", "farm"))
OUT = os.path.join(V, "成片")
AUD = os.path.join(V, "声音", "原片音轨_新词.wav")
REF = os.path.join(V, "原片.mp4")
W0, H0, FPS = 1056, 448, 24
os.makedirs(OUT, exist_ok=True)

ORDER = [("A1", 0.0, 5.667), ("A2", 5.667, 12.933), ("B1", 12.933, 18.033), ("B2", 18.033, 24.900), ("C", 24.900, 33.000), ("D", 33.000, 40.533), ("T", 40.533, 50.300),
         ("E", 50.300, 56.733), ("E2", 56.733, 61.433), ("F1", 61.433, 67.800), ("F2", 67.800, 73.467), ("G", 73.467, 80.467), ("H1", 80.467, 89.300), ("H2", 89.300, 92.800), ("I", 92.800, 101.367),
         ("J", 101.367, 111.733), ("K", 111.733, 121.167), ("c59", 121.167, 124.133), ("L", 124.133, 132.800),
         ("M1", 132.800, 138.533), ("M2", 138.533, 142.800), ("N1", 142.800, 147.133), ("N2", 147.133, 157.000)]
# A/B/F/H/N 超过 250 帧会把显存挤爆（每步慢十倍），按真实切点拆成小段；H 是一个长镜头，在 89.3 秒两句话之间拆开，
# H1 多生成 0.25 秒，拼接时和 H2 的开头溶接，遮掉镜头中间的接缝。
BLEND = {"H1": 0.25, "B2": 0.25}   # B2 也多生成到 25.4 秒并锚定 c09，和 C 段在 24.9 秒溶接   # 段名 → 与下一段溶接的秒数（该段生成时已多出这段时长）
TOTAL = 157.0

# 字幕：开始, 结束, 文字（原片台词；16、17 是新词）
SUBS = [
    (27.3, 28.3, "救我！"), (28.7, 31.3, "你还没亏爆仓不代表你有本事"), (31.4, 32.7, "是我们还没玩够"),
    (33.2, 34.2, "你们是什么人？"), (35.3, 37.5, "我们是爱死你们这帮散户的人"),
    (41.1, 42.2, "快点抬轿"), (42.3, 43.8, "你先把肉割了"), (44.3, 45.0, "快点！"),
    (59.0, 60.5, "你被套了"), (62.0, 63.0, "不要啊"), (67.4, 68.2, "再见！"), (72.4, 73.4, "你又被套！"),
    (78.0, 79.5, "你们杀了我吧！"), (80.6, 81.9, "你不是很了不起吗？"), (82.1, 84.9, "说什么顶级牛散，超越盈利周期"),
    (85.25, 89.1, "你现在跟真正的高手差得远呢，人家早就空仓了"), (89.75, 94.5, "你呢，追涨杀跌，天天接盘，标准的韭菜"),
    (94.0, 97.0, "恭喜割肉，可惜你割晚了"), (100.0, 102.8, "现在是下午三点零三秒，一秒一个！"),
    (104.0, 104.8, "遵命！"), (115.8, 116.6, "为什么？"), (118.3, 120.5, "散户，你走啊"), (121.3, 123.5, "散户，你走啊"),
]
# 标签：开始, 结束, 文字, x, y（相对画面 0–1），big=人质板块名字号更大
TAGS = [
    (12.95, 15.5, "电力", 0.43, 0.30), (12.95, 15.5, "半导体", 0.75, 0.30),
    (17.0, 18.0, "PCB", 0.90, 0.30), (18.05, 19.6, "存储", 0.30, 0.70),
    (24.95, 26.0, "机器人", 0.93, 0.93), (26.5, 27.9, "商业航天", 0.20, 0.50),
    (34.55, 36.4, "游资", 0.42, 0.08), (36.45, 37.8, "量化", 0.17, 0.40), (36.45, 37.8, "主力", 0.67, 0.10),
    (42.25, 43.95, "主力", 0.67, 0.12), (44.85, 48.1, "主力", 0.44, 0.10), (48.2, 50.25, "量化", 0.44, 0.22),
    (50.35, 51.3, "CPO", 0.37, 0.50), (51.35, 52.55, "CPO", 0.40, 0.75), (52.6, 53.4, "空头", 0.50, 0.10),
    (53.45, 54.2, "游资", 0.42, 0.08), (54.25, 55.3, "神秘机构", 0.65, 0.20), (55.35, 56.7, "主力", 0.50, 0.10),
    (56.75, 58.4, "CPO", 0.33, 0.93), (58.45, 61.4, "CPO", 0.80, 0.85), (61.45, 62.4, "主力", 0.65, 0.10),
    (62.45, 63.0, "PCB", 0.42, 0.30), (62.45, 63.0, "半导体", 0.42, 0.60),
    (64.5, 66.9, "神秘机构", 0.70, 0.10), (66.95, 67.8, "量化", 0.40, 0.20), (72.0, 73.45, "主力", 0.45, 0.10),
    (75.8, 77.5, "游资", 0.45, 0.10), (75.8, 77.5, "汪汪队", 0.50, 0.30),
    (80.5, 92.8, "主力", 0.50, 0.05), (93.7, 101.35, "主力", 0.50, 0.10),
    (101.4, 103.6, "神秘机构", 0.90, 0.05), (103.65, 105.1, "量化", 0.10, 0.05), (105.15, 105.9, "神秘机构", 0.90, 0.05),
    (105.95, 106.8, "电力 消费电子", 0.45, 0.60), (105.95, 106.8, "元件", 0.72, 0.85),
    (117.95, 121.1, "商业航天", 0.40, 0.25),
]
BIG = {"电力", "半导体", "元件", "CPO", "PCB", "存储", "机器人", "商业航天", "电力 消费电子"}
END = (150.5, 157.0, "一切尽在不言中")
FONT = "Hiragino Sans GB"


PICK = {"B2": "ref_seg_B2_00001_.mp4"}   # B2 第四版（XW 出的 00001，23:03）；其余段取最新文件   # 段 → 指定用哪个文件名（不指定就用最新的）


def latest(k):
    fs = sorted(glob.glob(os.path.join(G, f"seg_{k}", "*.mp4")), key=os.path.getmtime)
    if not fs:
        raise SystemExit(f"缺 {k} 段")
    if k in PICK:
        return os.path.join(G, f"seg_{k}", PICK[k])
    return fs[-1]


def join():
    tmp = os.path.join(OUT, "_cut")
    os.makedirs(tmp, exist_ok=True)
    lst = []
    for k, a, b in ORDER:
        d = b - a
        o = os.path.join(tmp, f"{k}.mov")
        if k == "c59":
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", REF,
                   "-vf", f"crop=1280:544:0:88,delogo=x=345:y=306:w=290:h=52,scale={W0}:{H0}:flags=lanczos,fps={FPS},format=yuv420p", "-an"]
        else:
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", latest(k), "-t", f"{d + BLEND.get(k, 0):.3f}", "-vf", f"fps={FPS},scale={W0}:{H0},format=yuv420p", "-an"]
        subprocess.run(cmd + ["-c:v", "libx264", "-crf", "12", "-preset", "fast", o], check=True)
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames",
                            "-of", "csv=p=0", o], capture_output=True, text=True).stdout.strip()
        print(k, f"{d:.3f}s", n, "帧", flush=True)
        if lst and lst[-1][0] in BLEND:   # 上一段要和这一段溶接：合成一个文件
            pk, po, pd = lst.pop()
            m = os.path.join(tmp, f"{pk}_{k}.mov")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", po, "-i", o, "-filter_complex",
                            f"[0:v][1:v]xfade=transition=fade:duration={BLEND[pk]:.3f}:offset={pd:.3f},format=yuv420p",
                            "-c:v", "libx264", "-crf", "12", "-preset", "fast", m], check=True)
            n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames",
                                "-of", "csv=p=0", m], capture_output=True, text=True).stdout.strip()
            print(f"{pk}+{k} 溶接 {BLEND[pk]}s →", n, "帧", flush=True)
            k, o, d = f"{pk}_{k}", m, pd + d
        lst.append((k, o, d))
    open(os.path.join(tmp, "list.txt"), "w").write("\n".join(f"file '{o}'" for _, o, _ in lst))
    joined = os.path.join(tmp, "joined.mov")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", joined], check=True)
    out = os.path.join(OUT, "拼接_草稿.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", AUD, "-map", "0:v", "-map", "1:a", "-t", f"{TOTAL:.3f}",
                    "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out], check=True)
    print(out)


def upscale():
    env = dict(os.environ)
    env.setdefault("COMFY_URL", "http://127.0.0.1:18189")
    env["COMFY_CLIENT_ID"] = "mac-claude"
    dl = os.path.join(OUT, "_2k")
    subprocess.run(["python3", f"{S}/recavsr_upscale.py", os.path.join(OUT, "拼接_草稿.mp4"), dl, "--scale", "2", "--color-fix", "wavelet",
                    "--prefix", "dmv2_2k", "--timeout", "7200"], env=env, check=True)
    f = sorted(glob.glob(os.path.join(dl, "*.mp4")), key=os.path.getmtime)[-1]
    os.replace(f, os.path.join(OUT, "拼接_2K.mp4"))
    print(os.path.join(OUT, "拼接_2K.mp4"))


def final(src):
    W, H = 1920, 1080
    PW, PH = 1920, 815
    TOP = (H - PH) // 2
    ts = lambda t: f"0:{int(t // 60):02d}:{t % 60:05.2f}"
    ass = [f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FONT},50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,2,40,40,{TOP // 2 - 25},1
Style: Tag,{FONT},44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3.5,2,5,0,0,0,1
Style: TagBig,{FONT},60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,2,5,0,0,0,1
Style: End,{FONT},58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,6,0,1,2,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""]
    for a, b, t in SUBS:
        ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{t}")
    for a, b, t, x, y in TAGS:
        px, py = int(x * PW), TOP + int(y * PH)
        st = "TagBig" if t in BIG else "Tag"
        ass.append(f"Dialogue: 1,{ts(a)},{ts(b)},{st},,0,0,0,,{{\\pos({px},{py})\\fad(60,60)}}{t}")
    a, b, t = END
    ass.append(f"Dialogue: 2,{ts(a)},{ts(b)},End,,0,0,0,,{{\\pos({W // 2},{H - TOP // 2})\\fad(600,400)}}{t}")   # 片尾字放下方黑边正中
    af = os.path.join(OUT, "_subs.ass")
    open(af, "w").write("\n".join(ass) + "\n")
    vf = f"scale={PW}:{PH}:flags=lanczos,pad={W}:{H}:0:{TOP}:black,fade=t=out:st={TOTAL - 0.8}:d=0.8,subtitles={af}"
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", AUD, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    j = json.loads(re.findall(r"\{[^{}]*\}", m)[-1])
    la = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,afade=t=out:st={TOTAL - 0.9}:d=0.9")
    out = os.path.join(OUT, "散户动漫版v2_成片.mp4")
    # 音轨直接用原片（换过新词的）wav，不用放大输出里重编码过的音轨（ReCaVSR 的 SaveVideo 会把音频压糊、偏 21 ms）
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", AUD, "-map", "0:v", "-map", "1:a", "-vf", vf, "-af", la, "-t", f"{TOTAL:.3f}", "-c:v", "libx264", "-crf", "17",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out], check=True)
    print(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "join":
        join()
    elif cmd == "upscale":
        upscale()
    elif cmd == "final":
        final(sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "拼接_2K.mp4"))
