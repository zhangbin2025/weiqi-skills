#!/usr/bin/env python3
"""
ClawHub 安全扫描预检工具
在发布前检查代码中可能被标记的敏感模式
"""

import os
import re
import sys
from pathlib import Path

# 敏感模式列表（会被 ClawHub 安全扫描标记）
SUSPICIOUS_PATTERNS = {
    "ssl_global_disable": {
        "pattern": r"ssl\._create_default_https_context\s*=",
        "description": "全局禁用 SSL 验证",
        "severity": "HIGH"
    },
    "ssl_cert_none_const": {
        "pattern": r"ssl\.CERT_NONE",
        "description": "使用 ssl.CERT_NONE 常量",
        "severity": "HIGH"
    },
    "ssl_verify_mode_zero": {
        "pattern": r"verify_mode\s*=\s*0",
        "description": "SSL verify_mode 设为 0（可能是 CERT_NONE）",
        "severity": "MEDIUM"
    },
    "innerHTML_assignment": {
        "pattern": r"\.innerHTML\s*=",
        "description": "直接赋值 innerHTML（XSS风险）",
        "severity": "MEDIUM"
    },
    "eval_function": {
        "pattern": r"\beval\s*\(",
        "description": "使用 eval() 函数",
        "severity": "HIGH"
    },
    "exec_function": {
        "pattern": r"\bexec\s*\(",
        "description": "使用 exec() 函数",
        "severity": "HIGH"
    },
    "os_system": {
        "pattern": r"os\.system\s*\(",
        "description": "使用 os.system() 执行命令",
        "severity": "HIGH"
    },
    "subprocess_shell": {
        "pattern": r"subprocess\..*shell\s*=\s*True",
        "description": "subprocess 使用 shell=True",
        "severity": "HIGH"
    },
    "compile_code": {
        "pattern": r"\bcompile\s*\(\s*['\"]",
        "description": "动态编译代码",
        "severity": "MEDIUM"
    },
    "import_module_dynamic": {
        "pattern": r"__import__\s*\(|importlib\.import_module",
        "description": "动态导入模块",
        "severity": "LOW"
    },
    "base64_decode_exec": {
        "pattern": r"base64\.(b64decode|decodestring).*exec|eval",
        "description": "Base64 解码后执行",
        "severity": "HIGH"
    },
    "requests_verify_false": {
        "pattern": r"verify\s*=\s*False",
        "description": "requests 禁用证书验证",
        "severity": "MEDIUM"
    }
}

# 文件扩展名映射
FILE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".html": "HTML",
    ".sh": "Shell",
    ".bash": "Shell"
}

class SecurityScanner:
    def __init__(self, skill_path):
        self.skill_path = Path(skill_path)
        self.findings = []
        self.files_scanned = 0
        
    def scan_file(self, file_path):
        """扫描单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            print(f"  ⚠️  无法读取文件 {file_path}: {e}")
            return
        
        ext = file_path.suffix
        if ext not in FILE_EXTENSIONS:
            return
        
        self.files_scanned += 1
        
        # 根据文件类型选择要检查的模式
        # JavaScript/HTML 文件中跳过 Python 特有的模式
        skip_patterns = set()
        if ext in ['.js', '.ts', '.html']:
            # JavaScript 的 regex.exec() 是正常用法，不是 Python 的 exec()
            skip_patterns.add('exec_function')
        
        # 检查每种模式
        for pattern_name, pattern_info in SUSPICIOUS_PATTERNS.items():
            if pattern_name in skip_patterns:
                continue
            
            regex = re.compile(pattern_info["pattern"], re.IGNORECASE)
            
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    # 对于 Python 文件，检查是否是嵌入的 JavaScript 代码
                    if ext == '.py' and pattern_name == 'exec_function':
                        # 如果行中包含明显的 JavaScript 语法，跳过
                        js_indicators = ['!==', '===', 'let ', 'const ', 'var ', 'null', 'undefined', 'function(', '=>']
                        if any(ind in line for ind in js_indicators):
                            continue
                    
                    self.findings.append({
                        "file": str(file_path.relative_to(self.skill_path)),
                        "line": line_num,
                        "pattern": pattern_name,
                        "description": pattern_info["description"],
                        "severity": pattern_info["severity"],
                        "code": line.strip()[:80]
                    })
    
    def scan_directory(self, directory):
        """递归扫描目录"""
        path = self.skill_path / directory
        if not path.exists():
            return
        
        for item in path.rglob('*'):
            if item.is_file():
                self.scan_file(item)
    
    def run(self):
        """运行扫描"""
        print(f"🔍 扫描技能包: {self.skill_path.name}")
        print(f"{'='*60}")
        
        # 扫描主要代码目录
        for subdir in ["scripts", "src", "lib", "."]:
            self.scan_directory(subdir)
        
        # 输出结果
        print(f"\n📊 扫描结果:")
        print(f"  扫描文件数: {self.files_scanned}")
        print(f"  发现问题数: {len(self.findings)}")
        
        if not self.findings:
            print(f"\n✅ 未发现可疑模式，可以安全发布！")
            return 0
        
        # 按严重程度分组
        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for finding in self.findings:
            severity_counts[finding["severity"]] += 1
        
        print(f"\n⚠️  问题分布:")
        for sev, count in severity_counts.items():
            if count > 0:
                icon = "🔴" if sev == "HIGH" else "🟡" if sev == "MEDIUM" else "🟢"
                print(f"  {icon} {sev}: {count} 个")
        
        print(f"\n📋 详细发现:")
        print(f"{'='*60}")
        
        for finding in self.findings:
            sev_icon = "🔴" if finding["severity"] == "HIGH" else "🟡" if finding["severity"] == "MEDIUM" else "🟢"
            print(f"\n{sev_icon} [{finding['severity']}] {finding['pattern']}")
            print(f"   文件: {finding['file']}:{finding['line']}")
            print(f"   描述: {finding['description']}")
            print(f"   代码: {finding['code']}")
        
        print(f"\n{'='*60}")
        
        if severity_counts["HIGH"] > 0:
            print(f"❌ 发现高危问题，建议修复后再发布！")
            return 1
        elif severity_counts["MEDIUM"] > 0:
            print(f"⚠️  发现中危问题，建议检查是否需要修复")
            return 0
        else:
            print(f"✅ 仅发现低危问题，可以发布")
            return 0

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python3 {sys.argv[0]} <技能包路径>")
        print("")
        print("示例:")
        print(f"  python3 {sys.argv[0]} ./weiqi-foxwq")
        sys.exit(1)
    
    skill_path = sys.argv[1]
    
    if not os.path.exists(skill_path):
        print(f"❌ 路径不存在: {skill_path}")
        sys.exit(1)
    
    scanner = SecurityScanner(skill_path)
    exit_code = scanner.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
