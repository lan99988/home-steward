#!/usr/bin/env python3
"""一键部署推荐模型 —— 自动硬件探测 + Ollama 拉取

用法:
  python scripts/setup_model.py          # 自动推荐并部署
  python scripts/setup_model.py qwen3:7b  # 手动指定模型
  python scripts/setup_model.py --list    # 列出可用模型
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path

AVAILABLE_MODELS = {
    "qwen3:3b":  {"params": "3B",  "ram": 4,  "vram": 0,  "quality": "good",      "disk_gb": 2.0},
    "qwen3:7b":  {"params": "7B",  "ram": 6,  "vram": 4,  "quality": "great",     "disk_gb": 4.5},
    "qwen3.5:9b":{"params": "9B",  "ram": 8,  "vram": 6,  "quality": "smart",     "disk_gb": 6.6},
    "qwen3:14b": {"params": "14B", "ram": 12, "vram": 8,  "quality": "excellent", "disk_gb": 9.0},
    "qwen3:35b": {"params": "35B", "ram": 32, "vram": 24, "quality": "max",       "disk_gb": 20.0},
}


def probe_hardware():
    """探测硬件配置"""
    total_ram = 4
    has_gpu = False
    vram = 0.0

    # RAM
    try:
        if platform.system() == "Linux":
            mem = os.popen("free -g | awk '/^Mem:/{print $2}'").read().strip()
            total_ram = float(mem) if mem else 4
        elif platform.system() == "Windows":
            mem = os.popen("wmic MemoryChip get Capacity").read().strip().split("\n")[1:]
            total_bytes = sum(int(m.strip()) for m in mem if m.strip().isdigit())
            total_ram = total_bytes / (1024**3) if total_bytes else 8
        elif platform.system() == "Darwin":
            mem = os.popen("sysctl -n hw.memsize").read().strip()
            total_ram = int(mem) / (1024**3)
    except:
        pass

    # GPU
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            vram_mb = [int(x) for x in result.stdout.strip().split("\n") if x.strip()]
            if vram_mb:
                has_gpu = True
                vram = max(vram_mb) / 1024
    except:
        pass

    return total_ram, has_gpu, vram


def recommend_model(ram, has_gpu, vram):
    """推荐最适合的模型"""
    if has_gpu:
        if vram >= 24:  return "qwen3:35b"
        if vram >= 8:   return "qwen3:14b"
        if vram >= 6:   return "qwen3.5:9b"
        if vram >= 4:   return "qwen3:7b"
    available = ram - 1.5  # 系统预留
    if available >= 30: return "qwen3:14b"
    if available >= 8:  return "qwen3.5:9b"
    if available >= 6:  return "qwen3:7b"
    if available >= 4:  return "qwen3:3b"
    return "qwen3:3b"


def check_ollama():
    """检测 Ollama 是否安装"""
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Ollama: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("❌ Ollama 未安装，请先安装: https://ollama.com")
    return False


def pull_model(model_name):
    """拉取模型"""
    info = AVAILABLE_MODELS.get(model_name, {})
    disk = info.get("disk_gb", "?")
    print(f"\n📦 正在拉取 {model_name} (~{disk}GB)...")
    print(f"   第一次下载可能需要较长时间，请耐心等待。\n")
    try:
        result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            print(f"✅ {model_name} 部署成功！")
            # 保存配置
            os.makedirs("data", exist_ok=True)
            with open("data/active_model.json", "w") as f:
                json.dump({"model": model_name, "param_count": info.get("params", ""), "quality": info.get("quality", "")}, f)
            print(f"📋 已保存到 data/active_model.json")
            return True
        else:
            print(f"❌ 拉取失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 下载超时（网络较慢或模型较大），请重试")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  🐌 Home Steward — 模型部署工具")
    print("=" * 50)

    if "--list" in sys.argv:
        print("\n可用模型:")
        print(f"  {'名称':<15} {'参数':<6} {'RAM最低':<8} {'VRAM最低':<9} {'大小':<8}")
        print(f"  {'-'*14} {'-'*5} {'-'*7} {'-'*8} {'-'*7}")
        for name, info in AVAILABLE_MODELS.items():
            print(f"  {name:<15} {info['params']:<6} {info['ram']}GB     {info['vram']}GB      {info['disk_gb']}GB")
        sys.exit(0)

    if not check_ollama():
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1].startswith("qwen"):
        model_name = sys.argv[1]
        print(f"\n📋 用户指定模型: {model_name}")
    else:
        ram, has_gpu, vram = probe_hardware()
        print(f"\n📊 硬件探测:")
        print(f"   RAM: {ram:.0f}GB")
        print(f"   GPU: {'✅ ' + str(round(vram, 1)) + 'GB VRAM' if has_gpu else '❌ 无'}")
        model_name = recommend_model(ram, has_gpu, vram)
        info = AVAILABLE_MODELS.get(model_name, {})
        print(f"\n🎯 推荐模型: {model_name} ({info.get('params', '')} · {info.get('quality', '')})")

    pull_model(model_name)
