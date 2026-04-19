"""Fertility model for demography: Hadwiger ASFR modulated by Becker (1991)
economic signals, bounded by a Malthusian soft ceiling.

Sources:
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion.
  Skandinavisk Aktuarietidskrift 23, 101-113. Canonical normalization per
  Chandola, Coleman & Hiorns (1999) Population Studies 53(3) and
  Schmertmann (2003) Demographic Research 9.
- Becker, G.S. (1991). A Treatise on the Family. Harvard University Press.
- Malthus-Ricardo preventive check formalization inspired by
  Ashraf & Galor (2011) AER 101(5).
"""
from __future__ import annotations

import math
from typing import Mapping


def hadwiger_asfr(age: float, params: Mapping[str, float]) -> float:
    """Age-specific fertility rate at age a using the canonical Hadwiger form.

    f(a) = (H * T / (R * sqrt(pi))) * (R / a) ** 1.5 *
           exp(-T ** 2 * (R / a + a / R - 2))

    where H is the target total fertility rate (integral of f over fertile ages),
    R is the Hadwiger shape parameter related to peak fertility age, and T
    controls the spread of the distribution.

    Returns 0.0 for ages outside the biologically fertile window [12, 50] and
    for non-positive ages.
    """
    if age <= 0 or age < 12 or age > 50:
        return 0.0
    H = float(params["H"])
    R = float(params["R"])
    T = float(params["T"])
    ratio = R / age
    coef = (H * T) / (R * math.sqrt(math.pi))
    shape = ratio ** 1.5
    tail = math.exp(-(T ** 2) * (ratio + age / R - 2.0))
    return coef * shape * tail
