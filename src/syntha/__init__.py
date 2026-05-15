"""syntha — synthetic patient record generator.

Top-level re-exports for ergonomics. Users can do:

    from syntha import GaussianCopulaGenerator, PipelineConfig, run

instead of having to know the submodule layout.
"""
__version__ = "0.5.6"

from .generator.copula import GaussianCopulaGenerator
from .pipeline import PipelineConfig, run

__all__ = ["GaussianCopulaGenerator", "PipelineConfig", "run", "__version__"]
