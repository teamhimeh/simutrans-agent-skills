---
name: simutrans-collect-cargo
description: 全路線の乗客カーゴデータ（乗車路線・次の乗換停留所・最終目的地・実人数）をSquirrelで収集し /tmp/simutrans_cargo.csv に保存する。simutrans-rank-transfers / simutrans-transfer-impact / simutrans-detect-backtrack の入力データとして使用。
argument-hint: "[max_convoys_per_line] (省略時: 30)"
allowed-tools: mcp__simutrans__run_squirrel, Bash(python3 *), Bash(wc *), Bash(date *)
---

# Simutrans 乗客データ収集

全路線の乗客カーゴを Squirrel で収集し `/tmp/simutrans_cargo.csv` に保存する。

## Step 1: max_convoys を決定

引数 `$ARGUMENTS` が整数なら使用、省略または非整数なら 30 を使う。

## Step 2: Squirrel でデータ収集

`get_amount()` で実人数を取得する。各 good_x は `ware_t` の1バッチを表し、`get_amount()` がそのバッチの実際の個数を返す。

```squirrel
local pl = player_x(0)
local lines = pl.get_line_list()
local demand = {}
local MAX = 30  // Step 1 で決めた値を使う

foreach(line in lines) {
  local lname = line.get_name()
  local convoys = line.get_convoy_list()
  local checked = 0
  foreach(convoy in convoys) {
    if (checked >= MAX) break
    try {
      local cargo = convoy.get_cargo()
      foreach(veh_cargo in cargo) {
        foreach(g in veh_cargo) {
          try {
            local transits = g.get_transit_halts()
            local dest = g.get_destination()
            if (!dest.is_valid()) continue
            local amt = g.get_amount()
            local dname = dest.get_name()
            local next = transits.len() >= 2 ? transits[0].get_name() : "DIRECT"
            local key = lname + "|" + next + "|" + dname
            if (!(key in demand)) demand[key] <- 0
            demand[key] += amt
          } catch(e) {}
        }
      }
    } catch(e) {}
    checked++
  }
}

local out = "line,next_halt,dest,amount\n"
foreach(k, v in demand) {
  local p = split(k, "|")
  out += p[0] + "," + p[1] + "," + p[2] + "," + v + "\n"
}
return out
```

player_nr=0 で実行する。

## Step 3: CSVファイルに保存

Squirrel の出力（CSV文字列）を Python で `/tmp/simutrans_cargo.csv` に書き込む。

```python
csv_data = """<squirrelの出力>"""
with open('/tmp/simutrans_cargo.csv', 'w', encoding='utf-8') as f:
    f.write(csv_data)
```

## Step 4: 完了確認

```bash
wc -l /tmp/simutrans_cargo.csv
date
```

行数・保存パス・収集日時を報告する。

## 注意事項

- `get_amount()` は `good_x` の `menge` フィールド（実旅客数）を返す
- `get_transit_halts()` の第1要素が次の乗換停留所、最後の要素が最終目的地と等しい
- ループ内の API 失敗は `try/catch` で握り潰す（`e.pos` など動作しない API がある）
- CSVのカンマ区切りは停留所名にカンマが含まれる可能性はほぼないが、含まれる場合はクォートが必要
