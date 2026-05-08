---
name: simutrans-convoy-count
description: 路線の必要編成数を journey_time と発車間隔（spacing）から時間ベースで算出する。
argument-hint: "<路線名（部分一致OK）>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 必要編成数算出

引数 `$ARGUMENTS` で指定された路線名（部分一致）の必要編成数を、スケジュールの所要時間と発車間隔から計算する。

## アルゴリズム

```
必要編成数 = ceil(往復所要時間 / ヘッドウェイ)
ヘッドウェイ    = ticks_per_month / min_spacing
往復所要時間    = 全エントリの journey_time[0] の合計
min_spacing     = 発車時刻が設定されているエントリのうち spacing の最小値
```

**なぜ最小 spacing か:** spacing が複数のエントリに設定されている場合、大きい値は短距離折り返し便など特殊な発車で、最小値が「全区間を通しで走る本数」を表す。必要編成数は最も少ない全区間便の頻度で決まる。

**発車時刻が設定されているエントリの見分け方:** `entry.spacing > 1` または `entry.flags & 64 != 0` のどちらかで判定できる（両方を使うと確実）。

## 手順

### Step 1: 対象路線を特定

```squirrel
local pl = player_x(0)
local keyword = "$ARGUMENTS"
local lines = pl.get_line_list()
local target = null
foreach(line in lines) {
    if(line.get_name().find(keyword) != null) { target = line; break }
}
if(target == null) return "路線が見つかりません: " + keyword
```

### Step 2: ticks_per_month を取得

```squirrel
local tpm = world.get_time().ticks_per_month  // 例: 2097152
```

### Step 3: 往復所要時間を集計

```squirrel
local sched = target.get_schedule()
local total_ticks = 0
foreach(entry in sched.entries) {
    local jt = entry.journey_time
    if(typeof(jt) == "array" && jt.len() > 0) total_ticks += jt[0]
}
```

**注意:** `journey_time[0]` は最新の実績値。0 のエントリはまだ走っていない区間（新設路線など）。全エントリが 0 の場合は実績なしで計算不能。

### Step 4: 発車間隔（ヘッドウェイ）を算出

```squirrel
local min_spacing = -1
foreach(entry in sched.entries) {
    if("spacing" in entry && entry.spacing > 1) {
        if(min_spacing < 0 || entry.spacing < min_spacing) {
            min_spacing = entry.spacing
        }
    }
}

if(min_spacing < 0) {
    // 発車時刻設定なし → 既存編成数から逆算
    local current_n = target.get_convoy_list().get_count()
    return "発車時刻未設定。現在の編成数: " + current_n + ", 往復=" + total_ticks + " ticks"
}

local headway = tpm / min_spacing  // ticks
```

### Step 5: 必要編成数を計算して返す

```squirrel
local required = ((total_ticks.tofloat() / headway.tofloat()) + 0.999).tointeger()
local current = target.get_convoy_list().get_count()
return target.get_name() + "\n"
    + "  往復所要時間: " + total_ticks + " ticks\n"
    + "  min_spacing: " + min_spacing + " 本/月 → ヘッドウェイ: " + headway + " ticks\n"
    + "  必要編成数: " + required + " 編成\n"
    + "  現在の編成数: " + current + " 編成 (差分: " + (required - current) + ")"
```

## 複数路線を比較する場合

`$ARGUMENTS` にカンマ区切りで路線名を渡し、foreach でループして各路線の結果をまとめて返す。

## 注意事項

- `entry.pos` は動作しない。座標が必要な場合は `entry.get_halt(pl).get_tile_list()[0]` を使う
- `journey_time` は `create_slot` のデフォルトが 0 の配列。新設エントリは 0 になる
- `world.get_time()` はテーブルなので `world.get_time().ticks_per_month` でアクセス（`world()` はエラー）
