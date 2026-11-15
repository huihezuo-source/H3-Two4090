"""一段生成视频 vs 原片同时段：逐帧轮廓匹配 + 对比图。和 逐帧对比诊断.py 同一口径（成片线条落在原片轮廓 ±2px 内的比例）。
用法：python3 段对比.py <生成mp4> <段起始绝对秒> <输出目录> [对照mp4(旧成片) 对照偏移秒]
输出：匹配曲线 png、每秒一张三联图（原片 | 新 | 红线叠加）、summary.json
"""
import cv2, numpy as np, subprocess, os, sys, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
plt.rcParams["font.family"] = ["Arial Unicode MS"]; plt.rcParams["axes.unicode_minus"] = False
V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = V + "/原片.mp4"; CROP = "crop=1280:544:0:88"; FPS = 24; W, H = 396, 168
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 16)
gen, t0, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
old = sys.argv[4] if len(sys.argv) > 4 else None; old_off = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
os.makedirs(out, exist_ok=True)

def frames(path, vf, w=W, h=H, ss=None, n=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{ss:.3f}"] if ss is not None else []) + ["-i", path] + (["-frames:v", str(n)] if n else []) + \
          ["-vf", f"{vf},scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    k = len(raw) // (w * h); return np.frombuffer(raw, np.uint8)[:k * w * h].reshape(k, h, w).copy()
def frame_at(path, t, vf, w=528, h=224):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf", f"{vf},scale={w}:{h}:flags=lanczos",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
K = np.ones((5, 5), np.uint8)
def edges(g): return cv2.Canny(cv2.GaussianBlur(g, (5, 5), 1.2), 50, 130) > 0
def match(src, o):
    eo = edges(o); es = cv2.dilate(edges(src).astype(np.uint8), K) > 0
    return (eo & es).sum() / max(eo.sum(), 1)

G = frames(gen, "null"); n = len(G)
S = frames(SRC, f"{CROP},fps={FPS}", ss=t0, n=n); n = min(n, len(S)); G, S = G[:n], S[:n]
M = np.array([match(S[i], G[i]) for i in range(n)])
res = {"frames": n, "mean": float(M.mean()), "median": float(np.median(M)), "below_0.5": float((M < 0.5).mean()), "above_0.7": float((M >= 0.7).mean()), "min": float(M.min())}
MO = None
if old:
    O = frames(old, f"fps={FPS}", ss=old_off, n=n); k = min(n, len(O))
    MO = np.array([match(S[i], O[i]) for i in range(k)])
    res["old_mean"] = float(MO.mean()); res["old_below_0.5"] = float((MO < 0.5).mean())
json.dump(res, open(out + "/summary.json", "w"), indent=1); print(json.dumps(res, indent=1))

t = t0 + np.arange(n) / FPS
sm = lambda x, k=5: np.convolve(x, np.ones(k) / k, mode="same")
plt.figure(figsize=(16, 4.5))
plt.plot(t, sm(M), color="#1f77b4", lw=1.2, label=f"新：ControlNet 控制  均值 {res['mean']:.2f}")
if MO is not None: plt.plot(t[:len(MO)], sm(MO), color="#d62728", lw=1.0, alpha=0.8, label=f"旧：Ref2VA 成片  均值 {res['old_mean']:.2f}")
plt.axhline(0.36, color="gray", ls="--", lw=1, label="乱配基线 0.36"); plt.ylim(0, 1); plt.xlabel("原片秒"); plt.ylabel("轮廓匹配度")
plt.legend(loc="lower right"); plt.title("逐帧轮廓匹配：生成段 vs 原片"); plt.tight_layout(); plt.savefig(out + "/匹配曲线.png", dpi=110); plt.close()

def label(img, txt):
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, im.width, 24], fill=(0, 0, 0)); dr.text((6, 3), txt, fill=(255, 255, 255), font=FONT)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
def overlay(o, s):
    e = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(s, cv2.COLOR_BGR2GRAY), (5, 5), 1.2), 50, 130) > 0
    o = o.copy(); o[e] = (0, 0, 255); return o
rows = []
for sec in np.arange(0, n / FPS, 1.0):
    i = int(sec * FPS); tt = t0 + sec + 0.02
    s = frame_at(SRC, tt, CROP); g = frame_at(gen, sec + 0.02, "null")
    cols = [label(s, f"原片 {tt:.2f}s"), label(g, f"新 {M[min(i, n-1)]:.2f}"), label(overlay(g, s), "红线=原片轮廓")]
    if old:
        o = frame_at(old, old_off + sec + 0.02, "null"); cols.insert(2, label(o, f"旧 {MO[min(i, len(MO)-1)]:.2f}"))
    rows.append(np.hstack(cols))
cv2.imwrite(out + "/每秒对比.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
print("图在", out)
