r"""Install ComfyUI-ReCaVSR (one-step video super-resolution) on a Windows ComfyUI: node pack, pip deps, model files, restart.
Usage (in PowerShell, with the ComfyUI venv python):  C:\ComfyUI\.venv\Scripts\python.exe install_recavsr.py [C:\ComfyUI]
WJ: D:\ComfyUI\.venv\Scripts\python.exe install_recavsr.py D:\ComfyUI
Needs ComfyUI 0.44+, Python 3.11+ (triton-windows), about 7 GB free. Log: <ROOT>\input\recavsr_install_log.txt.
Safe to re-run: finished parts are skipped. Restarts ComfyUI through <ROOT>\start_h3.bat at the end."""
import os, sys, subprocess, time, zipfile, shutil, hashlib, threading, urllib.request, json
ROOT = sys.argv[1] if len(sys.argv) > 1 else r'C:\ComfyUI'
H3 = ROOT[:3] + 'h3'   # zip and temp files go to <drive>:\h3
LOG = os.path.join(ROOT, 'input', 'recavsr_install_log.txt')
PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
PIPI = 'https://pypi.tuna.tsinghua.edu.cn/simple'
MODELS = os.path.join(ROOT, 'models', 'recavsr')
N = 8
FILES = [
    ('prompt.safetensors', 'https://huggingface.co/kopper/ReCaVSR/resolve/main/prompt.safetensors',
     4194392, '325ee3b5ec7d8bd43bc7ab186be5272dec0877c04e7c01a46fd0893260c9c6a5'),
    ('flashdecoder.safetensors', 'https://huggingface.co/kopper/ReCaVSR/resolve/main/flashdecoder.safetensors',
     228723776, 'f4feb3e7b0b65f98e15bb709a1ba28dfaada7c06bf7fc0ce4cdbcb58803034e8'),
    ('transformer_int8_convrot.safetensors',
     'https://huggingface.co/PedroMarinhoDev/ReCaVSR-ComfyUI/resolve/main/recavsr/transformer_int8_convrot.safetensors',
     6266935048, '70f77ac653a29dcab8cb8d5f5300acf27d9a3a45e9baf273fa4526fa43f66c9d'),
]


def L(m):
    s = time.strftime('%m-%d %H:%M:%S ') + str(m)
    print(s, flush=True)
    open(LOG, 'a', encoding='utf-8').write(s + '\n')


