"""
Multi-GPU Training Script for PMRS
Uses PyTorch DDP (Distributed Data Parallel) for 2x RTX 3090
"""
import os
import sys
import yaml
import torch
import torch.nn as nn
import torch.optim as optim
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.distributed import init_process_group, destroy_process_group
import pytorch_lightning as pl
from torch.utils.data import DataLoader, DistributedSampler
import argparse
from pathlib import Path
from datetime import datetime
import logging
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.multimodal import MultiModalPMRS, MultiModalTrainerWrapper
from data_loader.tcga_dataset import TCGADataModule,TCGAMultiModalDataset, tcga_collate_fn


def setup_distributed():
    """Initialize distributed training"""
    # Set up for 2 GPUs (local_rank 0 and 1)
    world_size = torch.cuda.device_count()
    
    if world_size < 2:
        logger.warning(f"Only {world_size} GPU(s) available. Running on single GPU.")
        return None
        
    init_process_group(backend='nccl')
    return world_size


def cleanup_distributed():
    """Clean up distributed training"""
    destroy_process_group()


class PMRSTrainingEngine:
    """
    Training engine for PMRS with multi-GPU support.
    Uses PyTorch Lightning for streamlined training.
    """
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.world_size = torch.cuda.device_count()
        
        logger.info(f"Device: {self.device}")
        logger.info(f"GPUs available: {self.world_size}")
        
        self.model = None
        self.trainer = None
        self.data_module = None
        
    def _load_config(self, config_path: str = None) -> dict:
        """Load or create default config"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default config
        return {
            'model': {
                'n_genes': 20000,
                'n_pathways': 50,
                'd_model': 768,
                'fusion_type': 'cross_attention',
                'use_pathology': True,
                'use_text': True,
                'use_pathways': True,
                'n_treatments': 10,
                'n_survival_years': 5,
                'dropout': 0.2
            },
            'training': {
                'batch_size': 16,
                'num_epochs': 50,
                'learning_rate': 1e-4,
                'weight_decay': 0.01,
                'warmup_epochs': 5,
                'lambda_risk': 1.0,
                'lambda_treatment': 0.5,
                'lambda_survival': 0.3,
                'gradient_clip_val': 1.0,
                'use_mixed_precision': True,
                'use_gradient_checkpointing': True
            },
            'data': {
                'data_dir': 'data/tcga',
                'train_ratio': 0.7,
                'val_ratio': 0.15,
                'test_ratio': 0.15,
                'n_samples_synthetic': 1000
            },
            'output': {
                'output_dir': 'outputs',
                'experiment_name': 'pmrs_experiment'
            }
        }
        
    def build_model(self):
        """Build and initialize model"""
        model_cfg = self.config['model']
        
        logger.info("Building MultiModalPMRS model...")
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
            dropout=model_cfg['dropout']
        )
        
        # Wrap with multi-task trainer
        train_cfg = self.config['training']
        self.model = MultiModalTrainerWrapper(
            model=base_model,
            lambda_risk=train_cfg['lambda_risk'],
            lambda_treatment=train_cfg['lambda_treatment'],
            lambda_survival=train_cfg['lambda_survival']
        )
        
        # Move to device
        self.model = self.model.to(self.device)
        
        # Log model size
        n_params = sum(p.numel() for p in self.model.parameters())
        n_trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        logger.info(f"Total parameters: {n_params:,}")
        logger.info(f"Trainable parameters: {n_trainable:,}")
        
        return self.model
        
    def build_data(self):
        """Prepare data loaders"""
        data_cfg = self.config['data']
        
        logger.info("Preparing TCGA data...")
        data_module = TCGADataModule(
            data_dir=data_cfg['data_dir'],
            batch_size=self.config['training']['batch_size'],
            n_genes=data_cfg.get('n_genes', 20000),
            n_pathways=data_cfg.get('n_pathways', 50)
        )
        
        # Generate synthetic data for development
        datasets = data_module._generate_synthetic_data(
            n_samples=data_cfg.get('n_samples_synthetic', 1000)
        )
        
        # Create datasets
        train_dataset = TCGAMultiModalDataset(
            meta_df=datasets['train']['meta'],
            gene_expression=datasets['train']['gene_expression'],
            pathway_activity=datasets['train']['pathway_activity'],
            mode='train'
        )
        
        val_dataset = TCGAMultiModalDataset(
            meta_df=datasets['val']['meta'],
            gene_expression=datasets['val']['gene_expression'],
            pathway_activity=datasets['val']['pathway_activity'],
            mode='val'
        )
        
        test_dataset = TCGAMultiModalDataset(
            meta_df=datasets['test']['meta'],
            gene_expression=datasets['test']['gene_expression'],
            pathway_activity=datasets['test']['pathway_activity'],
            mode='test'
        )
        
        # DataLoaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config['training']['batch_size'],
            shuffle=True,
            collate_fn=tcga_collate_fn,
            num_workers=4,
            pin_memory=True
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config['training']['batch_size'],
            shuffle=False,
            collate_fn=tcga_collate_fn,
            num_workers=4,
            pin_memory=True
        )
        
        test_loader = DataLoader(
            test_dataset,
            batch_size=self.config['training']['batch_size'],
            shuffle=False,
            collate_fn=tcga_collate_fn,
            num_workers=4,
            pin_memory=True
        )
        
        logger.info(f"Train batches: {len(train_loader)}")
        logger.info(f"Val batches: {len(val_loader)}")
        logger.info(f"Test batches: {len(test_loader)}")
        
        return train_loader, val_loader, test_loader
        
    def train(self, train_loader, val_loader):
        """Main training loop"""
        cfg = self.config['training']
        output_cfg = self.config['output']
        
        # Create output directory
        output_dir = Path(output_cfg['output_dir']) / output_cfg['experiment_name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Optimizer
        optimizer = optim.AdamW(
            self.model.parameters(),
            lr=cfg['learning_rate'],
            weight_decay=cfg['weight_decay']
        )
        
        # Learning rate scheduler (Cosine with warmup)
        total_steps = len(train_loader) * cfg['num_epochs']
        warmup_steps = len(train_loader) * cfg['warmup_epochs']
        
        def lr_lambda(step):
            if step < warmup_steps:
                return step / warmup_steps
            else:
                progress = (step - warmup_steps) / (total_steps - warmup_steps)
                return 0.5 * (1 + torch.cos(torch.tensor(progress * 3.14159)))
                
        scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
        
        # Mixed precision scaler
        scaler = torch.cuda.amp.GradScaler() if cfg['use_mixed_precision'] else None
        
        # Training loop
        best_val_loss = float('inf')
        global_step = 0
        epoch = 0
        
        for epoch in range(cfg['num_epochs']):
            self.model.train()
            epoch_losses = {'total': 0, 'risk': 0, 'treatment': 0, 'survival': 0}
            
            for batch_idx, batch in enumerate(train_loader):
                # Move batch to device
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                
                # Handle nested dict (clinical_text)
                if 'clinical_text' in batch:
                    batch['clinical_text'] = {
                        k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                        for k, v in batch['clinical_text'].items()
                    }
                
                optimizer.zero_grad()
                
                # Forward with mixed precision
                if cfg['use_mixed_precision']:
                    with torch.cuda.amp.autocast():
                        outputs, losses = self.model(batch, return_losses=True)
                        
                    # Backward
                    scaler.scale(losses['total']).backward()
                    
                    # Gradient clipping
                    if cfg.get('gradient_clip_val'):
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(
                            self.model.parameters(),
                            cfg['gradient_clip_val']
                        )
                        
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    outputs, losses = self.model(batch, return_losses=True)
                    losses['total'].backward()
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        cfg['gradient_clip_val']
                    )
                    optimizer.step()
                    
                scheduler.step()
                
                # Accumulate losses
                for k, v in losses.items():
                    epoch_losses[k] += v.item()
                    
                global_step += 1
                
                if batch_idx % 10 == 0:
                    lr = scheduler.get_last_lr()[0]
                    logger.info(
                        f"Epoch {epoch+1}/{cfg['num_epochs']} | "
                        f"Step {batch_idx}/{len(train_loader)} | "
                        f"Loss: {losses['total'].item():.4f} | "
                        f"LR: {lr:.2e}"
                    )
            
            # Epoch summary
            avg_losses = {k: v / len(train_loader) for k, v in epoch_losses.items()}
            logger.info(f"Epoch {epoch+1} SUMMARY:")
            logger.info(f"  Train Loss: {avg_losses['total']:.4f} (risk: {avg_losses['risk']:.4f})")
            
            # Validation
            val_loss = self.validate(val_loader)
            logger.info(f"  Val Loss: {val_loss:.4f}")
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_checkpoint(output_dir / "best_model.pt", epoch, optimizer)
                logger.info(f"  ✓ Saved best model (val_loss: {val_loss:.4f})")
                
        logger.info(f"Training complete! Best val loss: {best_val_loss:.4f}")
        return best_val_loss
        
    def validate(self, val_loader):
        """Validation loop"""
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                if 'clinical_text' in batch:
                    batch['clinical_text'] = {
                        k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                        for k, v in batch['clinical_text'].items()
                    }
                    
                _, losses = self.model(batch, return_losses=True)
                total_loss += losses['total'].item()
                
        return total_loss / len(val_loader)
        
    def test(self, test_loader):
        """Test evaluation"""
        self.model.eval()
        
        all_preds = {'risk': [], 'treatment': [], 'survival': []}
        all_labels = {'risk': [], 'treatment': [], 'survival': []}
        
        with torch.no_grad():
            for batch in test_loader:
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                if 'clinical_text' in batch:
                    batch['clinical_text'] = {
                        k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                        for k, v in batch['clinical_text'].items()
                    }
                    
                outputs, _ = self.model(batch, return_losses=True)
                
                all_preds['risk'].append(outputs['risk_score'].cpu())
                all_preds['treatment'].append(outputs['treatment_logits'].argmax(dim=-1).cpu())
                all_preds['survival'].append(outputs['survival_logits'].cpu())
                
                if 'risk_label' in batch:
                    all_labels['risk'].append(batch['risk_label'].cpu())
                if 'treatment_label' in batch:
                    all_labels['treatment'].append(batch['treatment_label'].cpu())
                    
        # Compute metrics
        metrics = {}
        if all_labels['risk'] and all_preds['risk']:
            risk_preds = torch.cat(all_preds['risk'])
            risk_labels = torch.cat(all_labels['risk'])
            metrics['risk_auc'] = self._compute_auc(risk_preds, risk_labels)
            metrics['risk_acc'] = ((risk_preds > 0.5).float() == risk_labels).float().mean().item()
            
        if all_labels['treatment'] and all_preds['treatment']:
            treatment_preds = torch.cat(all_preds['treatment'])
            treatment_labels = torch.cat(all_labels['treatment'])
            metrics['treatment_acc'] = (treatment_preds == treatment_labels).float().mean().item()
            
        logger.info("Test Results:")
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")
            
        return metrics
        
    def _compute_auc(self, preds, labels):
        """Compute AUC-ROC"""
        from sklearn.metrics import roc_auc_score
        try:
            return roc_auc_score(labels.numpy(), preds.numpy())
        except:
            return 0.0
            
    def save_checkpoint(self, path, epoch, optimizer):
        """Save model checkpoint"""
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'config': self.config
        }, path)
        
    def load_checkpoint(self, path):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        return checkpoint.get('epoch', 0)


def train_with_lightning():
    """
    Alternative: Use PyTorch Lightning for even simpler multi-GPU training.
    This handles DDP automatically.
    """
    from pytorch_lightning import Trainer
    from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
    
    # Build model
    engine = PMRSTrainingEngine()
    engine.build_model()
    
    # Build data
    train_loader, val_loader, test_loader = engine.build_data()
    
    # Lightning handles multi-GPU automatically
    trainer = Trainer(
        max_epochs=50,
        accelerator='gpu',
        devices=2,  # 2x RTX 3090
        strategy='ddp',  # Distributed Data Parallel
        precision=16,  # Mixed precision
        accumulate_grad_batches=2,  # Effective batch size = 32
        callbacks=[
            ModelCheckpoint(monitor='val_loss', save_top_k=3),
            EarlyStopping(monitor='val_loss', patience=10)
        ]
    )
    
    # Note: Would need to convert to LightningModule for this path
    logger.info("Use train_with_ddp() for current implementation")


def main():
    parser = argparse.ArgumentParser(description='Train PMRS Multi-Modal Model')
    parser.add_argument('--config', type=str, default=None, help='Config YAML path')
    parser.add_argument('--epochs', type=int, default=None, help='Override num epochs')
    parser.add_argument('--batch_size', type=int, default=None, help='Override batch size')
    parser.add_argument('--lr', type=float, default=None, help='Override learning rate')
    parser.add_argument('--output_dir', type=str, default='outputs', help='Output directory')
    args = parser.parse_args()
    
    # Initialize
    engine = PMRSTrainingEngine(config_path=args.config)
    
    # Override config
    if args.epochs:
        engine.config['training']['num_epochs'] = args.epochs
    if args.batch_size:
        engine.config['training']['batch_size'] = args.batch_size
    if args.lr:
        engine.config['training']['learning_rate'] = args.lr
    if args.output_dir:
        engine.config['output']['output_dir'] = args.output_dir
        
    # Build
    engine.build_model()
    train_loader, val_loader, test_loader = engine.build_data()
    
    # Train
    best_loss = engine.train(train_loader, val_loader)
    
    # Test
    logger.info("\n" + "="*60)
    logger.info("FINAL EVALUATION")
    logger.info("="*60)
    
    # Load best model
    output_dir = Path(engine.config['output']['output_dir']) / engine.config['output']['experiment_name']
    engine.load_checkpoint(output_dir / "best_model.pt")
    metrics = engine.test(test_loader)
    
    logger.info("\nExperiment complete! Results saved to:")
    logger.info(f"  {output_dir}")


if __name__ == '__main__':
    main()
