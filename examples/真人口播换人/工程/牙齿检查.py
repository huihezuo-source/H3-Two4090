#!/usr/bin/env python3
"""每隔 N 帧截一次嘴部特写拼成大图，逐帧看牙齿是否稳定（闪烁、变形、多排牙）。
用法: ~/models/venv/bin/python 牙齿检查.py 视频.mp4 输出.jpg [步长=2]
Haar 人脸框 → 取下 40% 当嘴区，框丢了就沿用上一帧的框。
"""
import sys, cv2, numpy as np
src, out = sys.argv[1], sys.argv[2]; step = int(sys.argv[3]) if len(sys.argv) > 3 else 2
import os
CAND = [cv2.data.haarcascades + "haarcascade_frontalface_default.xml", os.path.expanduser("~/.venvs/mflux/lib/python3.12/site-packages/cv2/data/haarcascade_frontalface_default.xml")]
XML = next((c for c in CAND if os.path.exists(c)), None); assert XML, "找不到 haarcascade_frontalface_default.xml"
cas = cv2.CascadeClassifier(XML); assert not cas.empty()
cap = cv2.VideoCapture(src); tiles = []; last = None; n = 0; lost = 0
TW, TH = 192, 120
while True:
    ok, fr = cap.read()
    if not ok: break
    if n % step == 0:
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = cas.detectMultiScale(g, 1.1, 5, minSize=(80, 80))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3]); last = (x, y, w, h)
        elif last is None:
            n += 1; continue
        else: lost += 1
        x, y, w, h = last
        my0 = y + int(h * 0.58); my1 = y + int(h * 0.98); mx0 = x + int(w * 0.2); mx1 = x + int(w * 0.8)
        crop = fr[max(0, my0):my1, max(0, mx0):mx1]
        if crop.size == 0: n += 1; continue
        t = cv2.resize(crop, (TW, TH), interpolation=cv2.INTER_CUBIC)
        cv2.putText(t, str(n), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)
    n += 1
cols = 12; rows = (len(tiles) + cols - 1) // cols
sheet = np.zeros((rows * TH, cols * TW, 3), np.uint8)
for k, t in enumerate(tiles): sheet[(k // cols) * TH:(k // cols + 1) * TH, (k % cols) * TW:(k % cols + 1) * TW] = t
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(f"帧 {n}，嘴部小图 {len(tiles)} 张（步长 {step}），人脸框丢失 {lost} 次 → {out}")
