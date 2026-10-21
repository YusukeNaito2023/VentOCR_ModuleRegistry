# VentOCR_ModuleRegistry

The list of VentOCR post-analysis modules that users can install from the VentOCR desktop app (**Analysis > Modules…**).
Only modules listed in [`modules.json`](modules.json) can be installed from the app. Each module lists its released versions;
each version pins a tag and commit of the public module repository and carries a validation report.

VentOCR のデスクトップアプリの「解析 > モジュール…」からインストールできる、事後解析のモジュールの一覧です（ライセンスは MIT）。
エンジンの一覧（[VentOCR_EngineRegistry](https://github.com/YusukeNaito2023/VentOCR_EngineRegistry)）と同じ作りです。
モジュールの約束事は [VentOCR_ModuleTemplate の MODULE_API.md](https://github.com/YusukeNaito2023/VentOCR_ModuleTemplate/blob/main/MODULE_API.md)。

## アプリでの使われ方

- アプリはネットにつながっていれば、モジュールの画面を開くたびと起動のときに、このリポジトリの `main` の最新の `modules.json` を読む。
  つながっていなければ前回読んだ一覧を使う
- 一覧のモジュールは「インストール」（versions の最新の版）で、その版の `commit` の zip をダウンロードして入れる。一覧の別の版に入れ直せる
- モジュールの manifest の `module_api`・`ventocr_min` がアプリより新しい版は、インストールできない（「VentOCR を更新してください」）

## 形（format 2）

```json
{"format": 2, "updated": "2026-10-21",
 "modules": [{"module_key": "get_pes_from_transpulm", "repository": "YusukeNaito2023/VentOCR_Module_GetPesFromTranspulm",
              "versions": [{"version": "0.1.0", "tag": "v0.1.0", "commit": "…", "manifest": {…}, "validation": {…}, …}]}]}
```

| キー（モジュール） | 内容 |
|---|---|
| `module_key` | モジュールキー（入れるフォルダの名前。manifest.json の `module_key` と同じ） |
| `repository` | モジュールの公開リポジトリ（`所有者/名前`。`VentOCR_Module_<名前>`） |
| `versions` | 版の一覧（版の昇順） |

| キー（版） | 内容 |
|---|---|
| `version` | 版（`0.X.Y`）。manifest.json の `version`・module.py の `MODULE_VERSION` と同じ |
| `tag`, `commit` | 版のタグ（`v<版>`）と、そのコミット（40 桁）。アプリは `commit` の zip を使う |
| `manifest` | タグの時点の manifest.json（対象のエンジン `engines`・要る波形 `requires`・出力の宣言 `outputs` を含む） |
| `default_options` | module_options.json（既定の設定） |
| `readme` | README.md の中身 |
| `image` | 説明の画像のファイル名（リポジトリの `image.png`。無ければ null） |
| `validation` | 精度の評価（下。版ごと） |

### validation（精度の評価）

| キー | 内容 |
|---|---|
| `reported` | 報告があるか |
| `module_version` | 評価したモジュールの版 |
| `date`, `reporter` | 評価した日・評価した人 |
| `reference` | 基準（正解）は何か（例: 呼吸器のモニターの記録） |
| `engine` | 評価に使った解析のエンジンと版 |
| `videos`, `breaths`, `modes` | 評価に使った動画の数・呼吸の数・換気モード |
| `comment` | 自由記載 |
| `values` | 1呼吸1値ごと: `{"unit", "metric", "result", "n", "comment"}` |
| `waveforms` | 波形ごと: `{"metric", "result", "n", "comment"}` |

## モジュールを載せる・版を上げる

1. モジュールのリポジトリで版を上げてタグ `v<版>` を付け、GitHub に push する
2. このリポジトリで `python3 tools/make_entry.py ../VentOCR_Module_<名前> v<版>`（そのキーの `versions` に版が足される）。
   モジュールのリポジトリに `validation.json` があれば、それが精度の評価になる
3. `python3 tools/check_registry.py` → コミットして `main` に push
