"""モジュールのリポジトリのタグから modules.json の版を作る・足す（format 2）。

    python3 tools/make_entry.py <モジュールのリポジトリ（手元の clone）> <タグ> [--repository 所有者/名前] [--ref <コミット>]

- タグの時点のファイル（manifest.json・module.py の MODULE_VERSION・module_options.json・README.md・image.png・validation.json）を
  `git show <タグ>:<ファイル>` で読む（作業中の変更は使わない）。タグのコミットは GitHub に push 済みであること
- 版は 0.X.Y。タグ = v<版>、manifest.json の version = module.py の MODULE_VERSION = 版、module_key が正しい形でなければ止める
- 既存のキーなら versions に足す（同じ版があれば置き換える。そのときは validation を残す）。新しいキーなら項目を作る
- validation（精度の評価）は、タグに validation.json があればそれを使う。無ければ、同じ版の前の値か、空（reported: false）
- --ref: GitHub に push する前に手元で試すとき、タグの代わりにこのコミットのファイルを読む（commit もこれになる）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "modules.json"
IMAGE = "image.png"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def show(repo: Path, ref: str, path: str) -> str | None:
    try:
        return git(repo, "show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def exists(repo: Path, ref: str, path: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{ref}:{path}"], capture_output=True).returncode == 0


def blank_validation(manifest: dict) -> dict:
    outputs = manifest.get("outputs") or {}
    return {
        "reported": False, "module_version": None, "date": None, "reporter": None, "reference": None, "engine": None,
        "videos": None, "breaths": None, "modes": [], "comment": "",
        "values": {v["name"]: {"unit": v.get("unit"), "metric": None, "result": None, "n": None, "comment": ""}
                   for v in outputs.get("breath_values") or [] if isinstance(v, dict) and v.get("name")},
        "waveforms": {w["name"]: {"metric": None, "result": None, "n": None, "comment": ""}
                      for w in outputs.get("waves") or [] if isinstance(w, dict) and w.get("name")},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("tag")
    parser.add_argument("--repository", help="GitHub の 所有者/名前（省略すると origin の URL から）")
    parser.add_argument("--ref", help="タグの代わりに読むコミット（push する前に手元で試すとき）")
    args = parser.parse_args()
    repo = args.repo.resolve()
    ref = args.ref or args.tag

    text = show(repo, ref, "manifest.json")
    if text is None:
        sys.exit(f"{ref} に manifest.json がありません")
    manifest = json.loads(text)
    key = manifest.get("module_key")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
        sys.exit("manifest.json に正しい module_key がありません")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"0\.\d+\.\d+", version):
        sys.exit(f"manifest.json の version が 0.X.Y ではありません: {version!r}")
    if args.tag != f"v{version}":
        sys.exit(f"タグ {args.tag} が manifest.json の version（v{version}）と違います")
    module_py = show(repo, ref, "module.py") or ""
    m = re.search(r'^MODULE_VERSION\s*=\s*["\']([^"\']+)["\']', module_py, re.M)
    if not m or m.group(1) != version:
        sys.exit(f"module.py の MODULE_VERSION（{m.group(1) if m else None}）が manifest.json の version（{version}）と違います")
    options = show(repo, ref, "module_options.json")
    repository = args.repository
    if not repository:
        url = git(repo, "remote", "get-url", "origin").strip()
        repository = re.sub(r"(\.git)?$", "", url.split("github.com")[-1].lstrip(":/"))
    release = {
        "version": version,
        "tag": args.tag,
        "commit": git(repo, "rev-list", "-n", "1", ref).strip(),
        "manifest": manifest,
        "default_options": json.loads(options) if options else None,
        "readme": show(repo, ref, "README.md"),
        "image": IMAGE if exists(repo, ref, IMAGE) else None,
    }
    validation_text = show(repo, ref, "validation.json")

    registry = json.loads(REGISTRY.read_text("utf-8")) if REGISTRY.is_file() else {"format": 2, "modules": []}
    if registry.get("format") != 2:
        sys.exit(f"modules.json の format が 2 ではありません（{registry.get('format')}）")
    entry = next((e for e in registry["modules"] if e["module_key"] == key), None)
    if entry is None:
        entry = {"module_key": key, "repository": repository, "versions": []}
        registry["modules"].append(entry)
    entry["repository"] = repository
    old = next((v for v in entry["versions"] if v["version"] == version), None)
    if validation_text:
        release["validation"] = json.loads(validation_text)
    else:
        release["validation"] = (old or {}).get("validation") or blank_validation(manifest)
    entry["versions"] = sorted([v for v in entry["versions"] if v["version"] != version] + [release],
                               key=lambda v: tuple(int(x) for x in v["version"].split(".")))
    registry["modules"].sort(key=lambda e: e["module_key"].lower())
    registry["updated"] = date.today().isoformat()
    REGISTRY.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"{key} {args.tag}（{release['commit'][:12]}）を{'置き換え' if old else '追加し'}ました（版: {', '.join(v['version'] for v in entry['versions'])}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
