"""Parse unit strings into SI scale factors and dimension vectors.

Dimensions are counted in five base quantities: mass M, length L, time T,
temperature Θ and amount of substance N. A unit string such as "MPa√m" becomes
scale 1e6 (to SI) and dimensions M¹ L^-½ T^-2.

Only the units that occur in SCC work are known; anything else raises
UnitError so the app can ask the user instead of guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

BASE = ("M", "L", "T", "Θ", "N")
DIMLESS = (0.0, 0.0, 0.0, 0.0, 0.0)


def _d(M=0, L=0, T=0, Th=0, N=0):
    return (float(M), float(L), float(T), float(Th), float(N))


# name -> (scale to SI, dimensions)
_UNITS = {
    "m": (1.0, _d(L=1)), "g": (1e-3, _d(M=1)), "s": (1.0, _d(T=1)),
    "min": (60.0, _d(T=1)), "h": (3600.0, _d(T=1)), "K": (1.0, _d(Th=1)),
    "mol": (1.0, _d(N=1)), "Pa": (1.0, _d(M=1, L=-1, T=-2)), "J": (1.0, _d(M=1, L=2, T=-2)),
    "N": (1.0, _d(M=1, L=1, T=-2)), "W": (1.0, _d(M=1, L=2, T=-3)),
    "L": (1e-3, _d(L=3)), "l": (1e-3, _d(L=3)), "cc": (1e-6, _d(L=3)),
    "bar": (1e5, _d(M=1, L=-1, T=-2)), "psi": (6894.76, _d(M=1, L=-1, T=-2)),
    "ksi": (6.89476e6, _d(M=1, L=-1, T=-2)), "in": (0.0254, _d(L=1)),
    "inch": (0.0254, _d(L=1)),
    "ppm": (1e-6, DIMLESS), "ppb": (1e-9, DIMLESS), "%": (0.01, DIMLESS),
}
_PREFIXES = {"G": 1e9, "M": 1e6, "k": 1e3, "c": 1e-2, "m": 1e-3,
             "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "n": 1e-9}
_PREFIXABLE = {"m", "g", "s", "Pa", "J", "N", "W", "L", "l", "mol"}
_CELSIUS = {"°C", "degC", "℃", "C°"}
_SUPERSCRIPT = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")


class UnitError(ValueError):
    pass


@dataclass(frozen=True)
class Unit:
    scale: float                  # multiply a raw value by this ...
    dims: tuple                   # ... and it is in SI with these dimensions
    offset: float = 0.0           # ... after adding this (only °C -> K)

    @property
    def dimensionless(self) -> bool:
        return all(abs(e) < 1e-9 for e in self.dims)


def parse_unit(text: str | None) -> Unit:
    """Parse a unit string. Empty / '-' / '1' mean dimensionless."""
    s = (text or "").strip()
    if s in ("", "-", "1"):
        return Unit(1.0, DIMLESS)
    if s in _CELSIUS:
        return Unit(1.0, _d(Th=1), offset=273.15)
    s = s.replace("·", "*").replace("×", "*").replace("°", "")
    s = s.replace("√", "*√")
    s = re.sub(r"√\(([^()]*)\)", r"(\1)^0.5", s)
    s = re.sub(r"√([A-Za-zµμ]+)", r"\1^0.5", s)
    s = re.sub(r"[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+", lambda m: "^" + m.group(0).translate(_SUPERSCRIPT), s)
    s = re.sub(r"^\s*\*", "", s)
    s = re.sub(r"\(\s*\*", "(", s)
    tokens = _tokenize(s)
    p = _Parser(tokens, text)
    scale, dims = p.expr()
    if p.i != len(tokens):
        raise UnitError(f"Cannot read unit '{text}'")
    return Unit(scale, tuple(float(x) for x in dims))


_TOKEN_RE = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][-+]?\d+)?)|([A-Za-zµμ%]+)|([\^*/()\-]))")


def _tokenize(s: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    s = s.rstrip()
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            raise UnitError(f"Unexpected character in unit: '{s[pos:]}'")
        num, ident, op = m.groups()
        out.append(("num", num) if num else ("id", ident) if ident else ("op", op))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, tokens, text):
        self.t, self.i, self.text = tokens, 0, text

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expr(self):
        scale, dims = self.term()
        while True:
            kind, val = self.peek()
            if val == "*":
                self.take()
                s2, d2 = self.term()
                scale, dims = scale * s2, dims + d2
            elif val == "/":
                self.take()
                s2, d2 = self.term()
                scale, dims = scale / s2, dims - d2
            elif kind in ("id", "num") or val == "(":  # implicit multiplication
                s2, d2 = self.term()
                scale, dims = scale * s2, dims + d2
            else:
                return scale, dims

    def term(self):
        scale, dims = self.factor()
        if self.peek()[1] == "^":
            self.take()
            e = self.exponent()
            scale, dims = scale ** e, dims * e
        return scale, dims

    def exponent(self) -> float:
        kind, val = self.take()
        sign = 1.0
        if val == "-":
            sign = -1.0
            kind, val = self.take()
        if kind == "num":
            return sign * float(val)
        if val == "(":
            num = self.take()
            if num[1] == "-":
                sign, num = -sign, self.take()
            if num[0] != "num":
                raise UnitError(f"Bad exponent in '{self.text}'")
            value = float(num[1])
            if self.peek()[1] == "/":
                self.take()
                value /= float(self.take()[1])
            if self.take()[1] != ")":
                raise UnitError(f"Bad exponent in '{self.text}'")
            return sign * value
        raise UnitError(f"Bad exponent in '{self.text}'")

    def factor(self):
        kind, val = self.take()
        if kind == "num":
            return float(val), np.zeros(5)
        if val == "(":
            scale, dims = self.expr()
            if self.take()[1] != ")":
                raise UnitError(f"Missing ')' in '{self.text}'")
            return scale, dims
        if kind == "id":
            return _lookup(val, self.text)
        raise UnitError(f"Cannot read unit '{self.text}'")


def _lookup(name: str, text: str):
    if name in _UNITS:
        s, d = _UNITS[name]
        return s, np.array(d)
    if len(name) > 1 and name[0] in _PREFIXES and name[1:] in _PREFIXABLE:
        s, d = _UNITS[name[1:]]
        return _PREFIXES[name[0]] * s, np.array(d)
    raise UnitError(f"Unknown unit '{name}' in '{text}'")


def format_dims(dims) -> str:
    parts = []
    for b, e in zip(BASE, dims):
        if abs(e) < 1e-9:
            continue
        f = Fraction(e).limit_denominator(12)
        parts.append(b if f == 1 else f"{b}^{f}")
    return " ".join(parts) if parts else "dimensionless"


def same_dims(a, b) -> bool:
    return all(abs(x - y) < 1e-9 for x, y in zip(a, b))
