"""Extra parameters that are not in the workbook.

Three kinds, all saved in one JSON file so they survive restarts and never
require editing the Excel file:

* constant  - one number with a unit, e.g. R = 8.314 J/(mol K). Usable in formulas.
* lookup    - a value per category of an existing column, e.g. elastic modulus
              per Material (304 -> 193 GPa, 316L -> 193 GPa ...).
* formula   - a new column computed from others, e.g. 1000 / (Temp + 273.15).

Formulas may use column variable names (CGR, K, Temp, ...), constant names,
earlier custom parameters, numbers, + - * / ** and the functions in FUNCTIONS.
Nothing else is allowed, so a typo cannot run arbitrary code.
"""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .loader import ColumnInfo, Dataset, make_var

FUNCTIONS = {
    "log": np.log, "ln": np.log, "log10": np.log10, "exp": np.exp,
    "sqrt": np.sqrt, "abs": np.abs, "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "where": np.where, "minimum": np.minimum, "maximum": np.maximum,
}
CONSTANTS_BUILTIN = {"pi": np.pi, "e": np.e}

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd,
    ast.Compare, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq,
)


@dataclass
class CustomParam:
    name: str                 # identifier used in formulas and as column name
    kind: str                 # "constant", "lookup" or "formula"
    unit: str = ""
    description: str = ""
    value: float | None = None              # constant
    formula: str = ""                       # formula
    key_column: str = ""                    # lookup: column whose categories are keys
    mapping: dict[str, float] = field(default_factory=dict)  # lookup
    default: float | None = None            # lookup: value for unlisted categories


class FormulaError(ValueError):
    pass


def check_formula(formula: str, known_names: set[str]) -> None:
    """Raise FormulaError if the formula uses anything that is not allowed."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Syntax error: {exc.msg}") from None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise FormulaError(f"Not allowed in a formula: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
                raise FormulaError(
                    "Only these functions are allowed: " + ", ".join(sorted(FUNCTIONS))
                )
            if node.keywords:
                raise FormulaError("Functions take positional arguments only")
        if isinstance(node, ast.Name) and not (
            node.id in known_names or node.id in FUNCTIONS or node.id in CONSTANTS_BUILTIN
        ):
            raise FormulaError(f"Unknown name '{node.id}'")


def evaluate_formula(formula: str, df: pd.DataFrame, constants: dict[str, float]) -> pd.Series:
    names = set(df.columns) | set(constants)
    check_formula(formula, names)
    scope = {c: df[c].astype(float) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    scope.update(constants)
    scope.update(CONSTANTS_BUILTIN)
    scope.update(FUNCTIONS)
    tree = ast.parse(formula, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in scope:
            raise FormulaError(f"'{node.id}' is not a numeric column")
    with np.errstate(all="ignore"):
        result = eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, scope)
    if np.isscalar(result):
        result = np.full(len(df), float(result))
    s = pd.Series(np.asarray(result, dtype=float), index=df.index)
    return s.replace([np.inf, -np.inf], np.nan)


def apply_params(ds: Dataset, params: list[CustomParam]) -> tuple[Dataset, list[str]]:
    """Return a copy of the dataset with custom parameters added as columns.

    Parameters are applied in list order, so a formula may use earlier ones.
    Errors are collected rather than raised, so one broken formula does not
    hide the rest of the data.
    """
    df = ds.df.copy()
    columns = dict(ds.columns)
    constants: dict[str, float] = {}
    errors: list[str] = []
    for p in params:
        try:
            if p.kind == "constant":
                constants[p.name] = float(p.value)
                continue
            if p.name in columns:
                raise FormulaError(f"'{p.name}' already exists in the data")
            if p.kind == "formula":
                df[p.name] = evaluate_formula(p.formula, df, constants)
                note = p.description or f"= {p.formula}"
            elif p.kind == "lookup":
                if p.key_column not in df.columns:
                    raise FormulaError(f"Lookup column '{p.key_column}' not found")
                keys = df[p.key_column].astype("string")
                mapping = {str(k): v for k, v in p.mapping.items() if v is not None}
                vals = keys.map(mapping).astype(float)
                if p.default is not None:
                    vals = vals.fillna(float(p.default))
                df[p.name] = vals
                note = p.description or f"per {p.key_column}"
            else:
                raise FormulaError(f"Unknown kind '{p.kind}'")
            columns[p.name] = ColumnInfo(
                header=p.name, name=p.name, unit=p.unit, var=p.name,
                kind="numeric", note=note, source="custom",
            )
        except (FormulaError, TypeError, ValueError) as exc:
            errors.append(f"{p.name}: {exc}")
    out = Dataset(df=df, columns=columns, sheet=ds.sheet, header_row=ds.header_row,
                  warnings=list(ds.warnings))
    return out, errors


def valid_name(name: str) -> bool:
    return bool(name) and make_var(name) == name and name not in FUNCTIONS \
        and name not in CONSTANTS_BUILTIN


def load_params(path: Path) -> list[CustomParam]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [CustomParam(**item) for item in data.get("parameters", [])]


def save_params(path: Path, params: list[CustomParam]) -> None:
    payload = {"parameters": [asdict(p) for p in params]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
