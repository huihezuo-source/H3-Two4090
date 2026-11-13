#!/bin/bash
# 等 69 张首帧齐 → 参考视频模式两台机器重生成 15 段 → 拼接 → ReCaVSR → 成片。用法：FARM_OUT=farm_ref [GEN_TURBO=1 GEN_STEPS=4] ./全流程.sh
set -u
cd "$(dirname "$0")"
V="$(cd .. && pwd)"; B=${H3_SCRIPTS:-$(cd ../../.. && pwd)/scripts}/board.py
export FARM_OUT=${FARM_OUT:-farm_ref} USE_REF=1 COMFY_CLIENT_ID=mac-claude
log(){ echo "$(date +%H:%M:%S) $*" | tee -a 全流程_log.txt; }
for i in $(seq 1 120); do n=$(ls "$V/首帧/原始"/c*.png 2>/dev/null | wc -l | tr -d ' '); [ "$n" -ge 69 ] && break; sleep 30; done
log "首帧 $n/69，开始分段生成（FARM_OUT=$FARM_OUT GEN_TURBO=${GEN_TURBO:-} GEN_STEPS=${GEN_STEPS:-20}）"
python3 $B step "重做问题镜头" running "15 段参考视频模式重生成中，输出 生成/$FARM_OUT" >/dev/null
python3 分段v2.py run N A H F B E J M T K L I C D G 2>&1 | tail -5 | tee -a 全流程_log.txt
ok=$(ls "$V/生成/$FARM_OUT"/seg_*/*.mp4 2>/dev/null | wc -l | tr -d ' ')
log "分段完成，共 $ok 个输出文件"
python3 成片v2.py join 2>&1 | tail -2 | tee -a 全流程_log.txt
python3 $B step "重做问题镜头" done "拼接草稿完成" >/dev/null
python3 $B file "$V/成片/拼接_草稿.mp4" "新版拼接草稿（参考视频模式）" >/dev/null
COMFY_URL=http://127.0.0.1:18189 python3 成片v2.py upscale 2>&1 | tail -2 | tee -a 全流程_log.txt
python3 成片v2.py final 2>&1 | tail -2 | tee -a 全流程_log.txt
python3 $B file "$V/成片/散户动漫版v2_成片.mp4" "新版成片（待自审）" >/dev/null
log "全流程结束"
