"""
TCGA Data Loader: Download and process TCGA data for multi-modal learning
Supports: Gene expression (RNA-seq), Clinical data, Slide images (TCGA-WIKI)
"""
import os
import json
import torch
import torch.nn.functional as F
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class TCGADataModule:
    """
    Data module for TCGA multi-modal cancer data.
    
    Manages:
    - RNA-seq gene expression (HT-Counts / FPKM)
    - Clinical metadata (survival, stage, treatments)
    - Pathology slide metadata (for WSI tiles)
    """
    
    def __init__(
        self,
        data_dir: str = "data/tcga",
        batch_size: int = 32,
        num_workers: int = 4,
        n_genes: int = 20000,
        n_pathways: int = 50,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ):
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.n_genes = n_genes
        self.n_pathways = n_pathways
        
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        
        # Data paths
        self.gene_expr_path = self.data_dir / "gene_expression"
        self.clinical_path = self.data_dir / "clinical"
        self.slide_path = self.data_dir / "slides"
        
    def download_tcga_data(self, cancer_types: List[str] = None):
        """
        Download TCGA data using GDC API.
        
        Args:
            cancer_types: list of TCGA cancer codes (e.g., ['BRCA', 'LUAD', 'COAD'])
                         If None, downloads all available.
        """
        print("=" * 60)
        print("TCGA Data Downloader")
        print("=" * 60)
        
        # TCGA cancer type codes
        all_cancers = [
            'BRCA', 'LUAD', 'COAD', 'READ', 'THCA', 'PRAD', 'SKCM',
            'LUSC', 'STAD', 'BLCA', 'KIRP', 'LIHC', 'CESC', 'OV',
            'PAAD', 'SARC', 'LAML', 'KICH', 'KIRC', 'ESCA', 'HNSC',
            'TGCT', 'THYM', 'REACT', 'SKCM', 'MESO', 'UVM', 'ACC',
            'PCPG', 'DLBC', ' UCS', 'CHOL'
        ]
        
        cancer_types = cancer_types or all_cancers
        print(f"Target cancer types: {len(cancer_types)}")
        
        # Create manifest for GDC download
        manifest = self._create_gdc_manifest(cancer_types)
        
        # Save manifest
        manifest_path = self.data_dir / "gdc_manifest.txt"
        manifest.to_csv(manifest_path, sep='\t', index=False)
        
        print(f"Manifest saved to: {manifest_path}")
        print("To download, use: gdc-client download -m gdc_manifest.txt -d data/tcga")
        print("\nOr use the TCGA data portal: https://portal.gdc.cancer.gov/")
        
        return manifest
        
    def _create_gdc_manifest(self, cancer_types: List[str]) -> pd.DataFrame:
        """Create a manifest DataFrame for GDC download"""
        # This would normally query the GDC API
        # For now, return template
        manifest_data = []
        for cancer in cancer_types:
            manifest_data.append({
                'id': f'placeholder_{cancer}',
                'project': f'TCGA-{cancer}',
                'data_type': 'Gene Expression Quantification',
                'file_name': f'{cancer}_expression.tsv'
            })
        return pd.DataFrame(manifest_data)
        
    def load_gene_expression(self, cancer_type: str = None) -> pd.DataFrame:
        """
        Load gene expression data.
        
        Returns:
            DataFrame with samples as rows, genes as columns
        """
        if cancer_type:
            file_path = self.gene_expr_path / f"{cancer_type}_expression.tsv"
        else:
            # Load all expression files and merge
            files = list(self.gene_expr_path.glob("*_expression.tsv"))
            dfs = []
            for f in files:
                df = pd.read_csv(f, sep='\t', index_col=0)
                dfs.append(df)
            return pd.concat(dfs, axis=0)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Expression file not found: {file_path}")
            
        return pd.read_csv(file_path, sep='\t', index_col=0)
        
    def load_clinical_data(self, cancer_type: str = None) -> pd.DataFrame:
        """Load clinical metadata"""
        if cancer_type:
            file_path = self.clinical_path / f"{cancer_type}_clinical.tsv"
        else:
            file_path = self.clinical_path / "all_clinical.tsv"
            
        if not file_path.exists():
            raise FileNotFoundError(f"Clinical file not found: {file_path}")
            
        return pd.read_csv(file_path, sep='\t', index_col=0)
        
    def prepare_data(self, use_synthetic: bool = True):
        """
        Prepare train/val/test splits.
        
        Args:
            use_synthetic: if True, generate synthetic data for development
        """
        if use_synthetic:
            print("Generating synthetic TCGA-like data for development...")
            return self._generate_synthetic_data()
        
        # Load real data
        gene_df = self.load_gene_expression()
        clinical_df = self.load_clinical_data()
        
        # Merge on sample ID
        merged = gene_df.merge(clinical_df, left_index=True, right_index=True, how='inner')
        
        # Create splits
        n_samples = len(merged)
        indices = np.random.permutation(n_samples)
        
        n_train = int(n_samples * self.train_ratio)
        n_val = int(n_samples * self.val_ratio)
        
        train_idx = indices[:n_train]
        val_idx = indices[n_train:n_train + n_val]
        test_idx = indices[n_train + n_val:]
        
        return {
            'train': merged.iloc[train_idx],
            'val': merged.iloc[val_idx],
            'test': merged.iloc[test_idx]
        }
        
    def _generate_synthetic_data(
        self,
        n_samples: int = 1000,
        n_genes: int = 20000,
        n_pathways: int = 50,
        cancer_types: List[str] = None
    ):
        """
        Generate synthetic TCGA-like data for development/testing.
        """
        cancer_types = cancer_types or ['BRCA', 'LUAD', 'COAD', 'THCA', 'PRAD']
        n_cancers = len(cancer_types)
        
        np.random.seed(42)
        torch.manual_seed(42)
        
        samples = []
        
        for i in range(n_samples):
            cancer = cancer_types[i % n_cancers]
            
            # Sample characteristics vary by cancer type
            base_risk = hash(cancer) % 100 / 100.0
            
            sample = {
                'sample_id': f'TCGA-{cancer}-{i:04d}',
                'cancer_type': cancer,
                # Gene expression: log-normalized counts
                'gene_expression': np.random.randn(n_genes).astype(np.float32),
                # Pathway activity
                'pathway_activity': np.random.rand(n_pathways).astype(np.float32),
                # Survival (days)
                'survival_time': np.random.randint(100, 2000),
                # Event (1=death, 0=censored)
                'survival_event': np.random.randint(0, 2),
                # Risk label (0=low, 1=high)
                'risk_label': int(base_risk + np.random.randn() * 0.2 > 0.5),
                # Treatment (0-9)
                'treatment_label': np.random.randint(0, 10),
                # Stage (I-IV)
                'stage': np.random.randint(1, 5),
                # Age
                'age': np.random.randint(30, 85),
                # Gender
                'gender': np.random.randint(0, 2),
            }
            samples.append(sample)
            
        # Create DataFrames
        records = []
        for s in samples:
            record = {k: v for k, v in s.items() if k not in ['gene_expression', 'pathway_activity']}
            records.append(record)
            
        meta_df = pd.DataFrame(records).set_index('sample_id')
        
        # Gene expression as separate array
        gene_expr = np.stack([s['gene_expression'] for s in samples]).astype(np.float32)
        pathway_act = np.stack([s['pathway_activity'] for s in samples]).astype(np.float32)
        
        # Split
        n = len(meta_df)
        perm = np.random.permutation(n)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)
        
        splits = {
            'train': slice(0, n_train),
            'val': slice(n_train, n_train + n_val),
            'test': slice(n_train + n_val, None)
        }
        
        datasets = {}
        for split_name, split_slice in splits.items():
            split_meta = meta_df.iloc[split_slice].copy()
            split_gene = gene_expr[split_slice]
            split_pathway = pathway_act[split_slice]
            
            datasets[split_name] = {
                'meta': split_meta,
                'gene_expression': split_gene,
                'pathway_activity': split_pathway,
                'n_samples': len(split_meta)
            }
            
        print(f"Synthetic data generated:")
        print(f"  Train: {datasets['train']['n_samples']} samples")
        print(f"  Val: {datasets['val']['n_samples']} samples")
        print(f"  Test: {datasets['test']['n_samples']} samples")
        
        return datasets


