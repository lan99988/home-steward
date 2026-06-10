"""模型部署器——硬件探测 → 模型推荐 → Ollama 部署"""

import json
import logging
import os
import platform
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareSpec:
    total_ram_gb: float
    cpu_cores: int
    has_nvidia_gpu: bool
    vram_gb: float
    is_raspberry_pi: bool


@dataclass
class ModelRecommendation:
    name: str
    param_count: str
    min_ram_gb: float
    min_vram_gb: float
    quality: str  # basic, base, good, great, excellent, max
    disk_gb: float


class ModelProvisioner:
    """硬件探测 → 推荐最适合的 Qwen3 模型 → 自动部署"""

    RECOMMENDATIONS = [
        ModelRecommendation("qwen3:0.5b", "0.5B", 0, 0, "basic", 0.4),
        ModelRecommendation("qwen3:1.5b", "1.5B", 2, 0, "base", 1.0),
        ModelRecommendation("qwen3:3b", "3B", 4, 0, "good", 2.0),
        ModelRecommendation("qwen3:7b", "7B", 6, 4, "great", 4.5),
        ModelRecommendation("qwen3:14b", "14B", 12, 8, "excellent", 9.0),
        ModelRecommendation("qwen3:35b", "35B", 32, 24, "max", 20.0),
    ]

    def probe(self) -> HardwareSpec:
        """探测用户硬件配置"""
        total_ram = self._get_ram_gb()
        cpu_cores = os.cpu_count() or 4
        has_gpu, vram = self._get_gpu_info()
        is_pi = self._is_raspberry_pi()
        spec = HardwareSpec(total_ram, cpu_cores, has_gpu, vram, is_pi)
        logger.info(f"硬件探测: {spec.total_ram_gb}GB RAM, "
                    f"{spec.cpu_cores}核 CPU, "
                    f"GPU: {'Yes' if spec.has_nvidia_gpu else 'No'}"
                    f"{f' ({spec.vram_gb}GB VRAM)' if spec.has_nvidia_gpu else ''}")
        return spec

    def recommend(self, spec: HardwareSpec) -> ModelRecommendation:
        """根据硬件推荐最适合的模型"""
        if spec.is_raspberry_pi:
            if spec.total_ram_gb >= 8:
                return self._find("qwen3:3b")
            return self._find("qwen3:1.5b")

        if spec.has_nvidia_gpu:
            vram = spec.vram_gb
            if vram >= 24:
                return self._find("qwen3:35b")
            elif vram >= 8:
                return self._find("qwen3:14b")
            elif vram >= 4:
                return self._find("qwen3:7b")

        available_ram = spec.total_ram_gb - 2  # 系统预留
        if available_ram >= 30:
            return self._find("qwen3:14b")
        elif available_ram >= 6:
            return self._find("qwen3:7b")
        elif available_ram >= 4:
            return self._find("qwen3:3b")
        elif available_ram >= 2:
            return self._find("qwen3:1.5b")
        else:
            return self._find("qwen3:0.5b")

    def deploy(self, model: ModelRecommendation) -> bool:
        """通过 Ollama 拉取并部署模型"""
        try:
            logger.info(f"📦 下载模型 {model.name} ({model.param_count}, ~{model.disk_gb}GB)...")
            result = subprocess.run(
                ["ollama", "pull", model.name],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                logger.error(f"模型部署失败: {result.stderr}")
                return False
            logger.info(f"✅ 模型 {model.name} 部署成功")
            return True
        except subprocess.TimeoutExpired:
            logger.error("模型下载超时（可能需要更快的网络）")
            return False
        except FileNotFoundError:
            logger.error("Ollama 未安装，请访问 https://ollama.com 安装")
            return False
        except Exception as e:
            logger.error(f"模型部署异常: {e}")
            return False

    def save_active_model(self, model: ModelRecommendation):
        """保存当前激活的模型配置"""
        os.makedirs("data", exist_ok=True)
        with open("data/active_model.json", "w") as f:
            json.dump({
                "model": model.name,
                "param_count": model.param_count,
                "quality": model.quality,
            }, f)
        logger.info(f"当前模型: {model.name} ({model.quality})")

    def _find(self, name: str) -> ModelRecommendation:
        return next(r for r in self.RECOMMENDATIONS if r.name == name)

    def _get_ram_gb(self) -> float:
        """获取系统总内存（GB）"""
        try:
            if platform.system() == "Linux":
                mem = os.popen("free -g | awk '/^Mem:/{print $2}'").read().strip()
                return float(mem) if mem else 4
            elif platform.system() == "Windows":
                mem = os.popen(
                    "wmic MemoryChip get Capacity"
                ).read().strip().split("\n")[1:]
                total_bytes = sum(int(m.strip()) for m in mem if m.strip().isdigit())
                return total_bytes / (1024 ** 3) if total_bytes else 8
            elif platform.system() == "Darwin":
                mem = os.popen("sysctl -n hw.memsize").read().strip()
                return int(mem) / (1024 ** 3)
        except Exception:
            pass
        return 4  # 安全默认值

    def _get_gpu_info(self) -> tuple:
        """检测 NVIDIA GPU 显存"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                vram_mb = [int(x) for x in result.stdout.strip().split("\n") if x.strip()]
                if vram_mb:
                    return True, max(vram_mb) / 1024
        except Exception:
            pass
        return False, 0.0

    def _is_raspberry_pi(self) -> bool:
        try:
            with open("/proc/device-tree/model") as f:
                return "Raspberry Pi" in f.read()
        except Exception:
            return False
