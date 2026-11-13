#!/bin/bash
# 成片前整片检查：1) 嘴动但没人说话（自动）2) 2 fps 总览 3) 远景并排。用法：成片检查.sh <拼接_草稿.mp4>
cd "$(dirname "$0")"; V="$(cd .. && pwd)"; D="$1"; S=/tmp/final_chk
rm -rf "$S"; mkdir -p "$S"
~/models/venv/bin/python 嘴动对人声.py "$D" 0 2>&1 | grep -v -i warn | tee "$S/lip_report.txt"
ffmpeg -v error -y -i "$D" -vf "fps=2,scale=400:170,drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='%{pts\:hms}':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6" "$S/f_%04d.jpg"
cd "$S" && python3 - <<'PY'
import glob, os, subprocess
fs=sorted(glob.glob("f_*.jpg")); per=80
for i in range(0,len(fs),per):
    chunk=fs[i:i+per]; open(f"l{i}.txt","w").write("\n".join(f"file '{os.path.abspath(f)}'" for f in chunk))
    subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",f"l{i}.txt","-vf","tile=8x10:padding=2","-frames:v","1",f"sheet{i//per+1}.jpg"],check=True)
print("sheets",(len(fs)+per-1)//per)
PY