class TCGAMultiModalDataset(Dataset):
    """
    PyTorch Dataset for TCGA multi-modal data.
    Returns gene expression, optional pathology tiles, optional clinical text.
    """
    
    def __init__(
        self,
        meta_df: pd.DataFrame,
        gene_expression: np.ndarray,
        pathway_activity: np.ndarray,
        transform=None,
        mode: str = 'train'
    ):
        self.meta = meta_df.reset_index()
        self.gene_expression = gene_expression
        self.pathway_activity = pathway_activity
        self.transform = transform
        self.mode = mode
        
    def __len__(self):
        return len(self.meta)
    
    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        row = self.meta.iloc[idx]
        
        sample = {
            # Gene expression: (n_genes,)
            'gene_expression': torch.from_numpy(
                self.gene_expression[idx]
            ).float(),
            # Pathway activity: (n_pathways,)
            'pathway_activity': torch.from_numpy(
                self.pathway_activity[idx]
            ).float(),
            # Sample ID for tracking
            'sample_id': row['sample_id'],
            'cancer_type': row['cancer_type'],
        }
        
        # Labels (for training)
        if 'risk_label' in self.meta.columns:
            sample['risk_label'] = torch.tensor(row['risk_label'], dtype=torch.float32)
        if 'treatment_label' in self.meta.columns:
            sample['treatment_label'] = torch.tensor(row['treatment_label'], dtype=torch.long)
        if 'survival_time' in self.meta.columns:
            sample['survival_time'] = torch.tensor(row['survival_time'], dtype=torch.float32)
        if 'survival_event' in self.meta.columns:
            sample['survival_event'] = torch.tensor(row['survival_event'], dtype=torch.float32)
            
        # Clinical text (synthetic for now)
        # In real setting, would load from preprocessed text data
        sample['clinical_text'] = {
            'input_ids': torch.randint(0, 30000, (128,)),
            'attention_mask': torch.ones(128, dtype=torch.long)
        }
        
        return sample


