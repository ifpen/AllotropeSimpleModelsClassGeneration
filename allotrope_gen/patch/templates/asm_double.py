"""Floating-point type accepting the ASM ``"NaN"`` string (generated)."""

from __future__ import annotations

import math
from typing import Annotated, Union

from pydantic import BeforeValidator, PlainSerializer


def _parse(value: object) -> object:
    """Map the ASM ``"NaN"`` string to ``math.nan``; reject other strings."""
    if value == "NaN":
        return math.nan
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected a number or the ASM string 'NaN'")
    return value


def _serialize(value: float) -> Union[float, str]:
    """Write NaN back as the ASM ``"NaN"`` string."""
    return "NaN" if isinstance(value, float) and math.isnan(value) else value


#: ``float`` that reads and writes NaN as the ASM string ``"NaN"``.
AsmDouble = Annotated[
    float,
    BeforeValidator(_parse),
    PlainSerializer(_serialize, return_type=Union[float, str]),
]
