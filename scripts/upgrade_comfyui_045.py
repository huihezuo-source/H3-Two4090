r"""Upgrade a zip-installed ComfyUI (0.44) to 0.45.2 in place: models, input, output, custom_nodes and .venv are untouched.
Old core files are backed up to <H3>\backup044. Log: <ROOT>\input\upgrade_log.txt.
Edit ROOT (ComfyUI folder) and H3 (scratch folder) below for the machine, then run it with the ComfyUI venv python:
  C:\ComfyUI\.venv\Scripts\python.exe upgrade_comfyui_045.py
No git needed. pip goes through the Tsinghua mirror (the Aliyun mirror stalls on big wheels)."""
import os, subprocess, time, zipfile, shutil
ROOT = r'C:\ComfyUI'; H3 = r'C:\h3'; VER = '0.45.2'   # WJ: D:\ComfyUI, D:\h3
LOG = os.path.join(ROOT, 'input', 'upgrade_log.txt')
PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
PIPI = 'https://pypi.tuna.tsinghua.edu.cn/simple'
def L(m):
    s = time.strftime('%m-%d %H:%M:%S ') + str(m)
    print(s, flush=True)
    open(LOG, 'a', encoding='utf-8').write(s + '\n')
os.makedirs(H3, exist_ok=True)
zipp = os.path.join(H3, f'comfy{VER}.zip')
url = f'https://github.com/comfyanonymous/ComfyUI/archive/refs/tags/v{VER}.zip'
L(f'download ComfyUI {VER} zip')
subprocess.run(['curl.exe', '-L', '--retry', '30', '--retry-all-errors', '-C', '-', '-o', zipp, url])
L(f'zip size {os.path.getsize(zipp)}')
unz = os.path.join(H3, f'unz{VER}')
shutil.rmtree(unz, ignore_errors=True)
with zipfile.ZipFile(zipp) as z:
    z.extractall(unz)
src = os.path.join(unz, f'ComfyUI-{VER}')
if not os.path.exists(os.path.join(src, 'main.py')):
    L('unzip failed, abort'); raise SystemExit(1)
L('stop running ComfyUI (loop bat + python)')
ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*start_h3.bat*' -or ($_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*8188*') } "
      "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }")
out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout
L('killed: ' + ' '.join(out.split()))
time.sleep(3)
L('backup old core files to ' + os.path.join(H3, 'backup044'))
subprocess.run(['robocopy', ROOT, os.path.join(H3, 'backup044'), '/E', '/XD', 'models', 'input', 'output', '.venv', 'user', 'temp', 'custom_nodes', '/NFL', '/NDL', '/NJH', '/NJS'], capture_output=True)
L('copy new files over')
shutil.copytree(src, ROOT, dirs_exist_ok=True)
L('pip install requirements')
r = subprocess.run([PY, '-m', 'pip', 'install', '-r', os.path.join(ROOT, 'requirements.txt'), '-i', PIPI, '--timeout', '60', '--retries', '10'], capture_output=True, text=True)
for line in (r.stdout + r.stderr).strip().splitlines()[-12:]:
    L('  ' + line)
try:
    L('version file: ' + [l for l in open(os.path.join(ROOT, 'comfyui_version.py')) if '__version__' in l][0].strip())
except Exception as e:
    L(f'version read failed {e}')
L('start ComfyUI')
subprocess.Popen(['cmd', '/c', 'start', '', os.path.join(ROOT, 'start_h3.bat')])
L('done')
