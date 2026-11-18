"""把一处"一帧跳变"用光流补顺：用前后两帧（a-1、b+1）做双向光流插值，替换掉 a..b 这几帧，音频不动。
用法：~/models/venv/bin/python 补帧.py in.mp4 out.mp4 <a> <b>   （帧号从 0 起，含 a 和 b）
"""
import sys, os, subprocess, tempfile, cv2, numpy as np
src, dst, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
cap = cv2.VideoCapture(src); fps = cap.get(5); W, H = int(cap.get(3)), int(cap.get(4))
frames = []
while True:
    ok, f = cap.read()
    if not ok: break
    frames.append(f)
assert 1 <= a <= b < len(frames) - 1, (a, b, len(frames))
k = b - a + 1
p0, p1 = frames[a - 1], frames[b + 1]
g0, g1 = cv2.cvtColor(p0, cv2.COLOR_BGR2GRAY), cv2.cvtColor(p1, cv2.COLOR_BGR2GRAY)
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
f01, f10 = dis.calc(g0, g1, None), dis.calc(g1, g0, None)
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
for j in range(k):
    t = (j + 1) / (k + 1)
    w0 = cv2.remap(p0, xs - t * f01[..., 0], ys - t * f01[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    w1 = cv2.remap(p1, xs - (1 - t) * f10[..., 0], ys - (1 - t) * f10[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    frames[a + j] = np.clip((1 - t) * w0.astype(np.float32) + t * w1.astype(np.float32), 0, 255).astype(np.uint8)
tmp = tempfile.mkdtemp(); raw = f"{tmp}/v.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", raw], stdin=subprocess.PIPE)
for f in frames: ff.stdin.write(f.tobytes())
ff.stdin.close(); ff.wait()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", src, "-map", "0:v", "-map", "1:a?", "-c", "copy", dst], check=True)
print(f"已用光流补了第 {a}–{b} 帧（{k} 帧）→ {dst}")
