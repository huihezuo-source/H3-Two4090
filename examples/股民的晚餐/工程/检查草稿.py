"""检查一条生成结果：每 0.5 秒抽帧总览、12.0–13.5 秒每 2 帧细看（关灯/换盘）、切点前后帧、音轨分析。
用法：python3 检查草稿.py <mp4> <输出目录>
"""
import os, subprocess, sys, json
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "fps=2,scale=216:-2,tile=10x3:padding=3:color=white", "-frames:v", "1", f"{out}/总览_每半秒.jpg"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "12.0", "-t", "1.5", "-i", src, "-vf", "select='not(mod(n,2))',scale=216:-2,tile=9x2:padding=3:color=white", "-frames:v", "1", f"{out}/细看_12.0-13.5s.jpg"], check=True)
# 切点前后：5.583 / 9.208 秒各取前 2 帧、后 2 帧
tiles = []
for t in (5.583, 9.208):
    for d in (-2, -1, 0, 1, 2):
        tt = t + d / 24; f = f"{out}/cut_{t}_{d:+d}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tt:.4f}", "-i", src, "-frames:v", "1", "-vf", "scale=216:-2", f], check=True); tiles.append(f)
subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", f] for f in tiles], []) + ["-filter_complex", "".join(f"[{i}:v]" for i in range(len(tiles))) + f"hstack={len(tiles)}", f"{out}/切点前后.jpg"], check=True)
for f in tiles: os.remove(f)
# 音轨
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", f"{out}/a.wav"], check=True)
import numpy as np, librosa
y, sr = librosa.load(f"{out}/a.wav", sr=16000)
H, P = librosa.effects.hpss(y); tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
seg = int(sr * 1.0); rms = [20 * np.log10(np.sqrt(np.mean(y[i:i + seg] ** 2)) + 1e-9) for i in range(0, len(y) - seg, seg)]
r = {"时长": round(len(y) / sr, 2), "谐波占比": round(float((H ** 2).sum() / ((H ** 2).sum() + (P ** 2).sum())), 2), "节拍BPM": round(float(np.atleast_1d(tempo)[0])),
     "每秒响度dB": [int(v) for v in rms]}
json.dump(r, open(f"{out}/音轨.json", "w"), ensure_ascii=False); print(json.dumps(r, ensure_ascii=False))
print("图：", out)
