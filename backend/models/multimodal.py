"""
MultiModalModel: Complete multi-modal architecture for precision medicine
Combines GeneEncoder + PathEncoder + TextEncoder with Fusion module
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from models.gene_encoder import GeneEncoder, GeneFeatureExtractor
from models.path_encoder import PathEncoder, PathEncoderMultipleInstance
from models.text_encoder import TextEncoder
from models.fusion import CrossAttentionFusion, ConcatFusion, GatedFusion, AttentionFusion


class MultiModalPMRS(nn.Module):
    """
    Complete Multi-Modal Precision Medicine Recommendation System.
    
    Inputs:
        gene_expression: (B, 20000) — RNA-seq gene expression values
        pathway_activity: (B, 50) — pathway-level aggregations (optional)
        path_tiles: (B, N, C, H, W) — histopathology image tiles (optional)
        clinical_text: (B, L) — tokenized clinical notes (optional)
    
    Outputs:
        risk_score: (B,) — predicted risk score (0-1)
        treatment_rec: (B, n_treatments) — treatment recommendation logits
        survival_pred: (B, n_years) — survival prediction over time
        embeddings: dict of modality embeddings for analysis
    """
    
    def __init__(
        self,
        # Gene encoder config
        n_genes: int = 20000,
        n_pathways: int = 50,
        d_model: int = 768,
        # Path encoder config
        n_path_tiles: int = 16,
        # Text encoder config
        text_model_name: str = "dmis-lab/biobert-base-cased-v1.2",
        # Fusion config
        fusion_type: str = "cross_attention",  # "cross_attention" | "concat" | "gated" | "attention"
        # Task config
        n_risk_classes: int = 2,  # binary risk (high/low) or multi-class
        n_treatments: int = 10,  # number of treatment options
        n_survival_years: int = 5,
        # Architecture
        use_pathology: bool = True,
        use_text: bool = True,
        use_pathways: bool = True,
        dropout: float = 0.2
    ):
        super().__init__()
        
        self.d_model = d_model
        self.fusion_type = fusion_type
        self.use_pathology = use_pathology
        self.use_text = use_text
        self.use_pathways = use_pathways
        
        # === Modality Encoders ===
        # Gene encoder (Transformer-based)
        self.gene_encoder = GeneEncoder(
            n_genes=n_genes,
            d_model=d_model,
            n_heads=12,
            n_layers=6
        )
        
        # Optional: pathway-based encoder (more efficient)
        if use_pathways:
            self.pathway_encoder = GeneFeatureExtractor(
                n_pathways=n_pathways,
                d_model=d_model
            )
        
        # Pathology encoder (CNN-based)
        if use_pathology:
            self.path_encoder = PathEncoder(
                d_model=d_model,
                pretrained=True
            )
        
        # Clinical text encoder (BERT-based)
        if use_text:
            self.text_encoder = TextEncoder(
                model_name=text_model_name,
                d_model=d_model,
                pooling="cls",
                freeze_layers=0  # Finetune all layers
            )
        
        # === Fusion Module ===
        fusion_dim = d_model * (2 if use_pathways else 1) + (d_model if use_pathology else 0) + (d_model if use_text else 0)
        
        if fusion_type == "cross_attention":
            self.fusion = CrossAttentionFusion(d_model=d_model, n_heads=8, dropout=dropout)
        elif fusion_type == "concat":
            self.fusion = ConcatFusion(n_modalities=3, d_model=d_model, hidden_dim=d_model * 2, dropout=dropout)
        elif fusion_type == "gated":
            self.fusion = GatedFusion(d_model=d_model, dropout=dropout)
        elif fusion_type == "attention":
            self.fusion = AttentionFusion(d_model=d_model, dropout=dropout)
        else:
            raise ValueError(f"Unknown fusion type: {fusion_type}")
        
        # === Task Heads ===
        # Risk prediction head
        self.risk_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.LayerNorm(d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1),
            nn.Sigmoid() if n_risk_classes == 2 else nn.Softmax(dim=-1)
        )
        
        # Treatment recommendation head
        self.treatment_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, n_treatments)
        )
        
        # Survival prediction head (Cox proportional hazards)
        self.survival_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.LayerNorm(d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, n_survival_years)
        )
        
        # Modality dropouts for contrastive learning
        self.modality_dropout = nn.Dropout(dropout)
        
    def forward(
        self,
        gene_expression,
        pathway_activity=None,
        path_tiles=None,
        clinical_text=None,
        input_ids=None,
        attention_mask=None,
        return_embeddings=False
    ):
        """
        Forward pass.
        
        Args:
            gene_expression: (B, 20000)
            pathway_activity: (B, 50) [optional]
            path_tiles: (B, N, C, H, W) or (B, C, H, W) [optional]
            clinical_text: dict with 'input_ids', 'attention_mask' [optional]
            return_embeddings: bool
        
        Returns:
            dict with keys: risk_score, treatment_logits, survival_logits
            optionally: embeddings dict
        """
        embeddings = {}
        
        # === Gene encoding ===
        gene_emb = self.gene_encoder(gene_expression)  # (B, d_model)
        gene_emb = self.modality_dropout(gene_emb)
        embeddings['gene'] = gene_emb
        
        # Optional pathway encoding
        if self.use_pathways and pathway_activity is not None:
            pathway_emb = self.pathway_encoder(gene_expression, pathway_activity)
            embeddings['pathway'] = pathway_emb
        else:
            pathway_emb = None
            
        # === Pathology encoding ===
        if self.use_pathology and path_tiles is not None:
            path_emb = self.path_encoder(path_tiles)
            path_emb = self.modality_dropout(path_emb)
            embeddings['pathology'] = path_emb
        else:
            path_emb = None
            
        # === Text encoding ===
        if self.use_text and clinical_text is not None:
            text_emb = self.text_encoder(
                input_ids=clinical_text.get('input_ids', input_ids),
                attention_mask=clinical_text.get('attention_mask', attention_mask)
            )
            text_emb = self.modality_dropout(text_emb)
            embeddings['text'] = text_emb
        else:
            text_emb = None
        
        # === Fusion ===
        # Collect embeddings for fusion
        gene_to_fuse = gene_emb
        path_to_fuse = path_emb if path_emb is not None else torch.zeros_like(gene_emb)
        text_to_fuse = text_emb if text_emb is not None else torch.zeros_like(gene_emb)
        
        # Handle missing modalities
        if path_emb is None:
            path_to_fuse = torch.zeros_like(gene_emb)
        if text_emb is None:
            text_to_fuse = torch.zeros_like(gene_emb)
            
        fused = self.fusion(gene_to_fuse, path_to_fuse, text_to_fuse)  # (B, d_model)
        embeddings['fused'] = fused
        
        # === Task heads ===
        outputs = {}
        outputs['risk_score'] = self.risk_head(fused).squeeze(-1)  # (B,) or (B, n_classes)
        outputs['treatment_logits'] = self.treatment_head(fused)  # (B, n_treatments)
        outputs['survival_logits'] = self.survival_head(fused)  # (B, n_years) — hazard scores
        
        if return_embeddings:
            outputs['embeddings'] = embeddings
            
        return outputs


class MultiModalTrainerWrapper(nn.Module):
    """
    Wrapper for training with multi-task loss.
    Handles modality dropout (some modalities may be missing at test time).
    """
    
    def __init__(self, model: MultiModalPMRS, lambda_risk: float = 1.0, lambda_treatment: float = 0.5, lambda_survival: float = 0.3):
        super().__init__()
        self.model = model
        self.lambda_risk = lambda_risk
        self.lambda_treatment = lambda_treatment
        self.lambda_survival = lambda_survival
        
    def forward(self, batch, return_losses=False):
        """
        Batch contains:
            gene_expression: (B, 20000)
            pathway_activity: (B, 50) [optional]
            path_tiles: (B, N, C, H, W) [optional]
            clinical_text: dict [optional]
            risk_label: (B,) — 0/1 for binary risk
            treatment_label: (B,) — treatment class
            survival_time: (B,) — time to event
            survival_event: (B,) — 1 if event (death), 0 if censored
        """
        outputs = self.model(
            gene_expression=batch['gene_expression'],
            pathway_activity=batch.get('pathway_activity'),
            path_tiles=batch.get('path_tiles'),
            clinical_text=batch.get('clinical_text'),
            input_ids=batch.get('input_ids'),
            attention_mask=batch.get('attention_mask')
        )
        
        if return_losses:
            losses = {}
            
            # Risk loss (binary cross-entropy)
            if 'risk_label' in batch:
                losses['risk'] = F.binary_cross_entropy(
                    outputs['risk_score'],
                    batch['risk_label'].float()
                )
            
            # Treatment loss (cross-entropy)
            if 'treatment_label' in batch:
                losses['treatment'] = F.cross_entropy(
                    outputs['treatment_logits'],
                    batch['treatment_label']
                )
            
            # Survival loss (Cox partial likelihood)
            if 'survival_time' in batch and 'survival_event' in batch:
                losses['survival'] = self._cox_loss(
                    outputs['survival_logits'],
                    batch['survival_time'],
                    batch['survival_event']
                )
            
            # Total loss
            total_loss = (
                self.lambda_risk * losses.get('risk', 0) +
                self.lambda_treatment * losses.get('treatment', 0) +
                self.lambda_survival * losses.get('survival', 0)
            )
            losses['total'] = total_loss
            
            return outputs, losses
        
        return outputs
    
    def _cox_loss(self, hazard_scores, survival_time, survival_event):
        """
        Cox proportional hazards loss (negative log partial likelihood).
        Higher hazard = higher risk of event.
        """
        # Sort by survival time (descending — events first)
        sorted_idx = torch.argsort(survival_time, descending=True)
        hazard_sorted = hazard_scores[sorted_idx]
        event_sorted = survival_event[sorted_idx].float()
        
        # Risk scores (higher = more risk)
        risk = torch.exp(hazard_sorted)  # exp(hazard) for Cox
        
        # Log partial likelihood
        log_partial_lik = 0.0
        for i in range(len(risk)):
            if event_sorted[i] == 1:
                # Event: compare to all at risk
                at_risk = risk[i:]
                log_partial_lik += hazard_sorted[i] - torch.log(at_risk.sum() + 1e-8)
        
        return -log_partial_lik / (event_sorted.sum() + 1e-8)
