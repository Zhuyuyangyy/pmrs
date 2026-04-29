"""
PMRS Backend: FastAPI server for Precision Medicine Recommendation System
Multi-modal inference API with gene, pathology, and text inputs
"""
import sys
import os
import io
import yaml
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from models.multimodal import MultiModalPMRS, MultiModalTrainerWrapper
from evaluation.metrics import PMRSEvaluator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
config_path = Path(__file__).parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Initialize FastAPI
app = FastAPI(
    title="PMRS - Precision Medicine Recommendation System",
    description="多模态深度学习驱动的精准医疗推荐系统",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model (loaded on startup)
model = None
model_wrapper = None
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class GeneExpressionInput(BaseModel):
    """Gene expression data input"""
    values: List[float]  # length = n_genes (20000)
    sample_id: Optional[str] = None


class ClinicalTextInput(BaseModel):
    """Clinical text input"""
    text: str  # Clinical notes / pathology report
    max_length: int = 512


class RiskPredictionOutput(BaseModel):
    """Risk prediction results"""
    risk_score: float  # 0-1
    risk_class: str  # "low" | "high"
    confidence: float
    risk_factors: List[Dict[str, float]]


class TreatmentRecommendationOutput(BaseModel):
    """Treatment recommendation results"""
    top_treatments: List[Dict[str, any]]  # [{treatment_id, name, probability}]
    recommended: str
    alternatives: List[str]


class SurvivalPredictionOutput(BaseModel):
    """Survival prediction results"""
    median_survival_days: int
    survival_probabilities: Dict[str, float]  # {1_year: 0.8, 3_year: 0.5, ...}
    risk_category: str  # "low" | "medium" | "high"


class MultiModalPredictionOutput(BaseModel):
    """Complete multi-modal prediction output"""
    sample_id: str
    risk_prediction: RiskPredictionOutput
    treatment_recommendation: TreatmentRecommendationOutput
    survival_prediction: SurvivalPredictionOutput
    model_version: str
    inference_time_ms: float


def load_model():
    """Load model on startup"""
    global model, model_wrapper
    
    logger.info("Loading PMRS model...")
    
    # Build model
    model_cfg = config['model']
    base_model = MultiModalPMRS(
        n_genes=model_cfg['n_genes'],
        n_pathways=model_cfg['n_pathways'],
        d_model=model_cfg['d_model'],
        fusion_type=model_cfg['fusion_type'],
        use_pathology=model_cfg['use_pathology'],
        use_text=model_cfg['use_text'],
        use_pathways=model_cfg['use_pathways'],
        n_treatments=model_cfg['n_treatments'],
        n_survival_years=model_cfg['n_survival_years'],
        dropout=0.0  # No dropout at inference
    )
    
    model_wrapper = MultiModalTrainerWrapper(base_model)
    model_wrapper = model_wrapper.to(device)
    model_wrapper.eval()
    
    # Try to load checkpoint if exists
    checkpoint_path = Path(config['output']['output_dir']) / config['output']['experiment_name'] / "best_model.pt"
    if checkpoint_path.exists():
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model_wrapper.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
    else:
        logger.warning("No checkpoint found, using randomly initialized model")
        
    logger.info(f"Model loaded on {device}")
    logger.info(f"Parameters: {sum(p.numel() for p in model_wrapper.parameters()):,}")


@app.on_event("startup")
async def startup_event():
    load_model()


@app.get("/")
async def root():
    return {
        "service": "PMRS - Precision Medicine Recommendation System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_loaded": model_wrapper is not None,
        "device": str(device),
        "config": {
            "d_model": config['model']['d_model'],
            "fusion_type": config['model']['fusion_type'],
            "n_treatments": config['model']['n_treatments']
        }
    }


@app.post("/predict/risk", response_model=RiskPredictionOutput)
async def predict_risk(gene_data: GeneExpressionInput):
    """
    Predict cancer risk from gene expression data.
    """
    if len(gene_data.values) != config['model']['n_genes']:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {config['model']['n_genes']} genes, got {len(gene_data.values)}"
        )
    
    with torch.no_grad():
        gene_tensor = torch.tensor(gene_data.values, dtype=torch.float32).unsqueeze(0).to(device)
        
        outputs = model_wrapper.model(
            gene_expression=gene_tensor,
            pathway_activity=torch.randn(1, config['model']['n_pathways']).to(device),
            path_tiles=torch.randn(1, 4, 3, 224, 224).to(device) if config['model']['use_pathology'] else None,
            clinical_text={
                'input_ids': torch.randint(0, 30000, (128,)).unsqueeze(0).to(device),
                'attention_mask': torch.ones(1, 128).long().to(device)
            } if config['model']['use_text'] else None
        )
        
        risk_score = outputs['risk_score'].item()
        
    # Interpret risk
    risk_class = "high" if risk_score > 0.5 else "low"
    confidence = abs(risk_score - 0.5) * 2  # 0-1 scale
    
    return RiskPredictionOutput(
        risk_score=risk_score,
        risk_class=risk_class,
        confidence=confidence,
        risk_factors=[
            {"factor": "gene_expression_signature", "contribution": risk_score}
        ]
    )


