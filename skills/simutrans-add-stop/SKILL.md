---
name: simutrans-add-stop
description: 往復路線に新しい停留所を正確に挿入する。往路・復路の両方に追加し、既存エントリのプロパティを毀損しない。
argument-hint: "<路線名> <停留所名> <直前の停留所名（往路）>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 路線停車追加

引数: `$ARGUMENTS`（例: `(2) 路線 草津東停 草津本町停`）

## 前提知識

- `line.change_schedule(pl, schedule)` の戻り値は **`true`（成功）**。`null` チェック不要。
- `schedule_entry_x(coord3d(x,y,z), load, wait, flags)` で新エントリ作成（整数直接渡し不可）
- エントリ削除は**後ろのインデックスから**行う
- `entry.get_halt(player_x(0))` はplayer引数必須

## 手順

### Step 1: 停留所の座標を特定

対象停留所が既存路線に含まれない場合、既知停留所の座標を基点に周辺を走査する。

**注意: ループ内で失敗する API（`e.pos` など）があると、スクリプト全体が "Call function failed" になる。原因はループ構文ではなくループ内の API 呼び出し。**

```squirrel
local pl = player_x(0)
// まず既知停留所（例: 路線上の隣接停留所）の座標を取得
local target_line = null
foreach(line in pl.get_line_list()) {
    if(line.get_name() == "路線名") { target_line = line; break }
}
local ref_halt = target_line.get_schedule().entries[N].get_halt(pl)
local ref_tiles = ref_halt.get_tile_list()  // h.get_tile_list() を使う（e.pos は動作しない）
local cx = ref_tiles[0].x
local cy = ref_tiles[0].y
local cz = ref_tiles[0].z

// ±50タイルを while ループで走査
local found_halts = {}
local dx = -50
while(dx <= 50) {
    local dy = -50
    while(dy <= 50) {
        try {
            local h = halt_x.get_halt(coord3d(cx+dx, cy+dy, cz), pl)
            if(typeof(h) == "instance") {
                local name = h.get_name()
                if(!(name in found_halts)) {
                    found_halts[name] <- true
                    if(name.find("検索名") != null) {
                        // 座標: cx+dx, cy+dy, cz
                    }
                }
            }
        } catch(e) {}
        dy++
    }
    dx++
}
```

### Step 2: 現在のスケジュール確認


```squirrel
local pl = player_x(0)
local target_line = null
foreach(line in pl.get_line_list()) {
    if(line.get_name() == "路線名") { target_line = line; break }
}
local schedule = target_line.get_schedule()
local n = schedule.entries.len()
local result = ""
local i = 0
while(i < n) {
    local e = schedule.entries[i]
    local h = e.get_halt(pl)
    local name = (typeof(h) == "instance") ? h.get_name() : "?"
    result += i + ": " + name + "\n"
    i++
}
```

### Step 3: 往路・復路への挿入

往路の「直前停留所」の次のインデックスに挿入。往路挿入後、復路のインデックスは+1ずれることに注意。

```squirrel
local ref = schedule.entries[往路インデックス]  // 隣接エントリからプロパティ参照
local new_entry = schedule_entry_x(coord3d(x, y, 0), ref.load, ref.wait, ref.flags)
if ("spacing" in ref) new_entry.spacing = ref.spacing
if ("delay_tolerance" in ref) new_entry.delay_tolerance = ref.delay_tolerance
if ("maximum_load" in ref) new_entry.maximum_load = ref.maximum_load

schedule.entries.insert(往路index, new_entry)
schedule.entries.insert(復路index, new_entry)  // 往路挿入後なので+1
target_line.change_schedule(pl, schedule)
```

### Step 4: 確認

変更後に `target_line.get_schedule().entries` を再取得して正しく挿入されたか確認。

## 注意事項

- スクリプトが複数回実行されると重複挿入される。**実行前に現在のスケジュールを確認**すること
- 削除操作が必要な場合は後ろのインデックスから `entries.remove(i)` を使う
- player_nr=0 で実行する
