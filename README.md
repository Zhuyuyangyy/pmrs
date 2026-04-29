# PMRS v1.0 快速启动脚本

## 环境准备

```bash
cd D:\ZYY Project\pmrs\backend
pip install -r requirements.txt
```

## 快速开始

### 1. 启动后端服务

```bash
python app.py
```

服务地址：
- API: http://localhost:8011
- 文档: http://localhost:8011/docs

### 2. 启动前端

直接在浏览器打开 `D:\ZYY Project\pmrs\frontend\index.html`

或者使用 Python 静态文件服务器：

```bash
cd D:\ZYY Project\pmrs\frontend
python -m http.server 8012
```

访问 http://localhost:8012

### 3. 开始训练（2× RTX 3090）

```bash
cd D:\ZYY Project\pmrs\backend
python train/train_multigpu.py --epochs 50 --batch_size 16
```

## 项目结构

```
pmrs/
├── backend/
│   ├── models/
│   │   ├── gene_encoder.py     # Geneformer-style Transformer
│   │   ├── path_encoder.py     # ResNet50 + Attention
│   │   ├── text_encoder.py     # BioBERT
│   │   ├── fusion.py           # Cross-attention fusion
│   │   └── multimodal.py       # 完整多模态模型
│   ├── data_loader/
│   │   └── tcga_dataset.py     # TCGA数据加载器
│   ├── train/
│   │   └── train_multigpu.py   # 多GPU训练脚本
│   ├── evaluation/
│   │   └── metrics.py          # 评估指标
│   ├── app.py                  # FastAPI 后端
│   ├── config.yaml             # 配置文件
│   └── requirements.txt
├── frontend/
│   └── index.html              # Vue3 可视化界面
└── README.md
```

## 快速测试

### 测试后端API

```bash
# 健康检查
curl http://localhost:8011/health

# 模型信息
curl http://localhost:8011/model/info

# 风险预测（需要 gene expression 数据）
curl -X POST http://localhost:8011/predict/risk \
  -H "Content-Type: application/json" \
  -d '{"values": [0.1, -0.2, ...], "sample_id": "test"}'
```

## 硬件要求

- GPU: 2× RTX 3090 (24GB each) 或等效算力
- 内存: 32GB+
- 存储: 100GB+ (TCGA数据集)
