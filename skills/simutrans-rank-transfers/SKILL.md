---
name: simutrans-rank-transfers
description: 乗換需要の多い停留所をランキングし、接続が欠落している箇所（新路線で直通化できる候補）を特定する。事前に simutrans-collect-cargo を実行しておくこと。
argument-hint: "[top_n] (省略時: 15)"
allowed-tools: mcp__simutrans__run_squirrel, Bash(python3 *), Bash(test *), Bash(ls *)
---

# Simutrans 乗換停留所ランキング

乗換需要の多い停留所を実人数でランキングし、路線設定が不十分な箇所を発見する。

## Step 1: データ確認

```bash
test -f /tmp/simutrans_cargo.csv && echo "exists" || echo "missing"
```

ファイルが存在しない場合は `simutrans-collect-cargo` スキルを先に実行するよう案内して終了する。

## Step 2: Python で集計

top_n は `$ARGUMENTS` が整数なら使用、省略時は 15。

```python
import csv, io
from collections import defaultdict

with open('/tmp/simutrans_cargo.csv', encoding='utf-8') as f:
    data = f.read()

# 乗換停留所ごとの総旅客数
by_transfer = defaultdict(int)   # next_halt -> amount合計
by_line_total = defaultdict(int) # line -> total amount

reader = csv.DictReader(io.StringIO(data.strip()))
for row in reader:
    amt = int(row['amount'])
    nxt = row['next_halt']
    line = row['line']
    by_line_total[line] += amt
    if nxt != 'DIRECT':
        by_transfer[nxt] += amt

top_n = 15  # $ARGUMENTS を整数に変換して使う

print(f"=== 乗換停留所ランキング TOP {top_n} ===")
print(f"{'人数':>6}  停留所名")
print("-" * 50)
for name, amt in sorted(by_transfer.items(), key=lambda x: -x[1])[:top_n]:
    print(f"{amt:>6}人  {name}")

print()
print("=== 路線別 総旅客数 ===")
print(f"{'路線':<30} {'合計':>6}")
print("-" * 40)
for line, amt in sorted(by_line_total.items(), key=lambda x: -x[1]):
    print(f"{line:<30} {amt:>6}人")
```

## Step 3: 結果の解釈

Python の出力を整形してユーザーに提示する。

各乗換停留所について以下を判定し注記する：
- **フェリー港**（明石港・益田港など「港」を含む停留所）：⚓ 船便の待ち客であり欠落ではない
- **既存接続あり**：その停留所を経由する路線が複数あり乗り換えが機能している → ✅
- **接続が薄い/欠落の可能性**：1路線しか通っていないのに乗換需要が多い → ⚠️

接続状況を判定するには Squirrel でその停留所を通過する路線数を確認する：

```squirrel
local pl = player_x(0)
local target = "停留所名"  // 上位停留所に合わせて変える
local lines = pl.get_line_list()
local count = 0
foreach(line in lines) {
  local sched = line.get_schedule()
  foreach(e in sched.entries) {
    try {
      local h = e.get_halt(pl)
      if (typeof(h)=="instance" && h.is_valid() && h.get_name() == target) {
        count++
        break
      }
    } catch(e2) {}
  }
}
return target + ": " + count + " 路線が通過"
```

## Step 4: 新路線候補の提言

乗換需要が多く、接続が薄い停留所の組み合わせから「直通にすると恩恵が大きい路線」を提案する。

典型的な発見パターン：
- A↔Bで乗換が多い → A-B直通線
- ある停留所で多くの旅客が「逆向き」に折り返している → V字経路の解消（`simutrans-detect-backtrack` で詳細調査）
- 乗換需要が特定のODペアに集中 → `simutrans-transfer-impact` で転移率を試算