def sh(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return (r.stdout or '') + (r.stderr or '')


os.makedirs(H3, exist_ok=True); os.makedirs(MODELS, exist_ok=True)
L('=== ReCaVSR install start, python ' + sys.version.split()[0])
free = shutil.disk_usage(ROOT[:3]).free / 2**30
L('free disk on %s: %.1f GB (need about 7 GB)' % (ROOT[:3], free))

# 1. node pack
dst = os.path.join(ROOT, 'custom_nodes', 'ComfyUI-ReCaVSR')
if os.path.exists(os.path.join(dst, 'nodes.py')):
    L('node pack already present, skip')
else:
    zipp = os.path.join(H3, 'ComfyUI-ReCaVSR.zip')
    L('download node pack zip')
    sh(['curl.exe', '-L', '--retry', '30', '--retry-all-errors', '-o', zipp,
        'https://github.com/PedroMarinhoDev/ComfyUI-ReCaVSR/archive/refs/heads/main.zip'])
    L('zip size %d' % os.path.getsize(zipp))
    unz = os.path.join(H3, 'unz_recavsr'); shutil.rmtree(unz, ignore_errors=True)
    with zipfile.ZipFile(zipp) as z:
        z.extractall(unz)
    src = os.path.join(unz, 'ComfyUI-ReCaVSR-main')
    if not os.path.exists(os.path.join(src, 'nodes.py')):
        L('unzip failed, abort'); raise SystemExit(1)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    L('node pack copied to ' + dst)

# 2. pip deps: comfy-kitchen 0.2.41 (fast kernels), triton-windows (attention kernels), opencv (reference resize)
L('pip install deps (tsinghua mirror)')
out = sh([PY, '-m', 'pip', 'install', '-i', PIPI, '--timeout', '60', '--retries', '10', '-U',
          'comfy-kitchen==0.2.41', 'opencv-python-headless', 'triton-windows<3.8'])
for line in out.strip().splitlines()[-8:]:
    L('  ' + line)
L('check: ' + sh([PY, '-c', 'import comfy_kitchen,cv2;print("comfy_kitchen",comfy_kitchen.__version__,"cv2",cv2.__version__)']).strip())
L('check: ' + sh([PY, '-c', 'import triton;print("triton",triton.__version__)']).strip()[-200:])


# 3. model files: 8-way segmented download with resume + sha256
def segment(url, part, start, end):
    while True:
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if start + have > end:
            return
        try:
            req = urllib.request.Request(url, headers={'Range': 'bytes=%d-%d' % (start + have, end), 'User-Agent': 'h3dl'})
            with urllib.request.urlopen(req, timeout=60) as r, open(part, 'ab') as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
        except Exception as e:
            L('retry %s: %s' % (os.path.basename(part), str(e)[:80]))
            time.sleep(10)


def fetch(name, url, size, sha):
    d = os.path.join(MODELS, name)
    if os.path.exists(d) and os.path.getsize(d) == size:
        L('already have ' + name); return
    step = size // N + 1
    parts, threads = [], []
    for i in range(N):
        s, e = i * step, min(size - 1, (i + 1) * step - 1)
        if s > e:
            break
        p = '%s.part%d' % (d, i); parts.append(p)
        t = threading.Thread(target=segment, args=(url, p, s, e), daemon=True); t.start(); threads.append(t)
    for t in threads:
        t.join()
    L('merge + sha256 ' + name)
    h = hashlib.sha256()
    with open(d + '.tmp', 'wb') as o:
        for p in parts:
            with open(p, 'rb') as f:
                while True:
                    b = f.read(1 << 24)
                    if not b:
                        break
                    o.write(b); h.update(b)
    if h.hexdigest() != sha:
        L('sha mismatch, delete and redo ' + name)
        os.remove(d + '.tmp')
        for p in parts:
            os.remove(p)
        return fetch(name, url, size, sha)
    os.replace(d + '.tmp', d)
    for p in parts:
        os.remove(p)
    L('done, sha ok ' + name)


def on_disk():
    n = 0
    for name, _, _, _ in FILES:
        d = os.path.join(MODELS, name)
        if os.path.exists(d):
            n += os.path.getsize(d); continue
        for i in range(N):
            p = '%s.part%d' % (d, i)
            if os.path.exists(p):
                n += os.path.getsize(p)
    return n


def monitor():
    total = sum(f[2] for f in FILES)
    last, lt = on_disk(), time.time()
    while True:
        time.sleep(60)
        now, t = on_disk(), time.time()
        sp = (now - last) / (t - lt); last, lt = now, t
        eta = (total - now) / sp / 60 if sp > 0 else 0
        L('download %.2f/%.2f GB, %.1f MB/s, about %.0f min left' % (now / 2**30, total / 2**30, sp / 2**20, eta))


L('download model files (6.5 GB total)')
threading.Thread(target=monitor, daemon=True).start()
for f in FILES:
    fetch(*f)

# 4. restart ComfyUI so it loads the new nodes
L('stop running ComfyUI (loop bat + python)')
ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*start_h3.bat*' -or ($_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*8188*') } "
      "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }")
L('killed: ' + ' '.join(sh(['powershell', '-NoProfile', '-Command', ps]).split()))
time.sleep(4)
L('start ComfyUI')
subprocess.Popen(['cmd', '/c', 'start', '', os.path.join(ROOT, 'start_h3.bat')])

# 5. wait until the node is registered
for i in range(60):
    time.sleep(10)
    try:
        with urllib.request.urlopen('http://127.0.0.1:8188/object_info/ReCaVSRUpscale', timeout=10) as r:
            d = json.load(r)
        if 'ReCaVSRUpscale' in d:
            L('ReCaVSRUpscale node is online. inputs: ' + ','.join(d['ReCaVSRUpscale']['input'].get('required', {}).keys()))
            break
        L('ComfyUI up but node missing (check custom_nodes import errors in the ComfyUI window)')
        break
    except Exception as e:
        if i % 6 == 5:
            L('waiting for ComfyUI... ' + str(e)[:60])
L('=== install done')
