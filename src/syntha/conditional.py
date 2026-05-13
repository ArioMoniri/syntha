"""Conditional sampling — generate synthetic episodes matching a filter.

Usage from the CLI:

    syntha generate \\
        --input data/raw/pristine_tolerant_episodes.csv \\
        --condition 'age > 60 & DM_Tum == 1' \\
        --n 1000 --output out/diabetic_seniors

Implementation: rejection sampling around the existing copula. Sample
`oversample_factor × n` rows from the fitted copula, evaluate the
pandas-style filter expression, keep the matches, repeat up to
``max_rounds`` until `n` matches are accumulated. Inefficient for very
rare conditions (e.g. P(condition) ≈ 0.01) but exact — no need to refit.

For rarer conditions, we could implement true conditional Gaussian
sampling (condition on a subset of variables, sample from the remaining
marginal of the multivariate normal), but that's a v0.7 task.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

import pandas as pd

from .generator.constraints import PhysiologicConstraints
from .generator.copula import GaussianCopulaGenerator


@dataclass
class ConditionalSamplingResult:
    rows: pd.DataFrame
    n_requested: int
    n_generated: int
    rounds: int
    rejection_rate: float


# Allowed AST node types in a condition expression. The walker rejects
# anything that could reach out (Attribute, Call, Subscript, Import) or
# bind new names (Lambda, comprehensions). Everything left over is just
# comparisons + boolean ops + arithmetic + literals + column references.
_ALLOWED_AST_NODES = {
    ast.Expression, ast.Compare, ast.BoolOp, ast.UnaryOp, ast.BinOp,
    ast.Name, ast.Constant, ast.Load,
    ast.And, ast.Or, ast.Not, ast.Invert,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv, ast.Pow,
    ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift,
    ast.USub, ast.UAdd,
    ast.Tuple, ast.List,
}


def _safe_eval_filter(df: pd.DataFrame, expression: str) -> pd.Series:
    """Apply a pandas-query-style filter on `df`, AST-validated.

    We parse the expression with ``ast.parse(mode="eval")`` and walk the
    tree rejecting any node not on the allowlist. This catches attribute
    access (``age.__class__``), function calls (``__import__('os')``),
    subscripts (``a[0]``), lambdas, comprehensions, named expressions
    (``:=``), starred expressions, and anything else that could escape
    the DataFrame namespace. Names are further restricted to actual
    DataFrame columns.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"invalid condition syntax: {e}") from e

    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_AST_NODES:
            raise ValueError(
                f"condition contains disallowed construct "
                f"{type(node).__name__!r}; only comparisons, boolean ops, "
                f"arithmetic, literals, and column-name references are allowed. "
                f"Got: {expression!r}"
            )
        if isinstance(node, ast.Name) and node.id not in df.columns:
            raise ValueError(
                f"condition references unknown name {node.id!r}; "
                f"available columns: {list(df.columns)[:8]}…"
            )
    mask = df.eval(expression, engine="python")
    if not isinstance(mask, pd.Series):
        raise ValueError(
            f"condition {expression!r} did not evaluate to a Series"
        )
    # Accept both numpy bool and pandas nullable boolean. The copula casts
    # some columns to Int64 (nullable) which propagates to boolean masks.
    if mask.dtype.name not in {"bool", "boolean"}:
        raise ValueError(
            f"condition {expression!r} did not evaluate to a boolean mask "
            f"(got dtype {mask.dtype.name})"
        )
    # Convert nullable boolean to plain numpy bool, treating NA as False so
    # downstream df[mask] indexing works without choking.
    return mask.fillna(False).astype(bool)


def sample_conditional(
    generator: GaussianCopulaGenerator,
    n: int,
    condition: str,
    *,
    oversample_factor: float = 5.0,
    max_rounds: int = 10,
    constraints: PhysiologicConstraints | None = None,
) -> ConditionalSamplingResult:
    """Rejection-sample n rows that satisfy ``condition``.

    Parameters
    ----------
    generator:
        A fitted GaussianCopulaGenerator.
    n:
        Target number of accepted rows.
    condition:
        A pandas df.eval-style expression in the model's column names.
        Example: ``"age > 60 & DM_Tum == 1 & bp_systolic >= 140"``
    oversample_factor:
        Initial multiplier — how many candidates to draw per accepted
        target. 5× is a reasonable default for moderately selective
        filters (P ≥ 0.05). Raise for rarer conditions.
    max_rounds:
        Safety cap. After this many rounds without filling the quota,
        the function returns what it has and reports the rejection rate.
    constraints:
        Optional PhysiologicConstraints to apply before the user filter.

    Returns
    -------
    ConditionalSamplingResult with the accepted rows, the round count,
    and the empirical rejection rate (so users can see how rare their
    condition is in this copula).
    """
    collected: list[pd.DataFrame] = []
    rounds = 0
    total_drawn = 0
    deficit = n

    while sum(len(d) for d in collected) < n and rounds < max_rounds:
        rounds += 1
        batch_size = max(1, int(deficit * oversample_factor))
        drawn = generator.sample(batch_size)
        total_drawn += len(drawn)

        if constraints is not None:
            kept, _ = constraints.apply(drawn)
        else:
            kept = drawn

        mask = _safe_eval_filter(kept, condition)
        matches = kept[mask].reset_index(drop=True)
        collected.append(matches)

        accumulated = sum(len(d) for d in collected)
        deficit = max(0, n - accumulated)
        if deficit > 0:
            # Update oversample_factor: if we got <50% of what we hoped for,
            # double the next batch to converge faster.
            empirical_rate = accumulated / total_drawn
            if empirical_rate > 0:
                oversample_factor = max(oversample_factor, 1.5 / empirical_rate)

    final = pd.concat(collected, ignore_index=True).head(n).reset_index(drop=True)
    rejection_rate = 1.0 - (len(final) / total_drawn) if total_drawn else 1.0
    return ConditionalSamplingResult(
        rows=final,
        n_requested=n,
        n_generated=len(final),
        rounds=rounds,
        rejection_rate=rejection_rate,
    )
