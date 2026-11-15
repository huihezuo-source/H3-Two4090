"""全片 ControlNet 重做（2026-11-14）：原片逐帧 Canny 控制结构，H3 Ref2VA + Fun ControlNet Union 2.0，参考图只放头像母版 + 一张动漫帧当画风，
不锚首帧，整段锁原声（换过新词的音轨）。段按真实切点切、每段 ≤243 帧（17k+5 网格），c42 在 86.5 秒拆两半、拼接时溶接 0.25 秒。

用法：python3 全片控制.py plan                → 打印分段表
      python3 全片控制.py ctrl [S01 …]        → 生成控制视频（烧入文字涂黑、逐镜头自适应阈值）+ 密度表 + 核对图
      python3 全片控制.py run xw [S01 …]      → 逐段提交到 XW 等结果，已有输出的段跳过，每段出来自动评分
      python3 全片控制.py join                → 按时间线拼 成片/拼接_草稿.mp4（c59 用原片），之后用 成片v2.py upscale / final
环境变量：GEN_STEPS（默认 20）、SEED_BASE（默认 700）、CTRL_STRENGTH（默认 1.5）
"""
import json, os, subprocess, sys, glob, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)
ROOT = os.path.dirname(V)
S = os.environ.get("H3_SCRIPTS", os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
M = os.path.join(V, "角色")
FF = os.path.join(V, "首帧", "生成尺寸")
FULL = os.path.join(V, "_scratch", "full")
SRC24 = os.path.join(FULL, "src24.mp4")                  # 原片裁 1280×544→1056×448、24fps
FR3 = os.path.join(FULL, "ocr", "fr3.json")               # 每 3 帧一次 OCR 的结果（fr3/f%05d.png 第 k 张 = 第 3k 帧）
MANUAL = {16: [[610, 120, 870, 160]], 36: [[495, 160, 735, 210]], 49: [[320, 235, 600, 290]], 52: [[320, 235, 600, 290]], 53: [[320, 235, 600, 290]],
          54: [[320, 235, 600, 290]], 55: [[320, 235, 600, 290]], 68: [[215, 385, 405, 428]]}   # OCR 在暗镜头里漏掉的水印，按镜头补
VOCAB = ["陈", "晓", "群", "重生", "版", "机器", "存储", "主力", "游姿", "汪汪", "电力", "半导", "导体", "商业", "航天", "CPO", "Cpo", "cpo", "元件", "PCB",
         "神秘", "机构", "量化", "空头", "消费", "策划", "文案", "配音", "素材", "故事", "一切", "不言", "搜", "从容", "奕市", "T344", "70/70", "3017", "作品"]
OUT = os.path.join(V, "生成", "ctrl_full")
AUD = os.path.join(V, "声音", "原片音轨_新词.wav")
FPS, W, H = 24, 1056, 448
GRID = [124, 141, 158, 175, 192, 209, 226, 243]
XFADE = 0.25
TOTAL = 157.0

spec = importlib.util.spec_from_file_location("fd", os.path.join(HERE, "分段v2.py"))
fd = importlib.util.module_from_spec(spec); spec.loader.exec_module(fd)
T0 = dict(fd.T0)
KS = sorted(T0)
END = {k: (T0[KS[i + 1]] if i + 1 < len(KS) else TOTAL) for i, k in enumerate(KS)}
DESC, SCENE = {}, {}
for _k, (_a, _b, _scene, _chars, _summ, _shots) in fd.SEGS.items():
    for n, d in _shots:
        if isinstance(n, int):
            DESC.setdefault(n, d); SCENE.setdefault(n, _scene)
DESC[59] = "a close-up of a hand holding a black remote control with a red digital countdown display; no face visible."
SCENE[59] = fd.WH_PLAIN
SPLIT = {42: [86.5]}          # 长镜头内部拆点（秒）


def grid(n):
    for g in GRID:
        if g >= n:
            return g
    raise SystemExit(f"{n} 帧超过 243")


def plan():
    """按切点贪心分段 ≤243 帧；SPLIT 里的长镜头内部拆开，前半段多生成 XFADE 秒。"""
    pieces = []   # (a, b, shot, part)
    for k in KS:
        a, b = T0[k], END[k]
        if k in SPLIT:
            cuts = [a] + SPLIT[k] + [b]
            for i in range(len(cuts) - 1):
                pieces.append((cuts[i], cuts[i + 1], k, i))
        else:
            pieces.append((a, b, k, None))
    segs, cur = [], []
    for p in pieces:
        if cur and (p[2] != cur[-1][2] and cur[-1][3] is not None):   # 拆开的长镜头：后半段单独起段，前半段单独成段
            segs.append(cur); cur = []
        if p[3] is not None and p[3] > 0:
            if cur: segs.append(cur)
            cur = []
        if cur and round((p[1] - cur[0][0]) * FPS) > 243:
            segs.append(cur); cur = []
        cur.append(p)
        if p[3] is not None and p[3] == 0:   # 长镜头前半段：到此为止
            segs.append(cur); cur = []
    if cur: segs.append(cur)
    out = []
    for i, ps in enumerate(segs):
        a, b = ps[0][0], ps[-1][1]
        xf = XFADE if (ps[-1][3] == 0) else 0.0
        n = int(round((b - a) * FPS)); L = grid(n + int(round(xf * FPS)))
        out.append(dict(name=f"S{i + 1:02d}", a=a, b=b, n=n, L=L, xfade=xf, shots=[p[2] for p in ps], parts=[p[3] for p in ps]))
    return out


SEGS = plan()
BY = {s["name"]: s for s in SEGS}


def shot_at(frame):
    t = frame / FPS + 1e-6
    k = KS[0]
    for kk in KS:
        if T0[kk] <= t: k = kk
    return k


def ctrl(names):
    import cv2, numpy as np
    os.makedirs(os.path.join(FULL, "ctrl"), exist_ok=True)
    # 逐帧文字框：第 i 帧取相邻 OCR 样本（±3 帧）的框并集，只认词表里的文字（排除戏服上的 POLICE 和脸上的误检），四周扩 10 px
    ocr = json.load(open(FR3)); FB = {}
    for fn, items in ocr.items():
        j = int(fn[1:6]) * 3
        FB[j] = [[max(0, it["x0"] - 10), max(0, it["y0"] - 10), min(W, it["x1"] + 10), min(H, it["y1"] + 10)]
                 for it in items if any(v in it["text"] for v in VOCAB)]
    def boxes_at(i, k):
        out = list(MANUAL.get(k, []))
        for j in range(i - 3, i + 4):
            out += FB.get(j, [])
        return out
    cap = cv2.VideoCapture(SRC24); frames = []
    while True:
        ok, f = cap.read()
        if not ok: break
        frames.append(f)
    NF = len(frames)
    K2 = np.ones((2, 2), np.uint8)
    THR = [(40, 110), (30, 85), (20, 60)]
    THIN = [(80, 180), (120, 250), (160, 320)]   # 密度 >0.35（满屏铁网格栅）的镜头：提高阈值、不加粗，免得控制图糊成一片白
    def canny(f, lo, hi):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); g = cv2.bilateralFilter(g, 7, 30, 5)
        e = cv2.Canny(g, lo, hi)
        return e if (lo, hi) in THIN else cv2.dilate(e, K2)
    def masked(e, i, k):
        for x0, y0, x1, y1 in boxes_at(i, k):
            e[int(y0):int(y1), int(x0):int(x1)] = 0
        return e
    # 每镜头选阈值：密度 <0.015 就降一档
    thr = {}
    for k in KS:
        i0, i1 = int(round(T0[k] * FPS)), min(int(round(END[k] * FPS)), NF)
        idx = list(range(i0, i1, max(1, (i1 - i0) // 6)))[:6]
        for lo, hi in THR:
            dens = np.mean([(masked(canny(frames[i], lo, hi), i, k) > 0).mean() for i in idx])
            thr[k] = (lo, hi, float(dens))
            if dens >= 0.015: break
        if thr[k][2] > 0.35:
            for lo, hi in THIN:
                dens = np.mean([(masked(canny(frames[i], lo, hi), i, k) > 0).mean() for i in idx])
                thr[k] = (lo, hi, float(dens))
                if dens <= 0.35: break
    rep = ["镜头  阈值     密度"] + [f"c{k:02d}  {thr[k][0]}/{thr[k][1]:<4} {thr[k][2]:.4f}" + ("  ←低" if thr[k][2] < 0.015 else ("  ←细线" if thr[k][:2] in THIN else "")) for k in KS]
    open(os.path.join(FULL, "ctrl", "密度表.txt"), "w").write("\n".join(rep)); print("\n".join(rep))
    for s in SEGS:
        if names and s["name"] not in names: continue
        i0 = int(round(s["a"] * FPS)); L = s["L"]
        outp = os.path.join(FULL, "ctrl", f"{s['name']}.mp4")
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-crf", "6", "-pix_fmt", "yuv420p", outp], stdin=subprocess.PIPE)
        sheet = []
        for j in range(L):
            i = min(i0 + j, NF - 1); k = shot_at(i)
            e = masked(canny(frames[i], thr[k][0], thr[k][1]), i, k)
            p.stdin.write(e.tobytes())
            if j % 48 == 0 and len(sheet) < 6:
                f = frames[i].copy()
                for x0, y0, x1, y1 in boxes_at(i, k): cv2.rectangle(f, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 255), 2)
                sheet.append(np.vstack([cv2.resize(f, (352, 149)), cv2.resize(cv2.cvtColor(e, cv2.COLOR_GRAY2BGR), (352, 149))]))
        p.stdin.close(); p.wait()
        cv2.imwrite(os.path.join(FULL, "ctrl", f"{s['name']}_核对.jpg"), np.hstack(sheet), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(s["name"], "控制视频", L, "帧", flush=True)


def ts(x):
    return f"{int(x) // 60:02d}:{x % 60:06.3f}"


def build(s):
    a, b, L = s["a"], s["b"], s["L"]
    shots = s["shots"]
    descs = [DESC[k] for k in shots]
    chars = [c for c in fd.CH if any("{" + c + "}" in d for d in descs)]
    imgs, subj, defs = [], {}, []
    for c in chars:
        f, desc = fd.CH[c]; mp = os.path.join(M, f)
        subj[c] = f"<Subject {len(subj) + 1}>"
        imgs.append(mp)
        defs.append(f"{subj[c]} is " + desc.format(p=f" (face, hair and mask exactly as in the head portrait <Picture {len(imgs)}>)") + ".")
    scene = SCENE[shots[0]]
    wn = f"<Subject {len(subj) + 1}>"
    defs.append(f"{wn} is {scene}.")
    style = next((os.path.join(FF, f"c{k:02d}.png") for k in shots if os.path.exists(os.path.join(FF, f"c{k:02d}.png"))), None)
    if style:
        imgs.append(style)
        defs.append(f"<Picture {len(imgs)}> is the art-style reference: every frame of the target video is drawn in exactly this flat cel-shaded Japanese theatrical action anime style with clean black outlines (it is only a style reference, not a composition to copy).")
    fmt = dict(subj)
    for c in fd.CH: fmt.setdefault(c, fd.NAME[c])
    desc_lines = []
    seen = set()
    for k, part in zip(shots, s["parts"]):
        if k in seen: continue
        seen.add(k)
        t = max(0.0, T0[k] - a) if part in (None, 0) else 0.0
        d = DESC[k].format(**fmt)
        if part == 1:
            d = "the same shot continues: " + d
        desc_lines.append(f"[Shot {len(desc_lines) + 1}] " + ("The video begins with " if not desc_lines else f"At {ts(t)}, the shot cuts to ") + d)
    seg_lines = [(t - a, sp, txt) for t, sp, txt in fd.LINES if a - 0.3 <= t < a + L / FPS]
    line_txt, speakers = [], set()
    for t, sp, txt in seg_lines:
        if sp.endswith("_off"):
            line_txt.append(f"At {ts(max(t, 0))}, an off-screen voice ({fd.NAME[sp[:-4]]}, not visible) says <d>[Chinese] {txt}</d> Nobody on screen moves their lips.")
        else:
            who = fmt[sp]; speakers.add(who)
            line_txt.append(f"At {ts(max(t, 0))}, {who} says <d>[Chinese] {txt}</d> Only {who}'s mouth moves, in sync with the words.")
    voice = (f"The soundtrack is locked to the original audio; {', '.join(sorted(speakers)) or 'the listed characters'} speak their lines in sync with it and everyone else keeps their lips closed."
             if seg_lines else "Nobody speaks in this segment; every visible mouth stays closed.")
    ret = [f"{subj[c]}: fully_preserved - face, hair, mask, clothing and colours exactly as in the head portrait." for c in chars]
    ret.append(f"{wn}: fully_preserved - the location, lighting and colours are kept.")
    prompt = "\n".join([
        "subject_definitions:", *defs, "",
        "summary:",
        f"[reference generation] A live-action scene redrawn shot for shot as Japanese theatrical action anime, {len(desc_lines)} shot(s) cut at the listed times. {voice}", "",
        "retention_analysis:", *ret, "",
        "detailed_description:",
        "The target video is Japanese theatrical action anime: cel shading, hard shadows, clean black outlines, expressive faces that keep the intensity of the live performance" + (", cold cyan-teal light falling from the skylights" if scene in (fd.WH, fd.WH_PLAIN) else "") + ". Every person present in the live scene is drawn, including small or distant figures. There is no on-screen text, subtitle, logo or watermark anywhere.",
        *desc_lines, *line_txt, "",
        "overall_soundscape:", "Locked to the original soundtrack.", "",
        "non_diegetic_music:", "N/A",
    ])
    os.makedirs(os.path.join(FULL, "aud"), exist_ok=True)
    wav = os.path.join(FULL, "aud", f"{s['name']}.wav")
    if not os.path.exists(wav):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{L / FPS:.3f}", "-i", AUD, "-ar", "48000", "-ac", "2", wav], check=True)
    job = {"prompt": prompt, "width": W, "height": H, "length": L, "steps": int(os.environ.get("GEN_STEPS", 20)), "turbo": False,
           "seed": int(os.environ.get("SEED_BASE", 700)) + SEGS.index(s), "prefix": f"dmv2/full_{s['name']}", "images": imgs, "anchor_frames": [],
           "guides": [{"audio": wav, "frame": 0}], "audios": [], "videos": [],
           "controlnet": {"video": os.path.join(FULL, "ctrl", f"{s['name']}.mp4"), "patch": "minimax_h3_fun_controlnet_union_2.0_pruned_int8_convrot.safetensors",
                          "strength": float(os.environ.get("CTRL_STRENGTH", 1.5)), "start": 0.0, "end": 1.0}}
    os.makedirs(os.path.join(HERE, "jobs"), exist_ok=True)
    jp = os.path.join(HERE, "jobs", f"full_{s['name']}.json")
    json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
    return jp


def latest(name):
    fs = sorted(glob.glob(os.path.join(OUT, name, "*.mp4")), key=os.path.getmtime)
    return fs[-1] if fs else None


def run(machine, names):
    env = dict(os.environ, COMFY_CLIENT_ID="mac-claude", COMFY_URL={"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[machine])
    log = open(os.path.join(OUT, "run_log.txt"), "a")
    for s in SEGS:
        if names and s["name"] not in names: continue
        od = os.path.join(OUT, s["name"]); os.makedirs(od, exist_ok=True)
        if latest(s["name"]):
            print(s["name"], "已有输出，跳过"); continue
        jp = build(s)
        import time; t = time.time()
        print(f"== {s['name']} {s['a']:.3f}-{s['b']:.3f} {s['L']}帧 镜头{s['shots']} 开始 {time.strftime('%H:%M:%S')}", flush=True)
        subprocess.run(["python3", f"{S}/h3_ref2va.py", jp, "--wait", od], env=env)
        f = latest(s["name"])
        line = f"{s['name']} {time.strftime('%H:%M:%S')} {(time.time() - t) / 60:.1f}分 " + (os.path.basename(f) if f else "失败")
        if f:
            ev = os.path.join(FULL, "eval", s["name"])
            r = subprocess.run([os.path.expanduser("~/models/venv/bin/python"), os.path.join(HERE, "段对比.py"), f, f"{s['a']:.3f}", ev], capture_output=True, text=True)
            try:
                sm = json.load(open(os.path.join(ev, "summary.json"))); line += f" 匹配 {sm['mean']:.2f} 低于0.5 {sm['below_0.5']:.0%}"
            except Exception as e:
                line += f" 评分失败 {e}"
        print(line, flush=True); log.write(line + "\n"); log.flush()


def join():
    import re
    tmp = os.path.join(V, "成片", "_cut_ctrl"); os.makedirs(tmp, exist_ok=True)
    REF = os.path.join(V, "原片.mp4")
    items = []   # (label, file, start_in_file, duration)
    for s in SEGS:
        f = latest(s["name"])
        if not f: raise SystemExit(f"缺 {s['name']}")
        a, b = s["a"], s["b"]
        if 59 in s["shots"]:   # c59 用原片
            items.append((s["name"] + "a", f, 0.0, T0[59] - a))
            items.append(("c59", REF, T0[59], END[59] - T0[59]))
            items.append((s["name"] + "b", f, END[59] - a, b - END[59]))
        else:
            items.append((s["name"], f, 0.0, b - a + s["xfade"]))
    lst = []
    for i, (label, f, st, d) in enumerate(items):
        o = os.path.join(tmp, f"{label}.mov")
        if label == "c59":
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.3f}", "-t", f"{d:.3f}", "-i", f,
                   "-vf", f"crop=1280:544:0:88,delogo=x=345:y=306:w=290:h=52,scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p", "-an"]
        else:
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.3f}", "-t", f"{d:.3f}", "-i", f, "-vf", f"fps={FPS},scale={W}:{H},format=yuv420p", "-an"]
        subprocess.run(cmd + ["-c:v", "libx264", "-crf", "12", "-preset", "fast", o], check=True)
        seg = BY.get(label)
        if lst and lst[-1][3] > 0:   # 上一条带溶接
            pl, po, pd, pxf = lst.pop()
            m = os.path.join(tmp, f"{pl}_{label}.mov")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", po, "-i", o, "-filter_complex",
                            f"[0:v][1:v]xfade=transition=fade:duration={pxf:.3f}:offset={pd - pxf:.3f},format=yuv420p",
                            "-c:v", "libx264", "-crf", "12", "-preset", "fast", m], check=True)
            label, o, d = f"{pl}_{label}", m, pd - pxf + d
            lst.append((label, o, d, seg["xfade"] if seg else 0.0))
        else:
            lst.append((label, o, d, seg["xfade"] if seg else 0.0))
        print(label, f"{d:.3f}s", flush=True)
    open(os.path.join(tmp, "list.txt"), "w").write("\n".join(f"file '{o}'" for _, o, _, _ in lst))
    joined = os.path.join(tmp, "joined.mov")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", joined], check=True)
    out = os.path.join(V, "成片", "拼接_草稿.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", AUD, "-map", "0:v", "-map", "1:a", "-t", f"{TOTAL:.3f}",
                    "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out], check=True)
    print(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "plan":
        for s in SEGS:
            print(f"{s['name']} {s['a']:8.3f}-{s['b']:8.3f} {s['n']:4d}帧 生成{s['L']:4d} 溶接{s['xfade']} 镜头{s['shots']}")
        print("段数", len(SEGS), "总帧", sum(s["n"] for s in SEGS))
    elif cmd == "ctrl":
        ctrl(sys.argv[2:])
    elif cmd == "run":
        os.makedirs(OUT, exist_ok=True)
        run(sys.argv[2], sys.argv[3:])
    elif cmd == "build":
        for n in sys.argv[2:]: print(build(BY[n]))
    elif cmd == "join":
        join()
