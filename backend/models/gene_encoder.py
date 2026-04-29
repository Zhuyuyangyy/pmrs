"""
GeneEncoder: Transformer-based encoder for gene expression sequences
Inspired by Geneformer (Theodoris et al., 2023)
"""
import torch
import torch.nn as nn
from transformers import BertConfig, BertModel


class GeneTokenizer:
    """Tokenize gene expression data into discrete bins"""
    
    def __init__(self, n_bins: int = 512):
        self.n_bins = n_bins
        # Discretize expression values into quantile bins
        self.quantiles = None
        
    def fit(self, expression_matrix):
        """Fit quantile bins from training data"""
        # expression_matrix: (n_genes,) or (n_samples, n_genes)
        flat = expression_matrix.flatten()
        self.quantiles = torch.quantile(flat, torch.linspace(0, 1, self.n_bins + 1))
        
    def tokenize(self, expression_vector):
        """Convert expression values to bin indices"""
        if self.quantiles is None:
            raise ValueError("Tokenizer not fitted")
        # Assign each gene to a bin (0 to n_bins-1)
        tokens = torch.bucketize(expression_vector, self.quantiles[1:-1])
        return tokens


class GeneEncoder(nn.Module):
    """
    Transformer encoder for gene expression data.
    
    Architecture:
    - Embedding layer (gene tokens → embeddings)
    - Transformer encoder (6 layers, 768 dim)
    - CLS token for [CLS] representation
    """
    
    def __init__(
        self,
        n_genes: int = 20000,
        n_bins: int = 512,
        d_model: int = 768,
        n_heads: int = 12,
        n_layers: int = 6,
        d_ff: int = 3072,
        dropout: float = 0.1,
        max_len: int = 2048
    ):
        super().__init__()
        
        self.n_genes = n_genes
        self.n_bins = n_bins
        self.d_model = d_model
        
        # Token embedding: each gene-bin pair becomes a token
        self.token_embedding = nn.Embedding(n_genes * n_bins, d_model)
        self.position_embedding = nn.Embedding(max_len, d_model)
        
        # Transformer encoder (GeneBERT)
        encoder_config = BertConfig(
            hidden_size=d_model,
            num_attention_heads=n_heads,
            num_hidden_layers=n_layers,
            intermediate_size=d_ff,
            hidden_dropout_prob=dropout,
            attention_probs_dropout_prob=dropout,
            max_position_embeddings=max_len
        )
        self.transformer = BertModel(encoder_config)
        
        # [CLS] token for pooled representation
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model))
        
        # Output projection
        self.output_proj = nn.Linear(d_model, d_model)
        self.layer_norm = nn.LayerNorm(d_model)
        
        self._init_weights()
        
    def _init_weights(self):
        nn.init.normal_(self.cls_token, std=0.02)
        
    def forward(self, gene_tokens, attention_mask=None):
        """
        Args:
            gene_tokens: (B, N_genes) — discretized gene expression tokens
            attention_mask: (B, N_genes) — 1 for real tokens, 0 for padding
        Returns:
            gene_embedding: (B, d_model) — pooled gene representation
        """
        B, N = gene_tokens.shape
        
        # Token embedding
        # Map (gene_idx, bin_idx) → embedding
        gene_embedding = self.token_embedding(gene_tokens)  # (B, N, d_model)
        
        # Position embedding
        positions = torch.arange(N, device=gene_tokens.device).unsqueeze(0)
        pos_embedding = self.position_embedding(positions)  # (1, N, d_model)
        
        # Add CLS token at position 0
        cls_tokens = self.cls_token.expand(B, -1, -1)  # (B, 1, d_model)
        hidden_states = torch.cat([cls_tokens, gene_embedding + pos_embedding], dim=1)  # (B, N+1, d_model)
        
        # Extend attention mask for CLS
        if attention_mask is not None:
            cls_mask = torch.ones(B, 1, device=attention_mask.device)
            attention_mask = torch.cat([cls_mask, attention_mask], dim=1)
        
        # Transformer encoding
        outputs = self.transformer(
            inputs_embeds=hidden_states,
            attention_mask=attention_mask
        )
        
        # Use CLS token as representation
        cls_output = outputs.last_hidden_state[:, 0]  # (B, d_model)
        
        # Project and normalize
        gene_embedding = self.layer_norm(self.output_proj(cls_output))
        
        return gene_embedding


class GeneFeatureExtractor(nn.Module):
    """
    Simplified gene encoder using pre-computed gene sets (e.g., pathways).
    More efficient than full sequence modeling.
    """
    
    def __init__(self, n_pathways: int = 50, d_model: int = 768):
        super().__init__()
        
        self.pathway_proj = nn.Linear(n_pathways, d_model)
        self.gene_proj = nn.Linear(20000, 512)
        self.combined_proj = nn.Linear(512 + d_model, d_model)
        self.layer_norm = nn.LayerNorm(d_model)
        
        # Self-attention to capture pathway interactions
        self.attention = nn.MultiheadAttention(d_model, n_heads=8, batch_first=True)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, gene_expression, pathway_activity):
        """
        Args:
            gene_expression: (B, 20000) — raw gene expression values
            pathway_activity: (B, 50) — pathway-level aggregation
        Returns:
            (B, d_model) — gene representation
        """
        # Project gene expression
        gene_feat = self.gene_proj(gene_expression)  # (B, 512)
        gene_feat = torch.relu(gene_feat)
        
        # Project pathway activity
        pathway_feat = self.pathway_proj(pathway_activity)  # (B, d_model)
        
        # Combine
        combined = torch.cat([gene_feat, pathway_feat], dim=-1)  # (B, 512+d_model)
        combined = self.combined_proj(combined)  # (B, d_model)
        
        # Self-attention with residual
        attn_out, _ = self.attention(
            combined.unsqueeze(1), combined.unsqueeze(1), combined.unsqueeze(1)
        )
        combined = combined + self.dropout(attn_out.squeeze(1))
        
        return self.layer_norm(combined)
