from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Sequence

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion[K: Hashable](
    rankings: Sequence[Sequence[K]], k: int = DEFAULT_RRF_K, weights: Sequence[float] | None = None
) -> dict[K, float]:
    """Fusión por rango recíproco (Cormack, Clarke y Büttcher, 2009).

    Se eligió frente a una combinación ponderada de puntajes porque coseno y
    BM25 viven en escalas incomparables —BM25 ni siquiera está acotado—, y
    calibrarlas exigiría un conjunto etiquetado grande que este proyecto no
    tiene. RRF solo usa posiciones, no tiene parámetros que sobreajustar (k=60
    es el valor del artículo original) y es robusta cuando uno de los dos
    sistemas falla por completo en una consulta.

    `weights` permite que cada lista vote con distinto peso (RRF ponderada).
    """
    weights = weights or [1.0] * len(rankings)
    fused: dict[K, float] = defaultdict(float)
    for ranking, weight in zip(rankings, weights, strict=True):
        for rank, key in enumerate(ranking, start=1):
            fused[key] += weight / (k + rank)
    return dict(fused)


def rank_bonus(k: int = DEFAULT_RRF_K, rank: int = 1) -> float:
    """Lo que aportaría aparecer en posición `rank` de una lista adicional.

    Expresar las señales estructurales (el artículo citado, la sección pedida)
    en la misma unidad que RRF evita inventar pesos: una coincidencia exacta de
    artículo «vale» lo mismo que un tercer recuperador que la pusiera primera.
    """
    return 1.0 / (k + rank)
