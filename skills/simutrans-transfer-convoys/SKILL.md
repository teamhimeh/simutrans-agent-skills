---
name: simutrans-transfer-convoys
description: 指定した編成数を、ある路線から別の路線へ付け替える。各編成の現在地に最も近いインデックスから再開するよう設定する。
argument-hint: "<移管元路線名> <移管先路線名> <編成数>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 編成路線付け替え

引数 `$ARGUMENTS` を `"<移管元> <移管先> <N>"` の形式で受け取り、N 編成を移管元から移管先へ付け替える。  
各編成の現在地 (`convoy.get_pos()`) から最も近い移管先スケジュールのインデックスを選んで設定するため、切り替え直後の混乱を最小化できる。

## 重要な実装ポイント

### 1. コンボイリストを先に配列へ収集する

`foreach(cnv in line.get_convoy_list())` でイテレーション中に `set_line` を呼ぶと、リストが縮んでイテレーションが途中で止まる。**必ず先に配列へ収集してから**移管する。

```squirrel
local arr = []
foreach(cnv in src_line.get_convoy_list()) { arr.append(cnv) }
```

### 2. `change_schedule` でラインとの関連を保ちつつ `current` を設定できる

`set_line` 後に `change_schedule` を呼んでも、スケジュール内容（エントリの stops・flags・spacing 等）が一致する限り `schedule_t::matches()` が `true` を返すため、**ラインとの関連は外れない**。`current`（現在向かっている index）は `matches()` の比較対象外。

```squirrel
// set_line でラインに所属させてから
cnv.set_line(pl, dst_line)

// ラインのスケジュールを取得して current だけ近いインデックスに書き換える
local sched = dst_line.get_schedule()
sched.current = best_idx
cnv.change_schedule(pl, sched)  // ライン所属はそのまま維持される
```

### 3. `convoy.get_pos()` で現在地を取得できる

`get_pos()` は `coord3d` インスタンス（`.x`, `.y`, `.z`）を返す。

```squirrel
local pos = cnv.get_pos()  // coord3d
local dx = halt_tile.x - pos.x
local dy = halt_tile.y - pos.y
local dist2 = dx*dx + dy*dy   // 比較にはsqrt不要
```

## 実装手順

### Step 1: 対象路線を特定

```squirrel
local pl = player_x(0)
// $ARGUMENTS を空白で分割してパース（路線名にスペースが含まれる場合は別途調整）
local src_name = ...
local dst_name = ...
local transfer_n = ...

local lines = pl.get_line_list()
local src_line = null
local dst_line = null
foreach(line in lines) {
    local n = line.get_name()
    if(n.find(src_name) != null) src_line = line
    if(n.find(dst_name) != null) dst_line = line
}
if(src_line == null || dst_line == null) return "路線が見つかりません"
```

### Step 2: 移管先スケジュールの各エントリ位置を事前取得

```squirrel
local dst_sched = dst_line.get_schedule()
local halt_positions = []   // 各インデックスの (x,y) を格納
foreach(i, entry in dst_sched.entries) {
    try {
        local h = entry.get_halt(pl)
        if(typeof(h) == "instance" && h.is_valid()) {
            local tiles = h.get_tile_list()
            if(tiles.len() > 0) {
                halt_positions.append({ idx = i, x = tiles[0].x, y = tiles[0].y })
            }
        }
    } catch(e) {}
}
```

### Step 3: 移管元の編成を配列に収集

```squirrel
local arr = []
foreach(cnv in src_line.get_convoy_list()) { arr.append(cnv) }
if(arr.len() < transfer_n) return "移管元の編成が不足 (" + arr.len() + " < " + transfer_n + ")"
```

### Step 4: 各編成を移管し、最近接インデックスを設定

```squirrel
local moved = 0
foreach(cnv in arr) {
    if(moved >= transfer_n) break

    // (a) 現在地取得
    local pos = cnv.get_pos()

    // (b) 最近接インデックスを探す
    local best_idx = 0
    local best_dist = 999999999
    foreach(hp in halt_positions) {
        local dx = hp.x - pos.x
        local dy = hp.y - pos.y
        local d = dx*dx + dy*dy
        if(d < best_dist) { best_dist = d; best_idx = hp.idx }
    }

    // (c) 路線付け替え
    cnv.set_line(pl, dst_line)

    // (d) current を近いインデックスに更新（ライン所属は維持される）
    local sched = dst_line.get_schedule()
    sched.current = best_idx
    cnv.change_schedule(pl, sched)

    moved++
}
```

### Step 5: 結果確認

```squirrel
return "移管完了: " + moved + " 編成\n"
    + src_line.get_name() + ": " + src_line.get_convoy_list().get_count() + " 編成\n"
    + dst_line.get_name() + ": " + dst_line.get_convoy_list().get_count() + " 編成"
```

## 注意事項

- `convoy.get_pos()` が返す座標は `coord3d`（`.x`, `.y`, `.z`）。`halt_x.get_tile_list()[0]` の座標と同じ系。
- デポ待機中など位置が特殊な場合も `get_pos()` は有効な座標を返す（depot位置になる）。
- `change_schedule` の後に路線から外れていないかは `cnv.get_line()` で確認できる（任意）。
- 移管元に残す編成数は `/simutrans-convoy-count` で事前に算出しておくこと。
