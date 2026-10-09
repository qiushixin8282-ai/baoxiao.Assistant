#!/usr/bin/env python3
"""一键安装 PaddleOCR。

用法：
    python scripts/install_ocr.py        # 安装 CPU 版（默认）
    python scripts/install_ocr.py gpu    # 安装 GPU 版 paddlepaddle-gpu

安装完成后会尝试导入验证。
"""

import subprocess
import sys


def main() -> int:
    target = (sys.argv[1] if len(sys.argv) > 1 else "cpu").lower()
    packages = ["paddleocr"]
    packages.append("paddlepaddle-gpu" if target == "gpu" else "paddlepaddle")

    cmd = [sys.executable, "-m", "pip", "install", *packages]
    print("执行：", " ".join(cmd))
    code = subprocess.call(cmd)
    if code != 0:
        print("安装失败，请检查网络或 pip 源。")
        return code

    print("正在验证导入...")
    try:
        import paddle  # noqa: F401
        import paddleocr  # noqa: F401

        print(f"PaddleOCR 安装成功：paddle {paddle.__version__}")
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"安装完成但导入失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
