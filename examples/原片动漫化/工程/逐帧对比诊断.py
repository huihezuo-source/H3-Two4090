"""原片 vs 成片 逐帧结构对比。输出：曲线图、最差时刻图、锚帧后漂移图、按镜头的表。"""
import cv2, numpy as np, subprocess, os, sys, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
plt.rcParams["font.family"] = ["Arial Unicode MS"]; plt.rcParams["axes.unicode_minus"] = False
V = "<视频目录>/整活_散户动漫版/v2原角色版"
SRC, OUT = V + "/原片.mp4", V + "/成片/拼接_草稿.mp4"
FF = V + "/首帧/原始"
D = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 396, 168, 24
CROP = "crop=1280:544:0:88"
FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

def frames(path, vf, w=W, h=H):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"{vf},scale={w}:{h}:flags=area,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (w * h)
    return np.frombuffer(raw, np.uint8)[:n * w * h].reshape(n, h, w).copy()

def frame_at(path, t, vf, w=528, h=224):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf",
                          f"{vf},scale={w}:{h}:flags=lanczos", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)

shots = []
for ln in open(os.path.dirname(V) + "/全片/shots.tsv"):
    p = ln.split()
    if len(p) >= 3 and p[0].isdigit(): shots.append((int(p[0]), float(p[1]), float(p[2])))

print("解码…"); S = frames(SRC, f"{CROP},fps={FPS}"); O = frames(OUT, f"fps={FPS}")
n = min(len(S), len(O)); S, O = S[:n], O[:n]; print("帧数", len(S), len(O), "用", n)

K = np.ones((5, 5), np.uint8)
def edges(g, lo=50, hi=130):
    return cv2.Canny(cv2.GaussianBlur(g, (5, 5), 1.2), lo, hi) > 0
def match(src, out):
    """成片画的线有多少落在原片轮廓 ±2px 内（0~1）。原片有纹理所以不反过来算。"""
    eo = edges(out); es = cv2.dilate(edges(src).astype(np.uint8), K) > 0
    return (eo & es).sum() / max(eo.sum(), 1)

