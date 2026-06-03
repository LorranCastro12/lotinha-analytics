"""Estratégias de predição para sorteios da Lotinha."""

from lotinha.analysis.strategies.base import BaseStrategy
from lotinha.analysis.strategies.core import (
    AtrasoStrategy,
    BancaAwareLGBMWrapper,
    FrequenciaStrategy,
    HybridMarkovWrapper,
    MarkovStrategy,
)
from lotinha.analysis.strategies.ensemble import EnsembleStrategy
from lotinha.analysis.strategies.lgbm import LightGBMStrategy

__all__ = [
    "AtrasoStrategy",
    "BancaAwareLGBMWrapper",
    "BaseStrategy",
    "EnsembleStrategy",
    "FrequenciaStrategy",
    "HybridMarkovWrapper",
    "LightGBMStrategy",
    "MarkovStrategy",
]
