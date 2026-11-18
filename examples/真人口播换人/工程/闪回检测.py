"""找视频里的闪回和背景跳切。两项指标，任何一项报警都要处理，不能看一眼条带就放过：
  A 整帧跳变：相邻帧灰度平均绝对差的 z 分数 > 6
  B 背景跳切：只看画面四周（人物以外）的区域，相邻帧相关系数突然掉下去（z > 6）——人没动、背景整个换掉的那种“秒切场景”
带 --src 原片 时，逐处对照原片同一帧：原片此处连续（z < 3）＝生成缺陷，必须重出或补帧；原片此处也跳＝原片本来就有切点。
用法：python3 闪回检测.py in.mp4 [输出目录] [--src 原片.mp4]
"""
import sys, os, subprocess, numpy as np, cv2
args = [a for a in sys.argv[1:]]
ref = None
if "--src" in args:
    k = args.index("--src"); ref = args[k + 1]; del args[k:k + 2]
src = args[0]; out = args[1] if len(args) > 1 else None
W, H = 144, 256
MASK = np.ones((H, W), bool); MASK[int(H * 0.30):, int(W * 0.24):int(W * 0.76)] = False   # 去掉中间的人，留天空以下的两侧和上方背景
MASK[:int(H * 0.22), :] = False                                                            # 纯天空没有纹理，不算

def measure(path):
    cap = cv2.VideoCapture(path); fps = cap.get(5); prev = None; d = []; c = []
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (W, H)).astype(np.float32)
        if prev is None: d.append(0.0); c.append(0.0)
        else:
            d.append(float(np.abs(g - prev).mean()))
            a, b = g[MASK] - g[MASK].mean(), prev[MASK] - prev[MASK].mean()
            c.append(1.0 - float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6)))   # 1-相关系数，越大越不像
        prev = g
    return np.array(d), np.array(c), fps

def zscore(x):
    med = np.median(x[1:]); mad = np.median(np.abs(x[1:] - med)) + 1e-6
    return (x - med) / (1.4826 * mad), med

d, c, fps = measure(src); zd, medd = zscore(d); zc, medc = zscore(c)
big = [i for i in range(1, len(d)) if zd[i] > 6]
bg = [i for i in range(1, len(c)) if zc[i] > 6]
sus = [i for i in range(1, len(d) - 1) if zd[i] > 6 and (zd[i + 1] > 6 or zd[i - 1] > 6)]   # 跳出又跳回
hits = sorted(set(big) | set(bg))
print(f"帧数 {len(d)} 中位差 {medd:.2f} 异常帧(z>6) {len(big)} 个: {big[:20]}  背景跳切(z>6) {len(bg)} 个: {bg[:20]}  闪回候选: {sus[:20]}")
if ref and hits:
    rd, rc, _ = measure(ref); rzd, _ = zscore(rd); rzc, _ = zscore(rc)
    for i in hits:
        lo, hi = max(1, i - 1), min(len(rd) - 1, i + 1)
        if lo > hi: continue
        sz = max(float(rzd[lo:hi + 1].max()), float(rzc[lo:hi + 1].max()))
        verdict = "原片此处也跳（原片切点）" if sz > 6 else ("原片此处连续 → 生成缺陷，重出或补帧" if sz < 3 else "原片此处运动较大，逐帧对照条带再定")
        print(f"  第 {i} 帧 {i / fps:.2f}s：整帧 z={zd[i]:.1f} 背景 z={zc[i]:.1f}；原片 z={sz:.1f} → {verdict}")
elif hits and not ref:
    print("  有报警但没给 --src：不许凭条带判成“转头”，带原片再跑一次")
if out and hits:
    os.makedirs(out, exist_ok=True)
    for i in hits[:6]:
        t0 = max(0, (i - 3)) / fps
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.4f}", "-i", src, "-frames:v", "7", "-vf", "scale=200:-2,tile=7x1:padding=2:color=white", "-frames:v", "1", f"{out}/闪回_第{i}帧_{i/fps:.2f}s.jpg"])
    print("条带：", out)
