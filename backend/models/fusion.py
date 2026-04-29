"""
Fusion Module: Multi-modal fusion for gene, pathology, and text embeddings
Implements cross-attention and concatenate-based fusion strategies
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CrossAttentionFusion(nn.Module):
    """
    Cross-attention based fusion.
    Each modality attends to all other modalities.
    """
    
    def __init__(self, d_model: int = 768, n_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        
        self.d_model = d_model
        self.n_heads = n_heads
        
        # Query, Key, Value projections for each modality
        self.gene_qkv = nn.Linear(d_model, d_model * 3)
        self.path_qkv = nn.Linear(d_model, d_model * 3)
        self.text_qkv = nn.Linear(d_model, d_model * 3)
        
        # Cross-attention: gene attends to path & text
        self.gene_cross_attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        
        # Cross-attention: path attends to gene & text  
        self.path_cross_attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        
        # Cross-attention: text attends to gene & path
        self.text_cross_attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        
        # Output projections with layer norm
        self.gene_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.path_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.text_proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        
        # Final fusion
        self.fusion_layer = nn.Sequential(
            nn.Linear(d_model * 3, d_model * 2),
            nn.LayerNorm(d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 2, d_model)
        )
        
    def forward(self, gene_emb, path_emb, text_emb):
        """
        Args:
            gene_emb: (B, d_model)
            path_emb: (B, d_model)
            text_emb: (B, d_model)
        Returns:
            fused: (B, d_model) — unified multi-modal representation
        """
        B = gene_emb.shape[0]
        
        # Expand to sequences for cross-attention: (B, 1, d_model)
        gene = gene_emb.unsqueeze(1)
        path = path_emb.unsqueeze(1)
        text = text_emb.unsqueeze(1)
        
        # === Cross-modal attention ===
        # Gene attends to Path
        gene2path, _ = self.gene_cross_attn(query=gene, key=path, value=path)
        # Gene attends to Text
        gene2text, _ = self.gene_cross_attn(query=gene, key=text, value=text)
        gene_fused = self.gene_proj(gene_emb + gene2path.squeeze(1) + gene2text.squeeze(1))
        
        # Path attends to Gene
        path2gene, _ = self.path_cross_attn(query=path, key=gene, value=gene)
        # Path attends to Text
        path2text, _ = self.path_cross_attn(query=path, key=text, value=text)
        path_fused = self.path_proj(path_emb + path2gene.squeeze(1) + path2text.squeeze(1))
        
        # Text attends to Gene
        text2gene, _ = self.text_cross_attn(query=text, key=gene, value=gene)
        # Text attends to Path
        text2path, _ = self.text_cross_attn(query=text, key=path, value=path)
        text_fused = self.text_proj(text_emb + text2gene.squeeze(1) + text2path.squeeze(1))
        
        # === Final fusion ===
        fused = torch.cat([gene_fused, path_fused, text_fused], dim=-1)  # (B, d_model * 3)
        fused = self.fusion_layer(fused)  # (B, d_model)
        
        return fused


class ConcatFusion(nn.Module):
    """
    Simple concatenation + MLP fusion.
    Less expressive but more stable for limited data.
    """
    
    def __init__(
        self,
        n_modalities: int = 3,
        d_model: int = 768,
        hidden_dim: int = 1024,
        dropout: float = 0.2
    ):
        super().__init__()
        
        self.fusion = nn.Sequential(
            nn.Linear(d_model * n_modalities, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, d_model)
        )
        
    def forward(self, *modal_embeddings):
        """
        Args:
            modal_embeddings: tuple of (B, d_model) tensors
        Returns:
            fused: (B, d_model)
        """
        concatenated = torch.cat(modal_embeddings, dim=-1)
        return self.fusion(concatenated)


class GatedFusion(nn.Module):
    """
    Gated fusion with learnable modality importance.
    Each modality has a gate controlling its contribution.
    """
    
    def __init__(self, d_model: int = 768, dropout: float = 0.1):
        super().__init__()
        
        # Modality-specific gates
        self.gene_gate = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.Sigmoid()
        )
        self.path_gate = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.Sigmoid()
        )
        self.text_gate = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.Sigmoid()
        )
        
        # Fusion projection
        self.fusion_proj = nn.Sequential(
            nn.Linear(d_model * 3, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        
        # Modality-specific transforms
        self.gene_transform = nn.Linear(d_model, d_model)
        self.path_transform = nn.Linear(d_model, d_model)
        self.text_transform = nn.Linear(d_model, d_model)
        
    def forward(self, gene_emb, path_emb, text_emb):
        """
        Args:
            gene_emb, path_emb, text_emb: (B, d_model)
        Returns:
            fused: (B, d_model)
        """
        # Compute cross-modal context for gating
        gene_context = torch.cat([gene_emb, (path_emb + text_emb) / 2], dim=-1)
        path_context = torch.cat([path_emb, (gene_emb + text_emb) / 2], dim=-1)
        text_context = torch.cat([text_emb, (gene_emb + path_emb) / 2], dim=-1)
        
        # Compute gates
        g_gene = self.gene_gate(gene_context)  # (B, d_model)
        g_path = self.path_gate(path_context)
        g_text = self.text_gate(text_context)
        
        # Gated transformation
        gene_gated = self.gene_transform(gene_emb) * g_gene
        path_gated = self.path_transform(path_emb) * g_path
        text_gated = self.text_transform(text_emb) * g_text
        
        # Concatenate and project
        fused = torch.cat([gene_gated, path_gated, text_gated], dim=-1)
        return self.fusion_proj(fused)


class AttentionFusion(nn.Module):
    """
    Attention-weighted fusion.
    Learns to weight modalities based on their informativeness.
    """
    
    def __init__(self, d_model: int = 768, dropout: float = 0.1):
        super().__init__()
        
        # Modality-specific encoders
        self.gene_encoder = nn.Linear(d_model, d_model)
        self.path_encoder = nn.Linear(d_model, d_model)
        self.text_encoder = nn.Linear(d_model, d_model)
        
        # Cross-modal attention
        self.cross_attn = nn.MultiheadAttention(d_model, n_heads=8, dropout=dropout, batch_first=True)
        
        # Modality attention (how important is each modality?)
        self.modality_attention = nn.Sequential(
            nn.Linear(d_model * 3, 3),  # 3 modalities
            nn.Softmax(dim=-1)
        )
        
        # Final fusion
        self.fusion = nn.Sequential(
            nn.Linear(d_model * 3, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        
    def forward(self, gene_emb, path_emb, text_emb):
        """
        Args:
            gene_emb, path_emb, text_emb: (B, d_model)
        Returns:
            fused: (B, d_model)
        """
        # Encode each modality
        gene_enc = self.gene_encoder(gene_emb)
        path_enc = self.path_encoder(path_emb)
        text_enc = self.text_encoder(text_emb)
        
        # Stack for cross-attention
        combined = torch.stack([gene_enc, path_enc, text_enc], dim=1)  # (B, 3, d_model)
        
        # Self-attention across modalities
        attended, _ = self.cross_attn(combined, combined, combined)
        
        # Attention weights for modality fusion
        combined_flat = torch.cat([gene_emb, path_emb, text_emb], dim=-1)
        mod_weights = self.modality_attention(combined_flat)  # (B, 3)
        
        # Weighted sum of attended features
        gene_att = attended[:, 0]  # (B, d_model)
        path_att = attended[:, 1]
        text_att = attended[:, 2]
        
        weighted = (
            gene_att * mod_weights[:, 0:1] +
            path_att * mod_weights[:, 1:2] +
            text_att * mod_weights[:, 2:3]
        )
        
        # Final projection
        fused = torch.cat([weighted, gene_emb, path_emb, text_emb], dim=-1)
        return self.fusion(fused)
