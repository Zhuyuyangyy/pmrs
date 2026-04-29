"""
TextEncoder: BERT-based encoder for clinical text (电子病历/病史)
Uses ClinicalBERT / BioBERT pretrained weights
"""
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer, AutoConfig


class TextEncoder(nn.Module):
    """
    Encoder for clinical text using pretrained BioBERT/ClinicalBERT.
    
    Architecture:
    - Pretrained BioBERT backbone
    - [CLS] token for document-level representation
    - Optional: attention pooling over sub-word tokens
    """
    
    def __init__(
        self,
        model_name: str = "dmis-lab/biobert-base-cased-v1.2",
        d_model: int = 768,
        pooling: str = "cls",  # "cls" | "mean" | "attention"
        freeze_layers: int = 0,  # Number of layers to freeze (0 = finetune all)
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.model_name = model_name
        self.d_model = d_model
        self.pooling = pooling
        
        # Load pretrained model and tokenizer
        self.transformer = AutoModel.from_pretrained(model_name)
        self.d_backbone = self.transformer.config.hidden_size
        
        # Freeze early layers if specified
        if freeze_layers > 0:
            self._freeze_layers(freeze_layers)
        
        # Projection to target dimension
        if self.d_backbone != d_model:
            self.projection = nn.Linear(self.d_backbone, d_model)
        else:
            self.projection = nn.Identity()
        
        # Attention pooling (optional)
        if pooling == "attention":
            self.attention_pool = AttentionTextPooling(self.d_backbone)
        else:
            self.attention_pool = None
            
        self.layer_norm = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)
        
    def _freeze_layers(self, n_layers):
        """Freeze first n_layers of transformer"""
        # BioBERT has 12 layers (0-11)
        for i in range(n_layers):
            for param in self.transformer.encoder.layer[i].parameters():
                param.requires_grad = False
                
    def _pooling(self, hidden_states, attention_mask):
        if self.pooling == "cls":
            # Use [CLS] token (first token)
            pooled = hidden_states[:, 0]
        elif self.pooling == "mean":
            # Mean pooling over non-padded tokens
            mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
            sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
            pooled = sum_embeddings / sum_mask
        elif self.pooling == "attention":
            pooled, _ = self.attention_pool(hidden_states, attention_mask)
        else:
            pooled = hidden_states[:, 0]
        return pooled
        
    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        """
        Args:
            input_ids: (B, L) — tokenized text
            attention_mask: (B, L) — 1 for real tokens, 0 for padding
            token_type_ids: (B, L) — sentence segment ids
        Returns:
            text_embedding: (B, d_model)
        """
        outputs = self.transformer(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        
        hidden_states = outputs.last_hidden_state  # (B, L, d_backbone)
        
        # Pooling
        pooled = self._pooling(hidden_states, attention_mask)
        
        # Project and normalize
        text_embedding = self.layer_norm(self.projection(pooled))
        text_embedding = self.dropout(text_embedding)
        
        return text_embedding


class AttentionTextPooling(nn.Module):
    """Attention-based pooling for text"""
    
    def __init__(self, d_model: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(d_model, d_model // 4),
            nn.Tanh(),
            nn.Linear(d_model // 4, 1)
        )
        
    def forward(self, hidden_states, attention_mask):
        # Compute attention weights
        attn_scores = self.attention(hidden_states).squeeze(-1)  # (B, L)
        
        # Mask padding tokens
        attn_scores = attn_scores.masked_fill(attention_mask == 0, float('-inf'))
        attn_weights = torch.softmax(attn_scores, dim=-1).unsqueeze(-1)  # (B, L, 1)
        
        # Weighted sum
        pooled = (hidden_states * attn_weights).sum(dim=1)  # (B, d_model)
        return pooled, attn_weights.squeeze(-1)


class TextEncoderSimple(nn.Module):
    """
    Simplified text encoder using TF-IDF + MLP.
    For quick experiments before using full BioBERT.
    """
    
    def __init__(self, vocab_size: int = 10000, d_model: int = 768, n_classes: int = None):
        super().__init__()
        
        self.embedding = nn.EmbeddingBag(vocab_size, d_model, mode='mean')
        
        self.encoder = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model)
        )
        
        # Optional classification head
        if n_classes:
            self.classifier = nn.Linear(d_model, n_classes)
        
    def forward(self, token_ids, offsets=None):
        """
        Args:
            token_ids: (B, L) — bag-of-words indices
            offsets: not used for EmbeddingBag
        Returns:
            (B, d_model)
        """
        text_feat = self.embedding(token_ids)  # (B, d_model)
        text_feat = self.encoder(text_feat)
        return text_feat
