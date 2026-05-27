#!/bin/bash
# PMRS - 工业控制协议漏洞全自动挖掘系统
# 基于大模型的工业控制软件协议漏洞全自动挖掘工具

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  PMRS - 工业控制协议漏洞挖掘系统"
echo "  支持: Modbus TCP / IEC 61850 / DNP3"
echo "=============================================="
echo

# 虚拟环境
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[PMRS] 创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# 安装依赖
pip install -q fastapi uvicorn sqlalchemy python-dotenv pydantic pyyaml langchain langchain-community 2>/dev/null

# 启动后端
echo "[PMRS] 启动后端服务..."
cd "$SCRIPT_DIR/backend"
echo "[PMRS] 访问: http://localhost:8000"
echo "[PMRS] API文档: http://localhost:8000/docs"
python3 main.py