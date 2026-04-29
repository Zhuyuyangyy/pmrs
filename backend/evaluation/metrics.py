"""
Evaluation Metrics for PMRS
Comprehensive metrics for multi-task cancer prediction
"""
import numpy as np
import torch
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_curve, precision_recall_curve,
    average_precision_score, cohen_kappa_score
)
from sklearn.calibration import calibration_curve


class PMRSEvaluator:
    """
    Comprehensive evaluator for PMRS multi-task outputs.
    
    Tasks:
    1. Risk Prediction (binary/multi-class)
    2. Treatment Recommendation (multi-class)  
    3. Survival Prediction (time-to-event)
    """
    
    def __init__(self):
        self.results = {}
        
    def evaluate_all(self, predictions, labels, survival_times=None, survival_events=None):
        """
        Run all evaluation metrics.
        
        Args:
            predictions: dict with keys 'risk_score', 'treatment_logits', 'survival_logits'
            labels: dict with 'risk_label', 'treatment_label'
            survival_times: (n_samples,) event times
            survival_events: (n_samples,) event indicators (1=death, 0=censored)
        """
        results = {}
        
        # 1. Risk Prediction Metrics
        if 'risk_score' in predictions and 'risk_label' in labels:
            results['risk'] = self._evaluate_risk(
                predictions['risk_score'],
                labels['risk_label']
            )
            
        # 2. Treatment Recommendation Metrics
        if 'treatment_logits' in predictions and 'treatment_label' in labels:
            results['treatment'] = self._evaluate_treatment(
                predictions['treatment_logits'],
                labels['treatment_label']
            )
            
        # 3. Survival Prediction Metrics
        if 'survival_logits' in predictions and survival_times is not None:
            results['survival'] = self._evaluate_survival(
                predictions['survival_logits'],
                survival_times,
                survival_events
            )
            
        self.results = results
        return results
        
    def _evaluate_risk(self, risk_probs, risk_labels):
        """
        Evaluate risk prediction (binary classification).
        
        Returns AUC-ROC, AUC-PR, Accuracy, Sensitivity, Specificity, etc.
        """
        # Convert to numpy
        if torch.is_tensor(risk_probs):
            risk_probs = risk_probs.cpu().numpy()
        if torch.is_tensor(risk_labels):
            risk_labels = risk_labels.cpu().numpy()
            
        # Binary predictions (threshold = 0.5)
        risk_preds_binary = (risk_probs > 0.5).astype(int)
        
        metrics = {
            # Overall metrics
            'auc_roc': roc_auc_score(risk_labels, risk_probs),
            'auc_pr': average_precision_score(risk_labels, risk_probs),
            'accuracy': accuracy_score(risk_labels, risk_preds_binary),
            
            # Class-specific
            'precision': precision_score(risk_labels, risk_preds_binary, zero_division=0),
            'recall': recall_score(risk_labels, risk_preds_binary, zero_division=0),
            'f1': f1_score(risk_labels, risk_preds_binary, zero_division=0),
            
            # Confusion matrix
            'confusion_matrix': confusion_matrix(risk_labels, risk_preds_binary).tolist(),
            'tn': int(confusion_matrix(risk_labels, risk_preds_binary)[0, 0]),
            'fp': int(confusion_matrix(risk_labels, risk_preds_binary)[0, 1]),
            'fn': int(confusion_matrix(risk_labels, risk_preds_binary)[1, 0]),
            'tp': int(confusion_matrix(risk_labels, risk_preds_binary)[1, 1]),
        }
        
        # Sensitivity (Recall for positive class)
        metrics['sensitivity'] = metrics['recall']
        
        # Specificity
        tn, fp, fn, tp = metrics['tn'], metrics['fp'], metrics['fn'], metrics['tp']
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        # Cohen's Kappa
        metrics['kappa'] = cohen_kappa_score(risk_labels, risk_preds_binary)
        
        # Calibration error (ECE)
        metrics['ece'] = self._expected_calibration_error(risk_probs, risk_labels, n_bins=10)
        
        # ROC curve data (for plotting)
        fpr, tpr, _ = roc_curve(risk_labels, risk_probs)
        metrics['roc_curve'] = {'fpr': fpr.tolist(), 'tpr': tpr.tolist()}
        
        # PR curve data
        precision_curve, recall_curve, _ = precision_recall_curve(risk_labels, risk_probs)
        metrics['pr_curve'] = {
            'precision': precision_curve.tolist(),
            'recall': recall_curve.tolist()
        }
        
        return metrics
        
    def _evaluate_treatment(self, treatment_logits, treatment_labels):
        """
        Evaluate treatment recommendation (multi-class).
        """
        if torch.is_tensor(treatment_logits):
            treatment_logits = treatment_logits.cpu().numpy()
        if torch.is_tensor(treatment_labels):
            treatment_labels = treatment_labels.cpu().numpy()
            
        treatment_preds = np.argmax(treatment_logits, axis=-1)
        n_classes = treatment_logits.shape[-1]
        
        metrics = {
            'accuracy': accuracy_score(treatment_labels, treatment_preds),
            'top3_accuracy': self._top_k_accuracy(treatment_logits, treatment_labels, k=3),
            'top5_accuracy': self._top_k_accuracy(treatment_logits, treatment_labels, k=5),
            'per_class_precision': precision_score(treatment_labels, treatment_preds, average=None, zero_division=0).tolist(),
            'per_class_recall': recall_score(treatment_labels, treatment_preds, average=None, zero_division=0).tolist(),
            'per_class_f1': f1_score(treatment_labels, treatment_preds, average=None, zero_division=0).tolist(),
            'confusion_matrix': confusion_matrix(treatment_labels, treatment_preds, labels=range(n_classes)).tolist(),
            'n_classes': n_classes
        }
        
        # Macro and weighted averages
        metrics['macro_precision'] = precision_score(treatment_labels, treatment_preds, average='macro', zero_division=0)
        metrics['macro_recall'] = recall_score(treatment_labels, treatment_preds, average='macro', zero_division=0)
        metrics['macro_f1'] = f1_score(treatment_labels, treatment_preds, average='macro', zero_division=0)
        
        metrics['weighted_precision'] = precision_score(treatment_labels, treatment_preds, average='weighted', zero_division=0)
        metrics['weighted_recall'] = recall_score(treatment_labels, treatment_preds, average='weighted', zero_division=0)
        metrics['weighted_f1'] = f1_score(treatment_labels, treatment_preds, average='weighted', zero_division=0)
        
        return metrics
        
    def _evaluate_survival(self, survival_logits, survival_times, survival_events):
        """
        Evaluate survival prediction (time-to-event).
        
        Metrics: C-index (concordance index), Brier score
        """
        if torch.is_tensor(survival_logits):
            survival_logits = survival_logits.cpu().numpy()
        if torch.is_tensor(survival_times):
            survival_times = survival_times.cpu().numpy()
        if torch.is_tensor(survival_events):
            survival_events = survival_events.cpu().numpy()
            
        # Predicted risk scores (higher = more risk)
        risk_scores = np.sum(survival_logits, axis=-1)  # Sum hazard over time
        
        # C-index (concordance index)
        c_index = self._concordance_index(survival_times, -risk_scores, survival_events)
        
        # Brier score (at specific time points)
        brier_scores = {}
        for t in [365, 730, 1095]:  # 1, 2, 3 years
            brier_scores[f'brier_{t}d'] = self._brier_score(risk_scores, survival_times, survival_events, t)
            
        metrics = {
            'c_index': c_index,
            'brier_scores': brier_scores,
            'mean_brier': np.mean(list(brier_scores.values()))
        }
        
        return metrics
        
    def _top_k_accuracy(self, logits, labels, k=3):
        """Top-K accuracy for multi-class"""
        top_k_preds = np.argsort(logits, axis=-1)[:, -k:]
        correct = np.any(top_k_preds == labels.reshape(-1, 1), axis=-1)
        return np.mean(correct)
        
    def _expected_calibration_error(self, probs, labels, n_bins=10):
        """Compute ECE (Expected Calibration Error)"""
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        
        for i in range(n_bins):
            mask = (probs >= bin_edges[i]) & (probs < bin_edges[i + 1])
            if mask.sum() > 0:
                bin_confidence = probs[mask].mean()
                bin_accuracy = labels[mask].mean()
                ece += mask.sum() * abs(bin_confidence - bin_accuracy)
                
        return ece / len(probs)
        
    def _concordance_index(self, times, risks, events):
        """
        Compute concordance index (C-index).
        Measures how well predictions order the survival times.
        """
        n = len(times)
        concordant = 0
        discordant = 0
        tied = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                # Only consider comparable pairs (one event, or both censored with different times)
                if events[i] == 1 or events[j] == 1:
                    # Event order
                    if events[i] == 1 and times[i] < times[j]:
                        # i had event, j is alive beyond i
                        if risks[i] > risks[j]:
                            concordant += 1
                        elif risks[i] == risks[j]:
                            tied += 1
                        else:
                            discordant += 1
                    elif events[j] == 1 and times[j] < times[i]:
                        # j had event, i is alive beyond j
                        if risks[j] > risks[i]:
                            concordant += 1
                        elif risks[j] == risks[i]:
                            tied += 1
                        else:
                            discordant += 1
                            
        total = concordant + discordant + tied
        if total == 0:
            return 0.0
        return (concordant + 0.5 * tied) / total
        
    def _brier_score(self, risks, times, events, t):
        """
        Compute Brier score at time t.
        Measures prediction error at specific time.
        """
        # Kaplan-Meier for censoring weights
        risk_set = times > t
        n_risk = risk_set.sum()
        if n_risk == 0:
            return 0.0
            
        # Predicted risk at time t (simplified)
        pred_risk = 1 - np.exp(-risks * t / 1000)  # Simplified
        
        # Observed outcomes
        observed = (times <= t) & (events == 1)
        
        # Weighted by inverse probability of censoring
        brier = (pred_risk ** 2 * observed.astype(float)).mean()
        
        return brier
        
    def print_report(self):
        """Print formatted evaluation report"""
        if not self.results:
            print("No results to report. Run evaluate_all() first.")
            return
            
        print("=" * 70)
        print("PMRS EVALUATION REPORT")
        print("=" * 70)
        
        if 'risk' in self.results:
            r = self.results['risk']
            print("\n📊 RISK PREDICTION (Binary Classification)")
            print("-" * 40)
            print(f"  AUC-ROC:        {r['auc_roc']:.4f}")
            print(f"  AUC-PR:         {r['auc_pr']:.4f}")
            print(f"  Accuracy:       {r['accuracy']:.4f}")
            print(f"  Sensitivity:     {r['sensitivity']:.4f}")
            print(f"  Specificity:    {r['specificity']:.4f}")
            print(f"  F1 Score:       {r['f1']:.4f}")
            print(f"  Cohen's Kappa:  {r['kappa']:.4f}")
            print(f"  ECE:            {r['ece']:.4f}")
            print(f"  Confusion Matrix:")
            print(f"    TN={r['tn']:4d}  FP={r['fp']:4d}")
            print(f"    FN={r['fn']:4d}  TP={r['tp']:4d}")
            
        if 'treatment' in self.results:
            t = self.results['treatment']
            print(f"\n💊 TREATMENT RECOMMENDATION (Multi-class, {t['n_classes']} classes)")
            print("-" * 40)
            print(f"  Accuracy:       {t['accuracy']:.4f}")
            print(f"  Top-3 Acc:      {t['top3_accuracy']:.4f}")
            print(f"  Top-5 Acc:      {t['top5_accuracy']:.4f}")
            print(f"  Macro F1:       {t['macro_f1']:.4f}")
            print(f"  Weighted F1:   {t['weighted_f1']:.4f}")
            
        if 'survival' in self.results:
            s = self.results['survival']
            print(f"\n⏱️ SURVIVAL PREDICTION (Time-to-Event)")
            print("-" * 40)
            print(f"  C-index:        {s['c_index']:.4f}")
            print(f"  Mean Brier:    {s['mean_brier']:.4f}")
            for k, v in s['brier_scores'].items():
                print(f"  {k}:  {v:.4f}")
                
        print("\n" + "=" * 70)
        
    def save_report(self, path):
        """Save evaluation report to JSON"""
        import json
        
        # Convert numpy types to native Python
        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj
                
        with open(path, 'w') as f:
            json.dump(convert(self.results), f, indent=2)
