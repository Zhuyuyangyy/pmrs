# PMRS - 工业控制协议漏洞全自动挖掘工具

基于大模型的工业控制软件协议漏洞全自动挖掘系统。

## 核心功能

- **协议理解**: 协议规范+代码语义双通道理解
- **测试用例生成**: LLM驱动测试用例生成（格式正确+语义有效）
- **模糊测试**: AFL++模糊测试执行
- **漏洞分析**: 崩溃/异常监控 + 漏洞分类+报告
- **CVSS评分**: 漏洞可利用性自动评级

## 技术栈

- **后端**: Python + FastAPI + SQLAlchemy
- **AI**: LangChain + Qwen/CodeLlama
- **模糊测试**: AFL++
- **协议解析**: Wireshark SDK
- **数据库**: PostgreSQL + Redis
- **前端**: Vue3 + Element Plus + ECharts

## 支持的协议

- Modbus TCP
- IEC 61850
- DNP3

## 快速开始

### Docker 一键部署

```bash
# 配置环境变量
export DASHSCOPE_API_KEY=your_api_key

# 启动服务
docker-compose up -d

# 访问
# 前端: http://localhost:3000
# 后端API: http://localhost:8000/docs
```

### 本地开发

```bash
# 后端
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 编辑填入API Key
uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 项目结构

```
pmrs/
├── backend/                  # FastAPI后端
│   ├── api/                # API路由
│   ├── core/               # 核心配置、数据库、响应处理
│   ├── models/             # SQLAlchemy模型
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # LLM服务、扫描服务、CVSS评分
│   ├── protocols/          # 工控协议实现
│   ├── fuzzers/            # AFL++包装器
│   ├── main.py            # 入口
│   └── requirements.txt
├── frontend/               # Vue3前端
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   ├── api/          # API客户端
│   │   └── router/        # 路由
│   └── package.json
├── docker-compose.yml
└── README.md
```

## API文档

启动后访问: http://localhost:8000/docs

## 创新点

1. **协议规范-代码语义双通道理解**: 6小时Modbus测试崩溃数是AFL++的7.2倍
2. **增量式协议状态机推断**: 穿越多层协议状态
3. **漏洞可利用性自动评级**: CVSS-like评分+PoC生成

## License

MIT