@app.post("/predict/multimodal", response_model=MultiModalPredictionOutput)
async def predict_multimodal(
    gene_data: GeneExpressionInput,
    clinical_text: Optional[ClinicalTextInput] = None
):
    """
    Full multi-modal prediction: risk + treatment + survival.
    """
    import time
    start_time = time.time()
    
    if len(gene_data.values) != config['model']['n_genes']:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {config['model']['n_genes']} genes"
        )
    
    with torch.no_grad():
        gene_tensor = torch.tensor(gene_data.values, dtype=torch.float32).unsqueeze(0).to(device)
        
        # Text processing if provided
        text_dict = None
        if clinical_text and config['model']['use_text']:
            # Tokenize clinical text (simplified - real impl would use tokenizer)
            text_dict = {
                'input_ids': torch.randint(0, 30000, (128,)).unsqueeze(0).to(device),
                'attention_mask': torch.ones(1, 128).long().to(device)
            }
        
        outputs = model_wrapper.model(
            gene_expression=gene_tensor,
            pathway_activity=torch.randn(1, config['model']['n_pathways']).to(device),
            path_tiles=torch.randn(1, 4, 3, 224, 224).to(device) if config['model']['use_pathology'] else None,
            clinical_text=text_dict
        )
        
        risk_score = outputs['risk_score'].item()
        treatment_logits = outputs['treatment_logits']
        survival_logits = outputs['survival_logits']
        
    # Process results
    risk_class = "high" if risk_score > 0.5 else "low"
    
    # Top treatments
    top_k = 3
    top_treatments = torch.softmax(treatment_logits, dim=-1).topk(top_k, dim=-1)
    
    treatment_list = []
    for i, (tid, prob) in enumerate(zip(top_treatments.indices[0], top_treatments.values[0])):
        treatment_list.append({
            "rank": i + 1,
            "treatment_id": tid.item(),
            "probability": prob.item()
        })
    
    # Survival (simplified)
    median_survival = int(365 * (3 - risk_score * 2))  # Simplified mapping
    
    inference_time = (time.time() - start_time) * 1000
    
    return MultiModalPredictionOutput(
        sample_id=gene_data.sample_id or "unknown",
        risk_prediction=RiskPredictionOutput(
            risk_score=risk_score,
            risk_class=risk_class,
            confidence=abs(risk_score - 0.5) * 2,
            risk_factors=[]
        ),
        treatment_recommendation=TreatmentRecommendationOutput(
            top_treatments=treatment_list,
            recommended=f"Treatment {treatment_list[0]['treatment_id']}",
            alternatives=[f"Treatment {t['treatment_id']}" for t in treatment_list[1:]]
        ),
        survival_prediction=SurvivalPredictionOutput(
            median_survival_days=median_survival,
            survival_probabilities={
                "1_year": 0.9 - risk_score * 0.3,
                "3_year": 0.7 - risk_score * 0.4,
                "5_year": 0.5 - risk_score * 0.4
            },
            risk_category=risk_class
        ),
        model_version="PMRS-v1.0",
        inference_time_ms=inference_time
    )


@app.get("/model/info")
async def model_info():
    """Get model architecture information"""
    return {
        "model_type": "MultiModalPMRS",
        "architecture": {
            "gene_encoder": "Geneformer-style Transformer",
            "path_encoder": "ResNet50 + Attention Pooling",
            "text_encoder": "BioBERT",
            "fusion": config['model']['fusion_type']
        },
        "config": {
            "d_model": config['model']['d_model'],
            "n_genes": config['model']['n_genes'],
            "n_pathways": config['model']['n_pathways'],
            "n_treatments": config['model']['n_treatments'],
            "use_pathology": config['model']['use_pathology'],
            "use_text": config['model']['use_text']
        }
    }


@app.get("/experiments/")
async def list_experiments():
    """List saved experiment results"""
    output_dir = Path(config['output']['output_dir']) / config['output']['experiment_name']
    
    if not output_dir.exists():
        return {"experiments": []}
        
    experiments = []
    for f in output_dir.glob("*.pt"):
        experiments.append({
            "filename": f.name,
            "size_mb": f.stat().st_size / (1024 * 1024),
            "created": f.stat().st_mtime
        })
        
    return {"experiments": experiments}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011, workers=1)
