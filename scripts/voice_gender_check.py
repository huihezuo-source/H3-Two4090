"""配音选角和成片的嗓音核对：每条参考音、每句台词量基频（pyin），和角色表里的性别、年龄对一遍，对不上就标出来。
起因：漫剧第 1 集芳姐（女）的参考音基频约 120 Hz、阿强（男）的约 270–410 Hz，我没量就用了，成片里芳姐开口是男声。

用法：
  /usr/bin/python3 voice_gender_check.py cast.json 参考音1.flac 参考音2.wav ...    # 选角：文件名里含角色名
  /usr/bin/python3 voice_gender_check.py cast.json --lines lines.json 成片.mp4     # 成片：按台词表的时间逐句量
cast.json：{"芳姐": "female", "阿强": "male", "老周": "male_old", "苏真真": "female_young"}
lines.json：[[开始秒, 结束秒, "角色", "台词"], ...]
判断范围（说话时的基频中位数，经验值）：男 75–165 Hz，女 165–330 Hz；亢奋、喊叫会偏高，男声可能到 250 Hz。
三档：符合 / 边界（要人耳听）/ 不符合。pyin 遇到基音弱的嗓子可能差一个八度，两种方法都超范围才算实锤。只是筛查，最后要人听。"""
import json, subprocess, sys
import numpy as np
import librosa

# (符合下限, 符合上限, 边界下限, 边界上限)
RANGE = {"male": (75, 165, 60, 250), "male_old": (75, 160, 60, 230), "female": (165, 330, 140, 420), "female_young": (180, 420, 150, 500)}
SR = 16000


def load(path, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss is not None else []) + ["-i", path] + (["-t", str(t)] if t else []) + ["-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.int16).astype(float) / 32768


def f0_median(y):
    f0, voiced, _ = librosa.pyin(y, fmin=60, fmax=500, sr=SR, frame_length=1024)
    f = f0[voiced]
    return (float(np.nanmedian(f)), float(np.nanpercentile(f, 25)), float(np.nanpercentile(f, 75))) if np.sum(voiced) > 5 else None


def verdict(kind, med):
    lo, hi, blo, bhi = RANGE[kind]
    if lo <= med <= hi: return "符合"
    if blo <= med <= bhi: return f"边界，要人耳听（{kind} 一般在 {lo}–{hi} Hz）"
    return f"✗ 不符合：{kind} 一般在 {lo}–{hi} Hz"


cast = json.load(open(sys.argv[1]))
args = sys.argv[2:]
if args and args[0] == "--lines":
    lines, video = json.load(open(args[1])), args[2]
    y = load(video)
    for a, b, who, text in lines:
        r = f0_median(y[int(a * SR):int(b * SR)])
        kind = cast.get(who)
        if not r or not kind: print(f"{a:6.2f}  {who}  （没量到或角色表里没有）  {text}"); continue
        print(f"{a:6.2f}  {who:4s} 中位 {r[0]:4.0f} Hz（{r[1]:.0f}–{r[2]:.0f}）  {verdict(kind, r[0])}  {text}")
else:
    for p in args:
        who = next((k for k in cast if k in p.split("/")[-1]), None)
        r = f0_median(load(p))
        if not r: print(f"{p.split('/')[-1]}: {who} 有声帧太少，量不出"); continue
        print(f"{p.split('/')[-1]}: {who} 中位 {r[0]:.0f} Hz（{r[1]:.0f}–{r[2]:.0f}）  {verdict(cast[who], r[0]) if who else '文件名里没有角色名'}")
