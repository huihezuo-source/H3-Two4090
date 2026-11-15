#!/bin/zsh
# 用法：./成片检查.sh <成片mp4> <输出目录>：分辨率/时长、响度、每秒抽帧总览（看标题位置、画面有无异常）
f="$1"; o="$2"; mkdir -p "$o"
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,codec_type -of default=nw=1 "$f"
ffmpeg -i "$f" -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|LRA:|Peak:" | tail -3
ffmpeg -v error -y -i "$f" -vf "fps=1,scale=216:-2,tile=8x2:padding=3:color=white" -frames:v 1 "$o/成片_每秒.jpg"
ffmpeg -v error -y -ss 10.5 -i "$f" -frames:v 1 "$o/成片_10.5s_原尺寸.png"
echo "图：$o"
