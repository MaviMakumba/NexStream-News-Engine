"""Hafif mutasyon testi: testler gerçekten kodun bozulduğunu yakalıyor mu?

Neden kendi aracımız: `mutmut` 3.x Linux fork'u gerektiriyor, Windows'ta çalışmıyor.
Bu araç bir kaynak dosyada her seferinde TEK değişiklik (mutant) yapar, ilgili
testleri koşar ve **testlerin yakalayamadığı (hayatta kalan)** mutantları listeler.
Hayatta kalan mutant = kod bozulmuş ama hiçbir test kırılmamış → zayıf/eksik test.

Kullanım:
    python scripts/mutation_check.py src/domain/news_cursor.py tests/adapters/test_v1_news_router.py
    python scripts/mutation_check.py <kaynak.py> <test dosyaları...> [--max N]

Kaynak dosya her mutant sonrası (hata olsa bile) özgün haline döndürülür.
Mutasyon operatörleri: karşılaştırma tersleme/gevşetme (< <= > >= == !=), and<->or,
`not` silme, True<->False, sayı sabiti ±1, aritmetik (+ <-> -), `return <ifade>` → None.
Yorum/biçim mutantları sayılmaz (çıktı ast.unparse ile yeniden üretilir).
"""
import ast
import copy
import os
import subprocess
import sys
from pathlib import Path

_CMP_SWAP = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}
_ARITH_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add}


def _sites(tree: ast.AST):
    """(düğüm_indeksi, tür, açıklama) — ast.walk sırası deterministik."""
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare):
            for j, op in enumerate(node.ops):
                if type(op) in _CMP_SWAP:
                    yield i, ("cmp", j), f"satır {node.lineno}: {type(op).__name__} → {_CMP_SWAP[type(op)].__name__}"
        elif isinstance(node, ast.BoolOp):
            to = "or" if isinstance(node.op, ast.And) else "and"
            yield i, ("bool",), f"satır {node.lineno}: {type(node.op).__name__.lower()} → {to}"
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            yield i, ("not",), f"satır {node.lineno}: `not` silindi"
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                yield i, ("bool_const",), f"satır {node.lineno}: {node.value} → {not node.value}"
            elif isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                yield i, ("num",), f"satır {node.lineno}: {node.value} → {node.value + 1}"
        elif isinstance(node, ast.BinOp) and type(node.op) in _ARITH_SWAP:
            yield i, ("arith",), f"satır {node.lineno}: {type(node.op).__name__} → {_ARITH_SWAP[type(node.op)].__name__}"
        elif isinstance(node, ast.Return) and node.value is not None \
                and not (isinstance(node.value, ast.Constant) and node.value.value is None):
            yield i, ("ret",), f"satır {node.lineno}: return <ifade> → return None"


def _mutate(tree: ast.AST, index: int, kind: tuple) -> ast.AST:
    tree = copy.deepcopy(tree)
    node = list(ast.walk(tree))[index]
    if kind[0] == "cmp":
        node.ops[kind[1]] = _CMP_SWAP[type(node.ops[kind[1]])]()
    elif kind[0] == "bool":
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
    elif kind[0] == "not":
        # `not x` → `x`: düğümü içeriğiyle değiştirmek için üst düğümü bulmak gerekir.
        for parent in ast.walk(tree):
            for field, value in ast.iter_fields(parent):
                if value is node:
                    setattr(parent, field, node.operand)
                elif isinstance(value, list):
                    for k, item in enumerate(value):
                        if item is node:
                            value[k] = node.operand
    elif kind[0] == "bool_const":
        node.value = not node.value
    elif kind[0] == "num":
        node.value = node.value + 1
    elif kind[0] == "arith":
        node.op = _ARITH_SWAP[type(node.op)]()
    elif kind[0] == "ret":
        node.value = ast.Constant(value=None)
    return ast.fix_missing_locations(tree)


def _tests_pass(test_files: list[str]) -> bool:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *test_files, "-x", "-q", "-p", "no:cacheprovider",
         "--no-header", "-W", "ignore"],
        capture_output=True, text=True, timeout=300,
        # Bayt kodu yazılmasın: aynı saniyede/aynı boyutta mutantlar bayat .pyc'ye takılıp
        # sahte "hayatta kaldı" üretmesin.
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return r.returncode == 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    max_mutants = None
    if "--max" in sys.argv:
        max_mutants = int(sys.argv[sys.argv.index("--max") + 1])
        args = [a for a in args if a != str(max_mutants)]
    if len(args) < 2:
        print(__doc__)
        return 2
    source, tests = Path(args[0]), args[1:]
    original = source.read_text(encoding="utf-8")
    tree = ast.parse(original)

    if not _tests_pass(tests):
        print("Mutasyondan ÖNCE testler zaten kırmızı — önce onları düzelt.")
        return 2

    sites = list(_sites(tree))
    if max_mutants:
        sites = sites[:max_mutants]
    survivors, killed = [], 0
    try:
        for n, (index, kind, desc) in enumerate(sites, 1):
            source.write_text(ast.unparse(_mutate(tree, index, kind)) + "\n", encoding="utf-8")
            try:
                caught = not _tests_pass(tests)
            except subprocess.TimeoutExpired:
                caught = True  # sonsuz döngü/asılma da "yakalandı" sayılır
            if caught:
                killed += 1
            else:
                survivors.append(desc)
            print(f"[{n}/{len(sites)}] {'yakalandı ' if caught else 'HAYATTA  '} {desc}", flush=True)
    finally:
        source.write_text(original, encoding="utf-8")

    total = len(sites)
    print(f"\n{source}: {killed}/{total} mutant yakalandı (%{100 * killed // max(total, 1)})")
    if survivors:
        print("HAYATTA KALANLAR (testlerin yakalayamadığı):")
        for s in survivors:
            print("  -", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
