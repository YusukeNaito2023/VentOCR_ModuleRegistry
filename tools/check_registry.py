"""modules.json の形を確かめる: python3 tools/check_registry.py（問題が無ければ終了コード 0）。push の前に実行する。

format 2: module_key ごとに1つの項目で、版は versions[]（版の昇順・重ならない）。版は 0.X.Y、タグ = v<版>、
manifest.json の version = 版、manifest.json の module_key = キー、module_api・ventocr_min・engines・requires がある、outputs の形。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 2
REQUIRED = ("module_key", "repository", "versions")
VERSION_REQUIRED = ("version", "tag", "commit", "manifest", "validation")
MANIFEST_REQUIRED = ("module_key", "version", "module_api", "ventocr_min", "engines", "requires")
VALIDATION = ("reported", "module_version", "date", "reporter", "videos", "breaths", "modes", "comment", "values", "waveforms")
RESULT = ("metric", "result", "n", "comment")
VERSION = re.compile(r"0\.(\d+)\.(\d+)")
COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def check_outputs(where: str, outputs) -> list[str]:
    if outputs is None:
        return []
    if not isinstance(outputs, dict):
        return [f"{where}: outputs は {{\"waves\": [...], \"breath_values\": [...]}}"]
    problems = []
    for group in ("waves", "breath_values"):
        items = outputs.get(group) or []
        if not isinstance(items, list):
            problems.append(f"{where}: outputs.{group} はリスト")
            continue
        names = [i.get("name") for i in items if isinstance(i, dict)]
        if len(names) != len(items) or not all(isinstance(n, str) and n for n in names):
            problems.append(f"{where}: outputs.{group} の各項目に name（文字）が要る")
        if len(set(names)) != len(names):
            problems.append(f"{where}: outputs.{group} の name が重複している")
        for item in items:
            if isinstance(item, dict) and item.get("color") and not COLOR.fullmatch(str(item["color"])):
                problems.append(f"{where}: outputs.{group}.{item.get('name')}.color は #rrggbb")
    return problems


def check_version(name: str, r: dict) -> list[str]:
    version = r.get("version", "")
    where = f"{name} {version or '?'}"
    problems = [f"{where}: {k} がありません" for k in VERSION_REQUIRED if not r.get(k) and r.get(k) is not False]
    if not VERSION.fullmatch(version or ""):
        problems.append(f"{where}: version は 0.X.Y")
    if r.get("tag") != f"v{version}":
        problems.append(f"{where}: tag は v{version}")
    manifest = r.get("manifest") or {}
    problems += [f"{where}: manifest の {k} がありません" for k in MANIFEST_REQUIRED if k not in manifest]
    if manifest.get("version") != version:
        problems.append(f"{where}: manifest の version（{manifest.get('version')}）が版と違います")
    if manifest.get("module_key") != name:
        problems.append(f"{where}: manifest の module_key が違います")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("ventocr_min", ""))):
        problems.append(f"{where}: manifest の ventocr_min は X.Y.Z")
    if not isinstance(manifest.get("engines"), list) or not manifest.get("engines"):
        problems.append(f"{where}: manifest の engines はリスト（全部なら [\"*\"]）")
    requires = manifest.get("requires")
    if not isinstance(requires, dict) or not isinstance(requires.get("waves", []), list):
        problems.append(f"{where}: manifest の requires は {{\"waves\": [...], \"columns\": [...]}}")
    problems += check_outputs(where, manifest.get("outputs"))
    if not re.fullmatch(r"[0-9a-f]{40}", r.get("commit") or ""):
        problems.append(f"{where}: commit は 40 桁のコミット")
    if r.get("image") is not None and (not re.fullmatch(r"[\w./-]+", str(r["image"])) or ".." in str(r["image"])):
        problems.append(f"{where}: image はリポジトリの中のファイル名")
    v = r.get("validation") or {}
    problems += [f"{where}: validation.{k} がありません" for k in VALIDATION if k not in v]
    for group in ("values", "waveforms"):
        for col, res in (v.get(group) or {}).items():
            problems += [f"{where}: validation.{group}.{col}.{k} がありません" for k in RESULT if k not in res]
    if v.get("reported") and not (v.get("module_version") and v.get("date") and v.get("breaths")):
        problems.append(f"{where}: reported なら module_version・date・breaths を書く")
    return problems


def main() -> int:
    data = json.loads((ROOT / "modules.json").read_text("utf-8"))
    problems = []
    if data.get("format") != FORMAT:
        problems.append(f"format は {FORMAT}")
    keys = set()
    n_versions = 0
    for i, e in enumerate(data.get("modules", [])):
        name = e.get("module_key", f"#{i}")
        problems += [f"{name}: {k} がありません" for k in REQUIRED if not e.get(k)]
        if name in keys:
            problems.append(f"{name}: module_key が重複しています")
        keys.add(name)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            problems.append(f"{name}: module_key は英字で始まる英数字と _")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", e.get("repository", "")):
            problems.append(f"{name}: repository は 所有者/名前")
        versions = e.get("versions") or []
        n_versions += len(versions)
        for r in versions:
            problems += check_version(name, r)
        numbers = [tuple(map(int, m.groups())) for r in versions if (m := VERSION.fullmatch(r.get("version") or ""))]
        if len(set(numbers)) != len(numbers):
            problems.append(f"{name}: 同じ版が2つあります")
        elif numbers != sorted(numbers):
            problems.append(f"{name}: versions は版の昇順に並べる")
    for p in problems:
        print(p)
    print(f"{len(data.get('modules', []))} 個のモジュール（{n_versions} 個の版）、" + (f"{len(problems)} 件の問題" if problems else "問題ありません"))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
