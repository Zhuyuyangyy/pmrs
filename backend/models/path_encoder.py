"""
PathEncoder: CNN-based encoder for histopathology whole-slide images
Uses pretrained ResNet50 with attention pooling
"""
import torch
import torch.nn as nn
import timm


class PathEncoder(nn.Module):
    """
    CNN encoder for pathology images.
    
    Architecture:
    - Pretrained ResNet50 backbone (ImageNet weights)
    - Attention-weighted pooling (instead of global avg pool)
    - Feature projection to d_model dimension
    """
    
    def __init__(
        self,
        d_model: int = 768,
        pretrained: bool = True,
        freeze_bn: bool = True,
        dropout: float = 0.2
    ):
        super().__init__()
        
        # Load pretrained ResNet50
        self.backbone = timm.create_model(
            'resnet50',
            pretrained=pretrained,
            num_classes=0,  # Remove classification head
            global_pool=''    # No pooling (we do attention pooling)
        )
        
        # Get feature dimension (ResNet50 = 2048)
        self.d_backbone = 2048
        
        # Attention pooling for multiple tile aggregation
        self.attention_pool = AttentionPooling(d_backbone, d_model)
        
        # Feature projection
        self.projection = nn.Sequential(
            nn.Linear(d_backbone, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, d_model)
        )
        
        self.layer_norm = nn.LayerNorm(d_model)
        
    def forward(self, image_tiles, return_attention_weights=False):
        """
        Args:
            image_tiles: (B, N_tiles, C, H, W) — multiple tiles from one slide
                         or (B, C, H, W) — single image
            return_attention_weights: bool
        Returns:
            path_embedding: (B, d_model)
            attention_weights: (optional) (B, N_tiles)
        """
        if image_tiles.dim() == 5:
            # Multiple tiles: (B, N, C, H, W)
            B, N, C, H, W = image_tiles.shape
            # Reshape to (B*N, C, H, W) for batch processing
            image_flat = image_tiles.view(B * N, C, H, W)
            
            # Extract features
            features = self.backbone.forward_features(image_flat)  # (B*N, features, h', w')
            
            # Adaptive pooling to (B*N, features)
            features = torch.nn.functional.adaptive_avg_pool2d(
                features, (1, 1)
            ).flatten(1)  # (B*N, d_backbone)
            
            # Reshape back to (B, N, features)
            features = features.view(B, N, -1)
            
            # Attention-weighted aggregation
            path_feat, attn_weights = self.attention_pool(features)
            
        else:
            # Single image: (B, C, H, W)
            features = self.backbone.forward_features(image_tiles)
            features = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1)).flatten(1)
            path_feat = features
            attn_weights = None
        
        # Project to d_model
        path_embedding = self.projection(path_feat)
        path_embedding = self.layer_norm(path_embedding)
        
        if return_attention_weights:
            return path_embedding, attn_weights
        return path_embedding


class AttentionPooling(nn.Module):
    """
    Attention-based pooling layer.
    Learns to weight different tiles/features by importance.
    """
    
    def __init__(self, d_in: int, d_out: int):
        super().__init__()
        
        self.attention = nn.Sequential(
            nn.Linear(d_in, d_in // 4),
            nn.Tanh(),
            nn.Linear(d_in // 4, 1),
            nn.Softmax(dim=1)
        )
        
        self.output_proj = nn.Linear(d_in, d_out)
        
    def forward(self, features):
        """
        Args:
            features: (B, N, d_in) — N feature vectors
        Returns:
            pooled: (B, d_out)
            attention_weights: (B, N)
        """
        # Compute attention weights
        attn_scores = self.attention(features)  # (B, N, 1)
        attention_weights = attn_scores.squeeze(-1)  # (B, N)
        
        # Weighted sum
        pooled = (features * attn_scores).sum(dim=1)  # (B, d_in)
        
        # Project output
        pooled = self.output_proj(pooled)  # (B, d_out)
        
        return pooled, attention_weights


class PathEncoderMultipleInstance(nn.Module):
    """
    Multiple Instance Learning (MIL) encoder for WSI.
    Each WSI is treated as a bag of tiles.
    """
    
    def __init__(
        self,
        tile_encoder: nn.Module,
        d_model: int = 768,
        n_heads: int = 8,
        n_layers: int = 2
    ):
        super().__init__()
        
        self.tile_encoder = tile_encoder
        self.d_model = d_model
        
        # Cross-attention between tiles (self-supervised pattern discovery)
        encoder_layer = nn.TransformerEncoderLayer(
            d=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            activation='gelu',
            batch_first=True
        )
        self.tile_transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        # MIL pooling (attention-based)
        self.mil_attention = nn.Sequential(
            nn.Linear(d_model, d_model // 4),
            nn.Tanh(),
            nn.Linear(d_model // 4, 1)
        )
        
        self.layer_norm = nn.LayerNorm(d_model)
        
    def forward(self, tiles):
        """
        Args:
            tiles: (B, N_tiles, C, H, W) or (B, C, H, W)
        Returns:
            (B, d_model) — slide-level representation
        """
        is_bag = tiles.dim() == 5
        
        if is_bag:
            B, N, C, H, W = tiles.shape
            # Encode each tile
            tile_feats = []
            for i in range(B):
                tile_feats.append(self.tile_encoder(tiles[i]))  # (N, d_model)
            tile_feats = torch.stack(tile_feats, dim=0)  # (B, N, d_model)
            
            # Self-attention across tiles
            tile_feats = self.tile_transformer(tile_feats)  # (B, N, d_model)
            
            # MIL attention pooling
            attn_scores = self.mil_attention(tile_feats)  # (B, N, 1)
            attn_weights = torch.softmax(attn_scores, dim=1)
            slide_feat = (tile_feats * attn_weights).sum(dim=1)  # (B, d_model)
        else:
            slide_feat = self.tile_encoder(tiles)  # (B, d_model)
        
        return self.layer_norm(slide_feat)
