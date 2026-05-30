---
name: simutrans-set-spacing
description: 路線の特定停留所エントリに発車間隔（spacing）と WAIT_FOR_TIME フラグを設定する。
argument-hint: "<路線名> <停留所名> <spacing値>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 発車間隔設定

引数: `$ARGUMENTS`（例: `和歌山北部バス 和歌山北端南停 36`）

路線の指定停留所エントリに `spacing` と `WAIT_FOR_TIME`（`flags | 16`）を設定する。

## 重要な注意事項

- **`sched.entries[N]` はコピーを返す。** プロパティを直接変更しても `change_schedule` に反映されない。必ず `entries.remove(N)` + `entries.insert(N, new_entry)` で置き換えること。
- **WAIT_FOR_TIME フラグは `1 << 4 = 16`**（64 ではない）。
- 停留所の座標は `entry.pos` では取得できない。`entry.get_halt(pl).get_tile_list()[0]` を使う。
- `change_schedule` の戻り値は非ネットワークモードで `true`（成功）。

## 手順

### Step 1: 路線と対象エントリを特定

```squirrel
local pl = player_x(0)
local line_kw = "路線名"   // $ARGUMENTS の第1引数
local halt_kw = "停留所名" // $ARGUMENTS の第2引数
local spacing_val = 36     // $ARGUMENTS の第3引数（整数）

local target = null
foreach(line in pl.get_line_list()) {
    if(line.get_name().find(line_kw) != null) { target = line; break }
}
if(target == null) return "路線が見つかりません: " + line_kw

local sched = target.get_schedule()
local result = "スケジュール一覧:\n"
local i = 0
foreach(entry in sched.entries) {
    local h = entry.get_halt(pl)
    local name = h.is_valid() ? h.get_name() : "?"
    local sp = ("spacing" in entry) ? entry.spacing : 1
    result += i + ": " + name + " flags=" + entry.flags + " spacing=" + sp + "\n"
    i++
}
return result
```

一覧を確認して対象インデックスを特定する。

### Step 2: エントリを置き換えて設定

対象インデックスが確定したら置き換えを実行する。

```squirrel
local pl = player_x(0)
local target = null
foreach(line in pl.get_line_list()) {
    if(line.get_name().find("路線名") != null) { target = line; break }
}

local sched = target.get_schedule()
local idx = N  // Step 1 で特定したインデックス
local old = sched.entries[idx]

// 座標を halt 経由で取得（entry.pos は動作しない）
local h = old.get_halt(pl)
local tiles = h.get_tile_list()
local pos = coord3d(tiles[0].x, tiles[0].y, tiles[0].z)

// 新エントリ: flags に WAIT_FOR_TIME (1<<4=16) を OR する
local new_entry = schedule_entry_x(pos, old.load, old.wait, old.flags | 16)
new_entry.spacing = spacing_val
if ("delay_tolerance" in old) new_entry.delay_tolerance = old.delay_tolerance
if ("maximum_load"   in old) new_entry.maximum_load    = old.maximum_load

// コピー問題回避: remove してから insert
sched.entries.remove(idx)
sched.entries.insert(idx, new_entry)
target.change_schedule(pl, sched)
```

### Step 3: 確認

```squirrel
local e = target.get_schedule().entries[idx]
local h = e.get_halt(pl)
return h.get_name() + " flags=" + e.flags + " spacing=" + e.spacing
// 期待: flags=16, spacing=spacing_val
```

期待値と一致すれば完了。
