#!/usr/bin/env python3
"""盯两台公司机器的队列，哪台空了就立刻提交下一条正式版（形象 1→2→3）。
用法: python3 调度_正式版.py            # 默认 512x896, TAG=正式20步_512s
日志: jobs/调度.log
"""
import json, os, subprocess, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
MACH = {"xw": "http://127.0.0.1:18189", "wj": "http://127.0.0.1:18188"}
JOBS = [int(x) for x in os.environ.get("JOBS", "1,2,3").split(",")]
ENV = dict(os.environ, GEN_SIZE=os.environ.get("GEN_SIZE", "512x896"), TAG=os.environ.get("TAG", "正式20步_512s"))
LOG = open(os.path.join(HERE, "jobs", "调度.log"), "a", encoding="utf-8")
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n"); LOG.flush()
def idle(url):
    try:
        q = json.load(urllib.request.urlopen(url + "/queue", timeout=30))
        return len(q["queue_running"]) == 0 and len(q["queue_pending"]) == 0
    except Exception as e:
        log("查队列失败", url, e); return False
running = {}  # machine -> (job_i, Popen)
pending = list(JOBS)
log("开始调度，待做:", pending, "尺寸", ENV["GEN_SIZE"], "标签", ENV["TAG"])
while pending or running:
    for m, (i, p) in list(running.items()):
        if p.poll() is not None:
            log(f"形象{i} 在 {m.upper()} 结束，返回码 {p.returncode}")
            del running[m]
    for m in MACH:
        if m in running or not pending: continue
        if idle(MACH[m]):
            i = pending.pop(0)
            out = open(os.path.join(HERE, "jobs", f"形象{i}_{m}.log"), "a", encoding="utf-8")
            p = subprocess.Popen([sys.executable, os.path.join(HERE, "做换人_公司.py"), str(i), m], env=ENV, stdout=out, stderr=subprocess.STDOUT, cwd=HERE)
            running[m] = (i, p); log(f"{m.upper()} 空闲，提交形象{i}")
            time.sleep(20)
    time.sleep(60)
log("全部结束")
