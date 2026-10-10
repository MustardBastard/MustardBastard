"""Dimensional analysis: Buckingham π groups and dimension checks of formulas.

All π groups are evaluated in SI units, so a group really is a pure number
regardless of whether a column was recorded in mm/s, MPa√m or °C.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from .units import DIMLESS, Unit, UnitError, format_dims, same_dims

_DIMLESS_FUNCS = {"log", "ln", "log10", "exp", "sin", "cos", "tan"}


class DimensionError(ValueError):
    pass


# --------------------------------------------------------------------------- formula dimensions

def formula_dims(formula: str, units: dict[str, Unit]) -> tuple:
    """Dimensions of a formula's result, given the unit of every name in it.

    Bare numbers added to a quantity take that quantity's dimensions
    ("Temp + 273.15"); functions like exp() and log() need a dimensionless
    argument.
    """
    tree = ast.parse(formula, mode="eval")
    return _dims(tree.body, units)


def _dims(node, units):
    if isinstance(node, ast.Constant):
        return None  # a bare number: dimensionless, but adopts dims when added
    if isinstance(node, ast.Name):
        if node.id in ("pi", "e"):
            return None
        if node.id not in units:
            raise DimensionError(f"No unit known for '{node.id}'")
        return units[node.id].dims
    if isinstance(node, ast.UnaryOp):
        return _dims(node.operand, units)
    if isinstance(node, ast.BinOp):
        a, b = _dims(node.left, units), _dims(node.right, units)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if a is None or b is None:
                return a if b is None else b
            if not same_dims(a, b):
                raise DimensionError(
                    f"Adding {format_dims(a)} to {format_dims(b)} in '{ast.unparse(node)}'")
            return a
        a = a or DIMLESS
        b = b or DIMLESS
        if isinstance(node.op, ast.Mult):
            return tuple(x + y for x, y in zip(a, b))
        if isinstance(node.op, ast.Div):
            return tuple(x - y for x, y in zip(a, b))
        if isinstance(node.op, ast.Pow):
            if not same_dims(b, DIMLESS):
                raise DimensionError("An exponent must be dimensionless")
            try:
                p = float(ast.literal_eval(node.right))
            except ValueError:
                if same_dims(a, DIMLESS):
                    return DIMLESS
                raise DimensionError("A quantity with units needs a plain number as exponent")
            return tuple(x * p for x in a)
        raise DimensionError(f"Operator not supported: {type(node.op).__name__}")
    if isinstance(node, ast.Call):
        name = node.func.id
        args = [_dims(a, units) for a in node.args]
        if name in _DIMLESS_FUNCS:
            if args and args[0] is not None and not same_dims(args[0], DIMLESS):
                raise DimensionError(
                    f"{name}() needs a dimensionless argument, got {format_dims(args[0])}")
            return DIMLESS
        if name == "sqrt":
            return tuple(x / 2 for x in (args[0] or DIMLESS))
        if name in ("abs", "minimum", "maximum"):
            return args[0]
        if name == "where":
            return args[1]
        raise DimensionError(f"Function not supported: {name}")
    if isinstance(node, ast.Compare):
        return DIMLESS
    raise DimensionError(f"Not supported: {type(node).__name__}")


def si_formula(formula: str, units: dict[str, Unit]) -> str:
    """Rewrite a formula so every name is converted to SI first."""
    tree = ast.parse(formula, mode="eval")

    class _ToSI(ast.NodeTransformer):
        def visit_Name(self, node):
            u = units.get(node.id)
            if u is None or (u.scale == 1.0 and u.offset == 0.0):
                return node
            return ast.parse(_si_term(node.id, u), mode="eval").body

    return ast.unparse(_ToSI().visit(tree))


def _si_term(name: str, u: Unit) -> str:
    if u.scale == 1.0 and u.offset == 0.0:
        return name
    expr = name if u.scale == 1.0 else f"{name} * {u.scale!r}"
    if u.offset:
        expr = f"{expr} + {u.offset!r}"
    return f"({expr})"


# --------------------------------------------------------------------------- Buckingham π

@dataclass
class PiGroup:
    main: str                         # the non-repeating variable this group is built on
    exponents: dict[str, Fraction]    # variable -> exponent (main has exponent 1)

    def label(self) -> str:
        parts = []
        for v, e in self.exponents.items():
            if e == 0:
                continue
            parts.append(v if e == 1 else f"{v}^{e}")
        return " · ".join(parts)

    def formula(self, units: dict[str, Unit]) -> str:
        """Python formula evaluating the group from raw columns, in SI."""
        parts = []
        for v, e in self.exponents.items():
            if e == 0:
                continue
            term = _si_term(v, units[v])
            if e != 1:
                exp = str(e.numerator) if e.denominator == 1 else f"({e.numerator}/{e.denominator})"
                term = f"{term}**{exp}"
            parts.append(term)
        return " * ".join(parts)


@dataclass
class PiResult:
    variables: list[str]
    rank: int
    repeating: list[str]
    groups: list[PiGroup] = field(default_factory=list)

    @property
    def n_groups(self) -> int:
        return len(self.variables) - self.rank


def dimension_matrix(variables: list[str], units: dict[str, Unit]) -> np.ndarray:
    return np.array([units[v].dims for v in variables], dtype=float).T  # 5 x n


def auto_repeating(variables: list[str], units: dict[str, Unit]) -> list[str]:
    """Pick repeating variables greedily, keeping the first (dependent) one out."""
    D = dimension_matrix(variables, units)
    rank = np.linalg.matrix_rank(D)
    chosen: list[int] = []
    order = list(range(1, len(variables))) + [0]
    for j in order:
        trial = chosen + [j]
        if np.linalg.matrix_rank(D[:, trial]) == len(trial):
            chosen = trial
        if len(chosen) == rank:
            break
    return [variables[j] for j in sorted(chosen)]


def buckingham(variables: list[str], units: dict[str, Unit],
               repeating: list[str] | None = None) -> PiResult:
    if len(set(variables)) != len(variables):
        raise DimensionError("A variable is listed twice")
    D = dimension_matrix(variables, units)
    rank = int(np.linalg.matrix_rank(D))
    if repeating is None:
        repeating = auto_repeating(variables, units)
    rep_idx = [variables.index(v) for v in repeating]
    A = D[:, rep_idx]
    if len(repeating) != rank or np.linalg.matrix_rank(A) != rank:
        raise DimensionError(
            f"Choose {rank} repeating variables that together contain all the dimensions "
            f"involved, and that cannot be combined into a dimensionless group themselves.")
    res = PiResult(list(variables), rank, list(repeating))
    for j, v in enumerate(variables):
        if v in repeating:
            continue
        a, *_ = np.linalg.lstsq(A, -D[:, j], rcond=None)
        if np.abs(A @ a + D[:, j]).max() > 1e-6:
            raise DimensionError(f"Could not make '{v}' dimensionless")
        exps = {v: Fraction(1)}
        for r, coef in zip(repeating, a):
            f = Fraction(float(coef)).limit_denominator(12)
            if f != 0:
                exps[r] = f
        res.groups.append(PiGroup(v, exps))
    return res


def is_dimensionless(formula: str, units: dict[str, Unit]) -> tuple[bool, str]:
    try:
        d = formula_dims(formula, units) or DIMLESS
    except (DimensionError, UnitError, SyntaxError) as exc:
        return False, str(exc)
    return same_dims(d, DIMLESS), format_dims(d)
