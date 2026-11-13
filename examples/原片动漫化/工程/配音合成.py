"""把新的第 16、17 句主力配音换进原片音轨：85.1–93.95 秒这段用 demucs 分出来的配乐（no_vocals）+ 新词，其余原样。
输出 声音/原片音轨_新词.wav，并重切 seg_H.wav（80.467–92.8）和 seg_I.wav（92.8–101.367）。

用法：python3 配音合成.py [16句文件] [17句文件]     默认 zhuli_l16_s1.wav zhuli_l17_s1.wav
"""
import os, sys, subprocess
import numpy as np, soundfile as sf, librosa

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(V, "声音")
SR = 48000
L16 = sys.argv[1] if len(sys.argv) > 1 else "zhuli_l16_s1.wav"
L17 = sys.argv[2] if len(sys.argv) > 2 else "zhuli_l17_s1.wav"
T16, T17 = 85.25, 89.75          # 新词的起点（跟原片两句的起点一样）
A0, A1 = 85.10, 93.95            # 换配乐的区间（原片人声 85.25–93.93）


def load(p, sr=SR):
    w, s = librosa.load(p, sr=sr, mono=False)
    if w.ndim == 1:
        w = np.stack([w, w])
    return w.astype(np.float32)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)) + 1e-9)


orig = load(os.path.join(A, "原片音轨.wav"))
bed = load(os.path.join(A, "分离", "htdemucs", "原片音轨", "no_vocals.wav"))
voc = load(os.path.join(A, "分离", "htdemucs", "原片音轨", "vocals.wav"))
n = min(orig.shape[1], bed.shape[1], voc.shape[1])
orig, bed, voc = orig[:, :n], bed[:, :n], voc[:, :n]
i0, i1 = int(A0 * SR), int(A1 * SR)
# 原片这段人声的响度，新词按它对齐
ref_level = rms(voc[:, int(85.25 * SR):int(89.3 * SR)])
out = orig.copy()
out[:, i0:i1] = bed[:, i0:i1]
for f, t in ((L16, T16), (L17, T17)):
    w = load(os.path.join(A, f))
    w = w * (ref_level / rms(w)) * 1.0
    s = int(t * SR)
    e = min(s + w.shape[1], i1)
    out[:, s:e] += w[:, : e - s]
    print(f, "放在", t, "秒，长", round(w.shape[1] / SR, 2), "秒")
# 边界 20 ms 淡接
k = int(0.02 * SR)
ramp = np.linspace(0, 1, k, dtype=np.float32)
out[:, i0 - k:i0] = orig[:, i0 - k:i0] * (1 - ramp) + bed[:, i0 - k:i0] * ramp
out[:, i1:i1 + k] = bed[:, i1:i1 + k] * (1 - ramp) + orig[:, i1:i1 + k] * ramp
out = np.clip(out, -1, 1)
dst = os.path.join(A, "原片音轨_新词.wav")
sf.write(dst, out.T, SR, subtype="PCM_16")
for k_, a, b in (("H", 80.467, 92.8), ("I", 92.8, 101.367)):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", dst, "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "48000", "-ac", "2",
                    os.path.join(A, f"seg_{k_}.wav")], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", dst, "-ss", "83", "-to", "96", "-c:a", "libmp3lame", "-q:a", "2",
                os.path.join(A, "试听_新词换进原片_83到96秒.mp3")], check=True)
print("写出", dst, "并重切 seg_H、seg_I")
