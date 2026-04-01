#!/usr/bin/env python3
"""
环境检测与引导模块 - 检测KataGo安装状态，提供安装指引
合并了 hardware.py 的硬件检测功能
"""

import os
import sys
import subprocess
import json
import re
import platform
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class HardwareInfo:
    """硬件信息"""
    cpu_cores: int
    cpu_arch: str
    avx2: bool
    opencl: bool
    cuda: bool
    vram_gb: float
    gpu_name: str
    memory_total_gb: float
    memory_available_gb: float
    os: str


class HardwareProfiler:
    """硬件分析器"""
    
    # 模型配置表：大小(GB), 最小显存(GB), 最小内存(GB), 质量评分(1-5)
    MODELS = {
        "b28c512nbt": {"size": 1.0, "min_vram": 6, "min_ram": 16, "quality": 5, "speed_gpu": 5, "speed_cpu": 60},
        "b18c384nbt": {"size": 0.3, "min_vram": 3, "min_ram": 8, "quality": 4, "speed_gpu": 2, "speed_cpu": 15},
        "b15c192nbt": {"size": 0.15, "min_vram": 2, "min_ram": 6, "quality": 3, "speed_gpu": 1, "speed_cpu": 8},
        "b10c128nbt": {"size": 0.07, "min_ram": 4, "quality": 3, "speed_gpu": 0.5, "speed_cpu": 5},
        "b6c64": {"size": 0.05, "min_ram": 2, "quality": 2, "speed_gpu": 0.3, "speed_cpu": 2},
    }
    
    def detect(self) -> HardwareInfo:
        """检测硬件信息"""
        return HardwareInfo(
            cpu_cores=self._detect_cpu_cores(),
            cpu_arch=platform.machine(),
            avx2=self._detect_avx2(),
            opencl=self._detect_opencl(),
            cuda=self._detect_cuda(),
            vram_gb=self._detect_vram(),
            gpu_name=self._detect_gpu_name(),
            memory_total_gb=self._detect_memory_total(),
            memory_available_gb=self._detect_memory_available(),
            os=platform.system().lower()
        )
    
    def _detect_cpu_cores(self) -> int:
        """检测CPU核心数"""
        return os.cpu_count() or 4
    
    def _detect_avx2(self) -> bool:
        """检测是否支持AVX2指令集"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read()
                return 'avx2' in content.lower()
        except:
            return False
    
    def _detect_opencl(self) -> bool:
        """检测OpenCL支持"""
        try:
            result = subprocess.run(['clinfo'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _detect_cuda(self) -> bool:
        """检测CUDA支持"""
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _detect_vram(self) -> float:
        """检测显存大小(GB)"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            vram_mb = int(result.stdout.strip().split('\n')[0])
            return vram_mb / 1024
        except:
            return 0
    
    def _detect_gpu_name(self) -> str:
        """检测GPU型号"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip().split('\n')[0]
        except:
            return "None"
    
    def _detect_memory_total(self) -> float:
        """检测总内存(GB)"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        return kb / (1024 * 1024)
        except:
            pass
        return 8.0  # 默认值
    
    def _detect_memory_available(self) -> float:
        """检测可用内存(GB)"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        kb = int(line.split()[1])
                        return kb / (1024 * 1024)
        except:
            pass
        return self._detect_memory_total() * 0.5
    
    def recommend_model(self, hw: HardwareInfo) -> Dict:
        """根据硬件推荐模型"""
        candidates = []
        
        for model_name, specs in self.MODELS.items():
            if hw.memory_total_gb < specs.get("min_ram", 2):
                continue
            
            if hw.cuda and hw.vram_gb > 0:
                if specs.get("min_vram", 0) > hw.vram_gb:
                    continue
                speed = specs["speed_gpu"]
            else:
                speed = specs["speed_cpu"]
            
            candidates.append({
                "name": model_name,
                "size": specs["size"],
                "quality": specs["quality"],
                "speed": speed,
                "score": specs["quality"] * 10 - speed
            })
        
        if not candidates:
            return {"name": "b6c64", "size": 0.05, "quality": 2, "speed": 2}
        
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[0]
    
    def estimate_time(self, moves: int, model: str, hw: HardwareInfo) -> Dict:
        """预估分析时间"""
        specs = self.MODELS.get(model, self.MODELS["b18c384nbt"])
        
        if hw.cuda and hw.vram_gb > 0:
            sec_per_move = specs["speed_gpu"]
            parallel_factor = 0.8
        else:
            sec_per_move = specs["speed_cpu"]
            if hw.cpu_cores >= 8:
                parallel_factor = 1.0
            elif hw.cpu_cores >= 4:
                parallel_factor = 1.2
            else:
                parallel_factor = 1.5
        
        total_seconds = moves * sec_per_move * parallel_factor
        
        return {
            "seconds_per_move": sec_per_move,
            "total_seconds": total_seconds,
            "total_minutes": total_seconds / 60,
            "formatted": self._format_time(total_seconds)
        }
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            return f"{int(seconds/60)}分钟"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}小时{mins}分钟"
    
    def generate_config(self, hw: HardwareInfo, model: str) -> str:
        """生成优化的KataGo配置"""
        lines = [
            "# KataGo 分析配置文件",
            f"# 自动生成 - {hw.cpu_cores}核 CPU, {hw.memory_total_gb:.1f}GB 内存",
            "",
        ]
        
        if hw.cuda and hw.vram_gb > 0:
            lines.extend([
                f"cudaGpuToUse = 0",
                f"nnCacheSizePowerOfTwo = {min(22, int(hw.vram_gb * 2) + 18)}",
                f"numNNServerThreadsPerModel = 1",
            ])
        else:
            lines.extend([
                f"cudaGpuToUse = -1",
                f"nnCacheSizePowerOfTwo = {min(20, int(hw.memory_total_gb) + 16)}",
                f"numNNServerThreadsPerModel = {min(2, max(1, hw.cpu_cores // 4))}",
            ])
        
        lines.extend([
            f"numSearchThreads = {hw.cpu_cores}",
            "",
            "# 分析参数",
            "maxVisits = 500",
            "maxTime = 10.0",
            "",
            "# 输出选项",
            "analysisPVLen = 15",
            "rootFpuReductionMax = 0.2",
            "",
            "# 日志目录（临时目录，不污染工作区）",
            "logDir = /tmp",
        ])
        
        return "\n".join(lines)
    
    def print_summary(self, hw: HardwareInfo):
        """打印硬件摘要"""
        print("硬件检测摘要")
        print("=" * 40)
        print(f"操作系统: {hw.os}")
        print(f"CPU: {hw.cpu_cores}核 (架构: {hw.cpu_arch}, AVX2: {'✓' if hw.avx2 else '✗'})")
        
        if hw.cuda:
            print(f"GPU: {hw.gpu_name} ({hw.vram_gb:.1f}GB VRAM)")
        else:
            print(f"GPU: 未检测到")
        
        print(f"内存: {hw.memory_total_gb:.1f}GB (可用: {hw.memory_available_gb:.1f}GB)")
        print()
        
        rec = self.recommend_model(hw)
        print(f"推荐模型: {rec['name']} ({rec['size']*1000:.0f}MB)")
        print(f"  - 质量: {'★' * rec['quality']}{'☆' * (5-rec['quality'])}")
        print(f"  - 预估速度: ~{rec['speed']}秒/手")
        
        estimate = self.estimate_time(200, rec['name'], hw)
        print(f"  - 200手棋谱预估用时: {estimate['formatted']}")


class KataGoSetup:
    """KataGo环境设置（合并了硬件检测）"""
    
    MODEL_URLS = {
        "lionffen_b6c64": {
            "url": "https://media.katagotraining.org/uploaded/networks/models_extra/lionffen_b6c64_3x3_v10.txt.gz",
            "size_mb": 2.1,
            "description": "超轻量模型，低端CPU首选 (19x19专用)"
        },
        "g170_b6c96": {
            "url": "https://katagoarchive.org/g170/neuralnets/g170-b6c96-s175395328-d26788732.bin.gz",
            "size_mb": 3.8,
            "description": "KataGo历史版本g170，6 block轻量模型"
        },
        "g170_b10c128": {
            "url": "https://katagoarchive.org/g170/neuralnets/g170-b10c128-s197428736-d67404019.bin.gz",
            "size_mb": 11.0,
            "description": "KataGo历史版本g170，10 block平衡模型"
        },
    }
    
    MODEL_SIZE_LIMITS = {
        "low": 50,
        "medium": 300,
        "high": 1000,
    }
    
    def __init__(self):
        self.profiler = HardwareProfiler()
        self.hw = self.profiler.detect()
    
    def get_latest_katago_url(self) -> Optional[str]:
        """从GitHub API获取最新版本下载链接"""
        try:
            import urllib.request
            import ssl
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            api_url = "https://api.github.com/repos/lightvector/KataGo/releases/latest"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            arch = self.hw.cpu_arch
            os_name = self.hw.os
            
            if os_name == "linux":
                if arch == "x86_64":
                    pattern = "eigenavx2-linux-x64"
                elif arch == "aarch64":
                    pattern = "linux-arm64"
                else:
                    pattern = "linux"
            elif os_name == "darwin":
                if arch == "arm64":
                    pattern = "osx-arm64"
                else:
                    pattern = "osx-x64"
            else:
                pattern = ""
            
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                url = asset.get("browser_download_url", "")
                if pattern in name and name.endswith(".zip"):
                    if "eigenavx2" in name or "+avx2" in name:
                        return url
            
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                url = asset.get("browser_download_url", "")
                if pattern in name and name.endswith(".zip"):
                    return url
                    
            return None
            
        except Exception as e:
            return None
    
    def get_model_size_limit(self) -> int:
        """根据硬件配置获取模型大小限制（MB）"""
        cpu_cores = self.hw.cpu_cores
        memory_gb = self.hw.memory_total_gb
        
        if cpu_cores < 2 or memory_gb < 4:
            return self.MODEL_SIZE_LIMITS["low"]
        elif cpu_cores <= 8 and memory_gb <= 16:
            return self.MODEL_SIZE_LIMITS["medium"]
        else:
            return self.MODEL_SIZE_LIMITS["high"]
    
    def check_model_size(self, model_path: str) -> Tuple[bool, str]:
        """检查模型大小是否适合当前硬件"""
        try:
            size_bytes = os.path.getsize(model_path)
            size_mb = size_bytes / (1024 * 1024)
            limit_mb = self.get_model_size_limit()
            
            if size_mb > limit_mb:
                return False, f"模型大小 {size_mb:.1f}MB 超过当前硬件限制 {limit_mb}MB"
            return True, f"模型大小 {size_mb:.1f}MB，符合硬件要求（限制 {limit_mb}MB）"
        except:
            return False, "无法检查模型大小"
    
    def check_katago(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """检测KataGo安装"""
        common_paths = [
            "katago",
            "/usr/local/bin/katago",
            "/usr/bin/katago",
            os.path.expanduser("~/.local/bin/katago"),
            os.path.expanduser("~/katago"),
        ]
        
        for path in common_paths:
            try:
                result = subprocess.run([path, "version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version = result.stdout.strip() or result.stderr.strip()
                    return True, path, version
            except:
                continue
        
        return False, None, None
    
    def check_models(self) -> List[Dict]:
        """检测可用的模型文件"""
        models = []
        
        search_paths = [
            Path("."),
            Path.home(),
            Path.home() / "katago",
            Path.home() / ".katago",
            Path("/usr/local/share/katago"),
        ]
        
        for path in search_paths:
            if not path.exists():
                continue
            for pattern in ["*.bin.gz", "*.txt.gz"]:
                for model_file in path.glob(pattern):
                    size_mb = model_file.stat().st_size / (1024 * 1024)
                    models.append({
                        "name": model_file.stem.replace(".bin", "").replace(".txt", ""),
                        "path": str(model_file),
                        "size_mb": size_mb
                    })
        
        return models
    
    def find_config(self) -> Optional[str]:
        """查找配置文件"""
        config_paths = [
            "analysis.cfg",
            "default.cfg",
            "katago.cfg",
            "/usr/local/etc/katago/analysis.cfg",
            os.path.expanduser("~/.katago/analysis.cfg"),
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                return path
        return None
    
    def run_setup(self):
        """运行完整设置流程"""
        print("KataGo 环境检测")
        print("=" * 50)
        
        # 1. 硬件检测
        print("\n📊 硬件检测")
        self.profiler.print_summary(self.hw)
        
        # 2. KataGo检测
        print("\n" + "=" * 50)
        print("🔍 KataGo 检测")
        
        installed, path, version = self.check_katago()
        
        if installed:
            print(f"  [✓] KataGo 已安装")
            print(f"      路径: {path}")
            print(f"      版本: {version}")
        else:
            print(f"  [✗] KataGo 未安装")
            print("\n  安装指引:")
            self._print_install_guide()
        
        # 3. 模型检测
        print("\n" + "=" * 50)
        print("🧠 模型检测")
        
        models = self.check_models()
        
        if models:
            print(f"  [✓] 找到 {len(models)} 个模型:")
            for m in models:
                is_suitable, msg = self.check_model_size(m['path'])
                status = "✓" if is_suitable else "⚠️"
                print(f"      {status} {m['name']} ({m['size_mb']:.1f}MB) @ {m['path']}")
                if not is_suitable:
                    print(f"         警告: {msg}")
                    print(f"         该模型在当前配置下运行可能很慢或内存不足")
        else:
            print(f"  [✗] 未找到模型文件")
            print("\n  推荐下载:")
            self._print_model_guide()
        
        # 4. 配置文件
        print("\n" + "=" * 50)
        print("⚙️ 配置文件")
        
        config = self.find_config()
        if config:
            print(f"  [✓] 找到配置文件: {config}")
        else:
            print(f"  [✗] 未找到配置文件")
            if installed and models:
                print("\n  建议生成配置:")
                print(f"  weiqi-katago setup --generate-config")
        
        # 5. 状态总结
        print("\n" + "=" * 50)
        print("📋 状态总结")
        
        if installed and models:
            print("  [✓] 环境就绪，可以开始分析")
            print("\n  快速开始:")
            print("    weiqi-katago analyze game.sgf")
        else:
            print("  [✗] 环境不完整，请按上述指引安装")
    
    def _print_install_guide(self):
        """打印安装指引"""
        os_name = self.hw.os
        arch = self.hw.cpu_arch
        
        latest_url = self.get_latest_katago_url()
        
        print(f"\n  Linux (推荐):")
        print(f"    1. 下载 KataGo (最新版本):")
        
        if latest_url:
            print(f"       wget \"{latest_url}\" -O katago.zip")
            print(f"       unzip katago.zip")
            print(f"       sudo mv katago /usr/local/bin/")
            print(f"       rm katago.zip")
        else:
            print(f"       # 无法获取最新版本，请手动下载:")
            print(f"       # 访问: https://github.com/lightvector/KataGo/releases/latest")
            print(f"       # 下载对应系统版本 (推荐 eigenavx2 版本)")
        
        print(f"    2. 验证安装:")
        print(f"       katago version")
        
        print(f"\n  macOS:")
        print(f"    brew install katago")
        
        print(f"\n  Windows:")
        print(f"    scoop install katago")
    
    def _print_model_guide(self):
        """打印模型下载指引"""
        limit_mb = self.get_model_size_limit()
        
        print(f"\n  当前硬件配置:")
        print(f"    CPU: {self.hw.cpu_cores}核")
        print(f"    内存: {self.hw.memory_total_gb:.1f}GB")
        print(f"    模型大小限制: {limit_mb}MB")
        
        suitable_models = []
        for name, info in self.MODEL_URLS.items():
            if info.get("size_mb", 999) <= limit_mb:
                suitable_models.append((name, info))
        
        if suitable_models:
            print(f"\n  推荐模型（适合当前配置）:")
            for name, info in suitable_models:
                print(f"\n    {name}")
                print(f"    大小: {info['size_mb']}MB")
                print(f"    说明: {info['description']}")
                print(f"    下载: wget \"{info['url']}\" -O {name}.txt.gz")
        else:
            print(f"\n  ⚠️ 当前硬件配置较低，建议先升级配置")
        
        print(f"\n  注意: 大型模型需要更多内存和计算时间")
        print(f"        当前限制: {limit_mb}MB")
    
    def generate_config(self, output_path: str = "analysis.cfg"):
        """生成优化的配置文件"""
        config = self.profiler.generate_config(self.hw, "b18c384nbt")
        
        with open(output_path, 'w') as f:
            f.write(config)
        
        print(f"配置文件已生成: {output_path}")
        print(f"  - CPU线程: {self.hw.cpu_cores}")
        print(f"  - {'GPU' if self.hw.cuda else 'CPU'} 模式")
        
        return output_path
    
    def validate_environment(self) -> Tuple[bool, str]:
        """验证环境是否可用"""
        installed, path, version = self.check_katago()
        if not installed:
            return False, "KataGo 未安装，请运行: weiqi-katago setup"
        
        models = self.check_models()
        if not models:
            return False, "未找到模型文件，请运行: weiqi-katago setup 查看下载指引"
        
        return True, "环境正常"


def main():
    """命令行入口"""
    setup = KataGoSetup()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--generate-config":
        setup.generate_config()
    else:
        setup.run_setup()


if __name__ == "__main__":
    main()
