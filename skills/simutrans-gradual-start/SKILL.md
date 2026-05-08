---
name: simutrans-gradual-start
description: 指定路線の指定停留所で発車待ちの編成数が閾値以下になるごとに、デポから指定台数を出庫させる監視スクリプトを起動する。
argument-hint: "<depot_x> <depot_y> <路線番号または名前> [schedule_index=0] [threshold=2] [batch=2] [interval=2]"
allowed-tools: mcp__simutrans__run_squirrel, Bash
---

# Simutrans 段階的出庫（監視付き）

引数 `$ARGUMENTS` を受け取り、バックグラウンド監視プロセスを起動する。

**リソース:** このスキルのディレクトリにある `monitor_convoy.py` を使用する。

## 引数フォーマット

```
<depot_x> <depot_y> <路線番号または名前> [schedule_index=0] [threshold=2] [batch=2] [interval=2]
```

| 引数 | 説明 | 例 |
|---|---|---|
| depot_x, depot_y | デポのタイル座標 | `31 184` |
| 路線番号または名前 | `(2)` のような番号、またはフル名 | `(2)` / `(2) [IC] 西宮-帯広` |
| schedule_index | 監視する停留所のスケジュールインデックス | `0`（始発停留所） |
| threshold | 発車待ち台数の閾値（以下になったら出庫） | `2` |
| batch | 1回に出庫する台数 | `2` |
| interval | チェック間隔（秒） | `2` |

## 手順

### Step 1: 路線のフル名を解決する

引数が `(2)` のような番号形式の場合は、まず路線のフル名を取得する。

```squirrel
local pl = player_x(0)
local lines = pl.get_line_list()
local result = ""
foreach(ln in lines) {
    local name = ln.get_name()
    if(name.slice(0, 3) == "(2)") {   // 番号部分でマッチ
        result = name
        break
    }
}
return result == "" ? "NOT FOUND" : result
```

フル名が取得できたら Step 2 へ。

### Step 2: 既存の監視プロセスを停止する

同じログファイルを使うプロセスが残っている場合は停止する。

```bash
pkill -f "monitor_convoy.py" 2>/dev/null; sleep 0.5
```

### Step 3: 監視スクリプトを起動する

スキルのディレクトリにある `monitor_convoy.py` をバックグラウンドで起動する。

```bash
SKILL_DIR="$(dirname "$0")"
# または絶対パスで
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"  # このスクリプトと同じディレクトリ

python3 "$SKILL_DIR/monitor_convoy.py" \
    <depot_x> <depot_y> "<line_full_name>" \
    <schedule_index> <threshold> <batch> <interval> \
    > /tmp/monitor_convoy.log 2>&1 &

echo "PID: $!"
```

### Step 4: 起動確認

数秒待ってログを確認し、正常動作していることを報告する。

```bash
sleep 5 && cat /tmp/monitor_convoy.log
```

ログに `ERROR` が出ていなければ成功。

## 停止方法

デポ内の編成が空になると自動終了する。手動で止める場合:

```bash
pkill -f "monitor_convoy.py"
```

## ログ確認

```bash
tail -20 /tmp/monitor_convoy.log
```

## 注意事項

- デポの編成はすでに対象路線のスケジュールが設定済みであること（未設定だと出庫後即デポ戻り）。
- `schedule_index=0` は通常、路線の始発停留所（西宮バスターミナル等）に対応する。
- 同時に複数の監視を走らせる場合はログファイルを別パスにすること（`/tmp/monitor_convoy_2.log` 等）。
- プロセスはターミナルセッションを超えて生存する（明示的に `pkill` するまで継続）。