def tcga_collate_fn(batch: List[Dict]) -> Dict[str, torch.Tensor]:
    """
    Collate function for TCGA DataLoader.
    Handles variable-length clinical text.
    """
    collated = {}
    
    # Gene expression — already fixed size
    collated['gene_expression'] = torch.stack([b['gene_expression'] for b in batch])
    collated['pathway_activity'] = torch.stack([b['pathway_activity'] for b in batch])
    
    # Labels
    if 'risk_label' in batch[0]:
        collated['risk_label'] = torch.stack([b['risk_label'] for b in batch])
    if 'treatment_label' in batch[0]:
        collated['treatment_label'] = torch.stack([b['treatment_label'] for b in batch])
    if 'survival_time' in batch[0]:
        collated['survival_time'] = torch.stack([b['survival_time'] for b in batch])
    if 'survival_event' in batch[0]:
        collated['survival_event'] = torch.stack([b['survival_event'] for b in batch])
        
    # Clinical text (pad to max length in batch)
    max_len = max(b['clinical_text']['input_ids'].size(0) for b in batch)
    
    input_ids = []
    attention_masks = []
    
    for b in batch:
        ids = b['clinical_text']['input_ids']
        mask = b['clinical_text']['attention_mask']
        
        # Pad if needed
        if ids.size(0) < max_len:
            pad_len = max_len - ids.size(0)
            ids = F.pad(ids, (0, pad_len), value=0)
            mask = F.pad(mask, (0, pad_len), value=0)
            
        input_ids.append(ids)
        attention_masks.append(mask)
        
    collated['clinical_text'] = {
        'input_ids': torch.stack(input_ids),
        'attention_mask': torch.stack(attention_masks)
    }
    
    # Metadata
    collated['sample_ids'] = [b['sample_id'] for b in batch]
    collated['cancer_types'] = [b['cancer_type'] for b in batch]
    
    return collated
