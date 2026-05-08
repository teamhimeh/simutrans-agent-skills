---
name: simutrans-start-convoy
description: 指定した車庫（デポ）の指定した編成を出庫させる。
argument-hint: "<depot_x> <depot_y> <編成名（部分一致）>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 編成出庫

引数 `$ARGUMENTS` を `"<depot_x> <depot_y> <編成名>"` の形式で受け取り、指定座標の車庫にある指定編成を出庫させる。

## 手順

### Step 1: 車庫内の編成一覧を確認

まず対象座標のタイルからデポを取得し、在庫している編成名とインデックスを一覧表示する。

```squirrel
local pl = player_x(0)
local dx = 912   // $ARGUMENTS から取得
local dy = 180   // $ARGUMENTS から取得

// 高さ0でタイルを取得してデポを探す
local tile = tile_x(dx, dy, 0)
local depot = tile.get_depot()
if(depot == null) return "指定座標にデポが見つかりません: (" + dx + "," + dy + ")"

local convoys = depot.get_convoy_list()
local result = "デポ (" + dx + "," + dy + ") の編成一覧:\n"
local i = 0
foreach(cnv in convoys) {
    result += i + ": " + cnv.get_name() + "\n"
    i++
}
return result == "デポ (" + dx + "," + dy + ") の編成一覧:\n" ? "編成なし" : result
```

**注意:** `tile_x` は `tile_x(x, y, z)` の形式。高さ0で見つからない場合は高さを変えて再試行する。

### Step 2: 出庫対象の編成を特定して出庫

Step 1 の一覧で確認した編成名（部分一致）で対象を絞り込み、`depot.start_convoy` で出庫させる。

```squirrel
local pl = player_x(0)
local dx = 912
local dy = 180
local keyword = "編成名"  // $ARGUMENTS の第3引数

local tile = tile_x(dx, dy, 0)
local depot = tile.get_depot()
if(depot == null) return "指定座標にデポが見つかりません"

local convoys = depot.get_convoy_list()
local target = null
foreach(cnv in convoys) {
    if(cnv.get_name().find(keyword) != null) {
        target = cnv
        break
    }
}
if(target == null) return "編成が見つかりません: " + keyword

depot.start_convoy(pl, target)
return "出庫しました: " + target.get_name()
```

### Step 3: 出庫確認

出庫後、編成がデポから消えたかを確認する。

```squirrel
local tile = tile_x(dx, dy, 0)
local depot = tile.get_depot()
local convoys = depot.get_convoy_list()
local result = "残存編成数: " + convoys.len() + "\n"
foreach(cnv in convoys) {
    result += "  " + cnv.get_name() + "\n"
}
return result
```

## 注意事項

- **スケジュール未設定の編成を出庫させると即デポに戻る。** 出庫前に路線が割り当てられているか確認すること。
- `depot.start_all_convoys(pl)` で全編成を一括出庫することも可能。
- player_nr=0 で実行する。
- `call_tool_init` を使うため、戻り値は非ネットワークモードで `true`（成功）。
