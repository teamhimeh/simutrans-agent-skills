---
name: simutrans-find-halt
description: 停留所名（部分一致）でゲーム内の停留所を検索し、座標・所有プレイヤーを返す。
argument-hint: "<停留所名（部分一致OK）>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 停留所検索

引数 `$ARGUMENTS` で指定された名前（部分一致）に一致する停留所を探す。

## 手順

### Step 1: 既存路線のスケジュールから検索

```squirrel
local pl = player_x(0)
local keyword = "$ARGUMENTS"
local found = {}
local result = ""

local lines = pl.get_line_list()
foreach(line in lines) {
    local entries = line.get_schedule().entries
    foreach(entry in entries) {
        try {
            local h = entry.get_halt(pl)
            if(typeof(h) == "instance") {
                local name = h.get_name()
                if(name.find(keyword) != null && !(name in found)) {
                    found[name] <- true
                    local tiles = h.get_tile_list()
                    if(tiles.len() > 0) {
                        local t = tiles[0]
                        result += name + " (" + t.x + "," + t.y + "," + t.z + ")\n"
                    }
                }
            }
        } catch(e) {}
    }
}
return result == "" ? null : result
```

### Step 2: 見つからない場合は座標スキャン

既存路線に含まれない新規停留所は Step 1 で見つからない。その場合、近隣の既知停留所を基点に `halt_x.get_halt` で走査する。

**注意: ループ内で失敗する API があると全体が "Call function failed" になる。原因特定のためループを分割してデバッグすること。**

```squirrel
// 基点停留所の座標を get_tile_list() で取得（e.pos は動作しない）
local ref_halt = schedule.entries[N].get_halt(pl)
local t0 = ref_halt.get_tile_list()[0]
local cx = t0.x
local cy = t0.y
local cz = t0.z

local found = {}
local result = ""
local dx = -50
while(dx <= 50) {
    local dy = -50
    while(dy <= 50) {
        try {
            local h = halt_x.get_halt(coord3d(cx+dx, cy+dy, cz), pl)
            if(typeof(h) == "instance") {
                local name = h.get_name()
                if(!(name in found)) {
                    found[name] <- true
                    if(name.find(keyword) != null) {
                        result += name + " (" + (cx+dx) + "," + (cy+dy) + "," + cz + ")\n"
                    }
                }
            }
        } catch(e) {}
        dy++
    }
    dx++
}
return result == "" ? "not found" : result
```

## 注意

- `entry.get_halt(player_x(0))` はプレイヤー引数が必須
- 座標取得は `h.get_tile_list()[0].x/y/z` を使う（`e.pos` は動作しない）
- "Call function failed" はループ構文でなくループ内の API 失敗（`e.pos` など）が原因

## 実行

mcp__simutrans__run_squirrel でコードを実行し、結果を整形して返す。player_nr=0 を使う。
