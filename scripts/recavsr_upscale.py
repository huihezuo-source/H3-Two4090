"""ReCaVSR 一步超分放大视频：中科大基于 Wan2.2 TI2V-5B 的流式超分，ComfyUI-ReCaVSR 节点。
每 21 帧再每 8 帧一块、每块 1 步扩散、边算边写盘，片子再长也不多占显存。4090 实测 149 帧 960×480 放大 4 倍 36 秒。

用法：python3 recavsr_upscale.py in.mp4 out_dir [--scale 2.5] [--color-fix none|adain|wavelet] [--seed 42]
                                [--kernels fast|exact] [--encoder auto|h264] [--prefix 名字] [--transformer 文件名]
  --scale    默认 4（模型按 4 倍训练；2 和 1.5 是作者另外验证过的），非整数也能跑，例如 576×800 用 2.5 得 1440×2000。
  --color-fix 默认 none；wavelet 保留原片低频（颜色更稳），adain 逐帧匹配均值方差。
  --encoder  默认 auto（HEVC NVENC，4096 像素一边以内也可 H.264 NVENC）；要在 Mac 上继续后期用 h264 最稳。
机器端要先装好：custom_nodes/ComfyUI-ReCaVSR，models/recavsr/ 下 transformer_int8_convrot.safetensors、prompt.safetensors、
flashdecoder.safetensors（装法见 references/公司4090使用说明.md 的「ReCaVSR 超分」一节）。
顺序：先放大无字幕的原片，再 post_subtitle_loud.py 烧字幕（字幕按分辨率自动缩放）。
"""
import argparse, os, time
import comfy

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--scale", type=float, default=4.0)
ap.add_argument("--color-fix", default="none", choices=["none", "adain", "wavelet"])
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--kernels", default="fast", choices=["fast", "exact"])
ap.add_argument("--encoder", default="auto")
ap.add_argument("--prefix", default=None)
ap.add_argument("--transformer", default="transformer_int8_convrot.safetensors")
ap.add_argument("--timeout", type=int, default=3600)
a = ap.parse_args()

name = f"recavsr_in_{int(time.time())}.mp4"
comfy.upload(a.src, name)
prefix = a.prefix or os.path.splitext(os.path.basename(a.src))[0] + f"_x{a.scale:g}"
prompt = {
    "1": {"class_type": "LoadVideo", "inputs": {"file": name}},
    "3": {"class_type": "ReCaVSRLoader", "inputs": {"transformer": a.transformer}},
    "4": {"class_type": "ReCaVSRUpscale", "inputs": {"model": ["3", 0], "video": ["1", 0], "scale": a.scale,
                                                     "color_fix": a.color_fix, "seed": a.seed, "decoder": "flashdecoder",
                                                     "kernels": a.kernels, "kv_offload": False, "encoder": a.encoder}},
    "6": {"class_type": "SaveVideo", "inputs": {"video": ["4", 0], "filename_prefix": f"recavsr/{prefix}",
                                                "format": "auto", "codec": "auto"}},
}
t = time.time()
got = comfy.run(prompt, a.out, timeout=a.timeout)
print(f"{time.time() - t:.0f} 秒", *got)