print("轮廓匹配…")
M = np.array([match(S[i], O[i]) for i in range(n)])
# 乱配基线：成片第 i 帧对原片错位 3 秒 / 随机帧
rng = np.random.default_rng(0)
B_shift = np.array([match(S[(i + 72) % n], O[i]) for i in range(0, n, 3)])
B_rand = np.array([match(S[rng.integers(n)], O[i]) for i in range(0, n, 3)])
# 自身上限：原片对原片（加一点模糊）
B_self = np.array([match(S[i], cv2.GaussianBlur(S[i], (3, 3), 0.8)) for i in range(0, n, 10)])
# 首帧（H3 Image 静态转绘）对原片同一帧：静态转绘能做到多准
FFM = {}
for num, a, b in shots:
    f = f"{FF}/c{num:02d}.png"
    if os.path.exists(f):
        g = cv2.cvtColor(cv2.resize(cv2.imread(f), (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        FFM[num] = match(S[min(int(round(a * FPS)), n - 1)], g)

print("光流…")
def flow_energy(X):
    e = np.zeros(len(X))
    for i in range(1, len(X)):
        fl = cv2.calcOpticalFlowFarneback(X[i - 1], X[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        e[i] = np.linalg.norm(fl, axis=2).mean()
    return e
ES, EO = flow_energy(S), flow_energy(O)
dS = np.r_[0, np.abs(S[1:].astype(np.int16) - S[:-1].astype(np.int16)).mean(axis=(1, 2))]
dO = np.r_[0, np.abs(O[1:].astype(np.int16) - O[:-1].astype(np.int16)).mean(axis=(1, 2))]

# 切点：成片里的硬跳（帧差大且光流不连续）
def cuts(d, thr):
    idx = np.where(d > thr)[0]; out = []
    for i in idx:
        if not out or i - out[-1] > 4: out.append(i)
    return out
cutS = cuts(dS, 22); cutO = cuts(dO, 18)
true_cuts = [a for _, a, _ in shots if a > 0]
rows = []  # 按镜头
for num, a, b in shots:
    i0, i1 = int(round(a * FPS)), min(int(round(b * FPS)), n)
    if i1 - i0 < 6: continue
    seg = M[i0 + 2:i1 - 1]
    first = M[i0 + 1]
    tail = M[max(i0 + 2, i1 - FPS):i1 - 1].mean() if i1 - i0 > FPS + 4 else np.nan
    # 动作时间差：光流曲线互相关
    lag = np.nan
    if i1 - i0 > 36:
        x, y = ES[i0 + 2:i1 - 1], EO[i0 + 2:i1 - 1]; x = x - x.mean(); y = y - y.mean()
        if x.std() > 1e-3 and y.std() > 1e-3:
            L = min(18, len(x) // 3); best = None
            for l in range(-L, L + 1):
                if l >= 0: c = (x[l:] * y[:len(y) - l]).sum()
                else: c = (x[:l] * y[-l:]).sum()
                c /= (len(x) - abs(l))
                if best is None or c > best[0]: best = (c, l)
            lag = best[1] / FPS
    # 成片在镜头内部的硬跳
    inner = [c / FPS for c in cutO if i0 + 3 < c < i1 - 3]
    # 成片在该镜头起点附近的切点与真实切点偏差
    near = [c for c in cutO if abs(c - i0) <= 30]
    off = (min(near, key=lambda c: abs(c - i0)) - i0) / FPS if near and a > 0 else np.nan
    ratio = EO[i0 + 2:i1 - 1].sum() / max(ES[i0 + 2:i1 - 1].sum(), 1e-6)
    rows.append(dict(shot=num, t0=a, dur=b - a, mean=seg.mean(), mn=seg.min(), first=first, tail=tail, ff=FFM.get(num, np.nan),
                     lag=lag, inner=inner, cut_off=off, motion_ratio=ratio))

summ = dict(frames=n, match_mean=float(M.mean()), match_median=float(np.median(M)),
            below_050=float((M < 0.5).mean()), below_040=float((M < 0.4).mean()),
            baseline_shift3s=float(B_shift.mean()), baseline_random=float(B_rand.mean()), self_upper=float(B_self.mean()),
            firstframe_mean=float(np.nanmean(list(FFM.values()))), firstframe_n=len(FFM),
            shot_first_mean=float(np.nanmean([r["first"] for r in rows])), shot_tail_mean=float(np.nanmean([r["tail"] for r in rows])),
            cuts_src_detected=len(cutS), cuts_out_detected=len(cutO),
            inner_jumps=sum(len(r["inner"]) for r in rows),
            lag_abs_mean=float(np.nanmean([abs(r["lag"]) for r in rows if not np.isnan(r["lag"])])),
            lag_over_0_25=int(sum(1 for r in rows if not np.isnan(r["lag"]) and abs(r["lag"]) > 0.25)),
            cut_off_abs_mean=float(np.nanmean([abs(r["cut_off"]) for r in rows if not np.isnan(r["cut_off"])])),
            cut_off_over_0_2=int(sum(1 for r in rows if not np.isnan(r["cut_off"]) and abs(r["cut_off"]) > 0.2)),
            motion_ratio_median=float(np.median([r["motion_ratio"] for r in rows])))
json.dump(dict(summary=summ, rows=rows), open(D + "/diag.json", "w"), ensure_ascii=False, indent=1, default=float)
np.save(D + "/M.npy", M); np.save(D + "/ES.npy", ES); np.save(D + "/EO.npy", EO)
print(json.dumps(summ, ensure_ascii=False, indent=1))
print("\n镜头  起点   时长  匹配均值 最低  首帧(H3图) 段首  段尾   动作时差  动作量比 切点偏差 段内硬跳")
for r in rows:
    print(f"c{r['shot']:02d} {r['t0']:6.2f} {r['dur']:5.2f}  {r['mean']:.2f}   {r['mn']:.2f}  {r['ff']:.2f}     {r['first']:.2f} {r['tail']:.2f}   {r['lag']:+.2f}    {r['motion_ratio']:.2f}   {r['cut_off']:+.2f}   {','.join(f'{t:.1f}' for t in r['inner'])}")

# ---- 图 1：曲线 ----
t = np.arange(n) / FPS
sm = lambda x, k=9: np.convolve(x, np.ones(k) / k, mode="same")
fig, ax = plt.subplots(3, 1, figsize=(22, 11), sharex=True, gridspec_kw=dict(height_ratios=[3, 2, 1.4]))
ax[0].plot(t, sm(M), lw=0.9, color="#1f77b4", label="成片每帧轮廓落在原片轮廓上的比例")
ax[0].axhline(summ["baseline_random"], color="gray", ls="--", lw=1, label=f"乱配基线（随机帧）{summ['baseline_random']:.2f}")
ax[0].axhline(summ["self_upper"], color="green", ls=":", lw=1, label=f"上限（原片对自己）{summ['self_upper']:.2f}")
for num, a, b in shots:
    ax[0].axvline(a, color="k", alpha=0.15, lw=0.6)
    if num in FFM: ax[0].plot(a, FFM[num], "o", color="orange", ms=4)
ax[0].plot([], [], "o", color="orange", label="每镜头首帧（H3 Image 静态转绘）对原片的匹配")
ax[0].set_ylim(0, 1); ax[0].set_ylabel("轮廓匹配度"); ax[0].legend(loc="lower right", fontsize=9)
ax[0].set_title("原片 vs 成片：逐帧轮廓匹配（竖线=原片切点）", fontsize=13)
ax[1].plot(t, sm(ES, 5), lw=0.8, color="#333", label="原片 动作量（光流）")
ax[1].plot(t, sm(EO, 5), lw=0.8, color="#d62728", label="成片 动作量（光流）")
for num, a, b in shots: ax[1].axvline(a, color="k", alpha=0.15, lw=0.6)
ax[1].set_ylabel("平均光流 px/帧"); ax[1].legend(loc="upper right", fontsize=9); ax[1].set_ylim(0, max(np.percentile(ES, 99), np.percentile(EO, 99)) * 1.1)
for r in rows:
    if not np.isnan(r["cut_off"]): ax[2].bar(r["t0"], r["cut_off"], width=0.8, color="#d62728" if abs(r["cut_off"]) > 0.2 else "#999")
    for ti in r["inner"]: ax[2].plot(ti, 0, "x", color="purple", ms=7)
ax[2].axhline(0, color="k", lw=0.6); ax[2].set_ylabel("切点偏差 秒\n（×=段内多出的硬跳）"); ax[2].set_xlabel("秒")
ax[2].set_xlim(0, n / FPS)
plt.tight_layout(); plt.savefig(D + "/对比_逐帧曲线.png", dpi=110); plt.close()

# ---- 图 2：最差时刻（不同镜头各取最低点）----
font = ImageFont.truetype(FONT, 20); font_s = ImageFont.truetype(FONT, 16)
def label(img, txt, big=False):
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, im.width, 26], fill=(0, 0, 0)); dr.text((6, 3), txt, fill=(255, 255, 255), font=font if big else font_s)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
def overlay(out_img, src_img):
    g = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY); e = cv2.Canny(cv2.GaussianBlur(g, (5, 5), 1.2), 50, 130) > 0
    o = out_img.copy(); o[e] = (0, 0, 255); return o
worst = sorted([r for r in rows if r["dur"] > 1.0], key=lambda r: r["mean"])[:8]
tiles = []
for r in worst:
    i0, i1 = int(round(r["t0"] * FPS)), int(round((r["t0"] + r["dur"]) * FPS))
    i = i0 + 2 + int(np.argmin(M[i0 + 2:i1 - 1])); tt = i / FPS
    s = frame_at(SRC, tt, CROP); o = frame_at(OUT, tt, "null")
    row = np.hstack([label(s, f"原片 {tt:.2f}s（镜头 c{r['shot']:02d}）"), label(o, f"成片 同一时刻  匹配 {M[i]:.2f}"),
                     label(overlay(o, s), "红线=原片轮廓 叠在成片上")])
    tiles.append(row)
cv2.imwrite(D + "/对比_最差时刻.jpg", np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])

# ---- 图 3：锚帧之后的漂移：挑 4 个 >4 秒且段首高、段尾低的镜头 ----
cand = sorted([r for r in rows if r["dur"] > 4 and not np.isnan(r["tail"])], key=lambda r: r["tail"] - r["first"])[:4]
blocks = []
for r in cand:
    ts = [r["t0"] + 0.05] + [r["t0"] + k for k in (1, 2, 3) if r["t0"] + k < r["t0"] + r["dur"] - 0.1]
    srow = np.hstack([label(frame_at(SRC, tt, CROP, 352, 149), f"原片 {tt:.2f}s") for tt in ts])
    orow = np.hstack([label(frame_at(OUT, tt, "null", 352, 149), f"成片 {tt:.2f}s 匹配 {M[min(int(tt*FPS), n-1)]:.2f}") for tt in ts])
    blocks.append(label(np.vstack([srow, orow]), f"镜头 c{r['shot']:02d}：锚帧起步 {r['first']:.2f} → 段尾 {r['tail']:.2f}", True))
wmax = max(b.shape[1] for b in blocks)
blocks = [np.pad(b, ((0, 8), (0, wmax - b.shape[1]), (0, 0))) for b in blocks]
cv2.imwrite(D + "/对比_锚帧后漂移.jpg", np.vstack(blocks), [cv2.IMWRITE_JPEG_QUALITY, 88])
print("done")
