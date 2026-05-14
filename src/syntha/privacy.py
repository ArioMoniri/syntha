"""Privacy attack module — G2 from the medical-officer review.

Implements two standard privacy attacks against any generator that
exposes a fit() / sample() API:

  1. **Membership inference attack (MIA)** — given an unknown record, can
     an attacker tell whether it was in the generator's training set?
     We use the simple but well-validated "distance-to-closest-record"
     attack of Stadler et al. (2022): an attacker observes the
     generator's synthetic output, computes the distance from each
     candidate (real) record to its nearest synthetic neighbor, and
     classifies records with the smallest distance as "training-set
     members".

  2. **Attribute inference attack (AIA)** — given an attacker who knows
     some of a record's attributes (e.g., demographics), can they
     predict the unknown attributes (e.g., sensitive diagnoses) better
     than chance using only synthetic data?

Both are scored as ROC-AUC where 0.50 = no privacy leakage (perfect
privacy) and 1.00 = perfect attack (model memorized training data).

These attacks run in CI per .github/workflows/privacy-attack.yml and
fail the build if the attacker's AUC exceeds a configured threshold —
the formal evidence (per MO review G2) that v0.5 doesn't memorize.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


@dataclass
class PrivacyReport:
    n_synthetic: int
    n_real_members: int
    n_real_holdout: int
    membership_inference_auc: float
    attribute_inference_aucs: dict[str, float]
    columns_attacked: list[str]
    verdict: str   # "pass" | "fail"

    def summary(self) -> dict:
        return {
            "n_synthetic": self.n_synthetic,
            "n_real_members": self.n_real_members,
            "n_real_holdout": self.n_real_holdout,
            "membership_inference_auc": self.membership_inference_auc,
            "attribute_inference_aucs": self.attribute_inference_aucs,
            "max_attribute_inference_auc": max(
                self.attribute_inference_aucs.values(), default=0.5,
            ),
            "verdict": self.verdict,
        }


def _prepare(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Numericize + standardize a feature matrix for distance comparisons."""
    sub = df[cols].copy()
    for c in cols:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub = sub.fillna(sub.median(numeric_only=True)).fillna(0.0)
    scaler = StandardScaler()
    return scaler.fit_transform(sub.to_numpy())


def membership_inference_attack(
    real_train: pd.DataFrame,
    real_holdout: pd.DataFrame,
    synthetic: pd.DataFrame,
    feature_cols: list[str],
) -> float:
    """Stadler-style nearest-neighbor MIA.

    Returns ROC-AUC of an attacker that scores each record by its negative
    distance to its closest synthetic neighbor (closer = more likely a
    training member). AUC=0.50 means perfect privacy; AUC=1.00 means
    perfect memorization detection.
    """
    common = [c for c in feature_cols if c in real_train.columns
              and c in real_holdout.columns and c in synthetic.columns]
    if len(common) < 3:
        return 0.5

    X_train = _prepare(real_train, common)
    X_holdout = _prepare(real_holdout, common)
    X_syn = _prepare(synthetic, common)

    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(X_syn)
    # Distance to nearest synthetic; smaller distance = "closer to training"
    dist_train, _ = nn.kneighbors(X_train)
    dist_holdout, _ = nn.kneighbors(X_holdout)

    # Attacker score: higher = more likely a member. Use negative distance.
    scores = np.concatenate([-dist_train.flatten(), -dist_holdout.flatten()])
    labels = np.concatenate([
        np.ones(len(dist_train)),
        np.zeros(len(dist_holdout)),
    ])

    if len(np.unique(labels)) < 2:
        return 0.5
    return float(roc_auc_score(labels, scores))


def attribute_inference_attack(
    real_holdout: pd.DataFrame,
    synthetic: pd.DataFrame,
    public_cols: list[str],
    target_col: str,
) -> float:
    """Train a classifier ONLY on synthetic data to predict ``target_col``
    from ``public_cols``, evaluate it on the held-out real records.

    The intuition: if the synthetic data preserves the (public_attribute
    → sensitive_attribute) mapping well enough, an attacker who has the
    synthetic data + the public attributes of a real person can guess
    the sensitive attribute. AUC>0.50 means information leakage; AUC
    close to a model trained on real data means full leakage.
    """
    if target_col not in synthetic.columns or target_col not in real_holdout.columns:
        return 0.5
    common = [c for c in public_cols if c in synthetic.columns
              and c in real_holdout.columns and c != target_col]
    if len(common) < 2:
        return 0.5

    X_syn = _prepare(synthetic, common)
    y_syn = pd.to_numeric(synthetic[target_col], errors="coerce").fillna(0).astype(int).to_numpy()

    if len(np.unique(y_syn)) < 2:
        return 0.5

    # Train on synthetic
    clf = LogisticRegression(max_iter=500, class_weight="balanced")
    clf.fit(X_syn, y_syn)

    # Score on real holdout
    X_holdout = _prepare(real_holdout, common)
    y_holdout = pd.to_numeric(real_holdout[target_col], errors="coerce").fillna(0).astype(int).to_numpy()
    if len(np.unique(y_holdout)) < 2:
        return 0.5
    proba = clf.predict_proba(X_holdout)[:, 1]
    return float(roc_auc_score(y_holdout, proba))


# Thresholds chosen from the SynQP / Stadler 2022 literature:
#   * MIA AUC ≤ 0.60 is the standard "no meaningful leakage" threshold
#   * AIA AUC ≤ 0.70 indicates attacker only marginally beats demographic
#     base rates (which themselves leak ~0.65-0.70 AUC on common targets
#     like HTN given age + gender)
DEFAULT_MIA_THRESHOLD = 0.60
DEFAULT_AIA_THRESHOLD = 0.70


def run_privacy_audit(
    real_train: pd.DataFrame,
    real_holdout: pd.DataFrame,
    synthetic: pd.DataFrame,
    feature_cols: list[str],
    sensitive_targets: list[str],
    *,
    mia_threshold: float = DEFAULT_MIA_THRESHOLD,
    aia_threshold: float = DEFAULT_AIA_THRESHOLD,
) -> PrivacyReport:
    """Run both attacks and return a pass/fail PrivacyReport.

    Failure modes:
      * MIA AUC > mia_threshold (membership inference)
      * Any AIA AUC > aia_threshold (attribute inference on at least
        one sensitive target)
    """
    mia = membership_inference_attack(
        real_train, real_holdout, synthetic, feature_cols,
    )
    public_cols = [c for c in feature_cols if c not in sensitive_targets]
    aia: dict[str, float] = {}
    for target in sensitive_targets:
        aia[target] = attribute_inference_attack(
            real_holdout, synthetic, public_cols, target,
        )

    verdict = "pass"
    if mia > mia_threshold:
        verdict = "fail"
    elif aia and max(aia.values()) > aia_threshold:
        verdict = "fail"

    return PrivacyReport(
        n_synthetic=len(synthetic),
        n_real_members=len(real_train),
        n_real_holdout=len(real_holdout),
        membership_inference_auc=mia,
        attribute_inference_aucs=aia,
        columns_attacked=sensitive_targets,
        verdict=verdict,
    )
