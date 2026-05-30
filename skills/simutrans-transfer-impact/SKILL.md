---
name: simutrans-transfer-impact
description: 新路線を設定した場合に既存路線から何人の旅客が転移するかを推定する。事前に simutrans-collect-cargo を実行しておくこと。
argument-hint: "<乗換点1>,<乗換点2>,... (新路線で直通化する乗換停留所名のカンマ区切り。例: 武蔵野停,和歌山 和歌山 農協倉庫前 停)"
allowed-tools: Bash(python3 *), Bash(test *)
---

# Simutrans 新路線転移効果推定

新路線が既存の乗換需要をどれだけ吸収できるかを推定する。

## 前提

新路線が「転移させる」旅客とは：
- 現在、引数で指定した乗換停留所で乗り換えを強いられている旅客
- かつ、最終目的地が新路線の停留所群に含まれている旅客

## Step 1: データ確認

```bash
test -f /tmp/simutrans_cargo.csv && echo "exists" || echo "missing"
```

ファイルが存在しない場合は `simutrans-collect-cargo` を先に実行するよう案内して終了する。

## Step 2: 引数の解釈

`$ARGUMENTS` をカンマで分割し、「転移対象の乗換停留所」リストを作る。

例：`武蔵野停,和歌山 和歌山 農協倉庫前 停` → 2箇所の乗換点

新路線が経由する停留所群は、現在ある路線のスケジュールから取得するか、ユーザーが別途提示している場合はそれを使う。  
**この停留所群を「新路線カバー停留所」と定義し、最終目的地がここに含まれる旅客が転移対象となる。**

停留所群が不明な場合は、乗換需要の行き先（`dest`列）の分布を出力して、ユーザーにどこまでカバーするかを確認する。

## Step 3: Python で転移量を計算

```python
import csv, io
from collections import defaultdict

TRANSFER_HALTS = set()  # Step 2 で特定した乗換停留所名を入れる
# 例: TRANSFER_HALTS = {"武蔵野停", "和歌山 和歌山 農協倉庫前 停", "和歌山停"}

NEW_ROUTE_STOPS = set()  # 新路線がカバーする停留所名を入れる

with open('/tmp/simutrans_cargo.csv', encoding='utf-8') as f:
    data = f.read()

total = 0
will_transfer = 0
by_line_total = defaultdict(int)
by_line_transfer = defaultdict(int)
dest_distribution = defaultdict(int)  # TRANSFER_HALTSでの乗換先の分布

reader = csv.DictReader(io.StringIO(data.strip()))
for row in reader:
    line = row['line']
    nxt = row['next_halt']
    dest = row['dest']
    amt = int(row['amount'])
    total += amt
    by_line_total[line] += amt
    if nxt in TRANSFER_HALTS:
        dest_distribution[dest] += amt
        if dest in NEW_ROUTE_STOPS:
            will_transfer += amt
            by_line_transfer[line] += amt

print(f"全旅客数: {total}人")
print(f"新路線へ転移: {will_transfer}人 ({will_transfer/total*100:.1f}%)")
print()
print(f"{'路線':<30} {'総旅客':>6} {'転移':>6} {'転移率':>7}")
print("-" * 55)
for line in sorted(by_line_total.keys()):
    tot = by_line_total[line]
    tr  = by_line_transfer.get(line, 0)
    pct = tr/tot*100 if tot > 0 else 0
    marker = " ★" if tr > 0 else ""
    print(f"{line:<30} {tot:>6} {tr:>6} {pct:>6.1f}%{marker}")

if not NEW_ROUTE_STOPS:
    print()
    print("=== 乗換地点での目的地分布（NEW_ROUTE_STOPS設定の参考に）===")
    for dest, amt in sorted(dest_distribution.items(), key=lambda x: -x[1])[:20]:
        print(f"  {amt:>5}人  {dest}")
```

## Step 4: 推奨編成数の計算

転移量が判明したら、新路線に必要な編成数の目安を計算する。

- 既存路線の編成数 × 転移率 × (新路線journey_time / 既存路線journey_time) を参考値とする
- journey_time の正確な値は `simutrans-convoy-count` スキルで計算する

## 注意事項

- 転移率はサンプリング（max_convoys_per_line 台）に基づく推定値
- フェリー港（明石港・益田港など）での乗換はフェリー待ちなので除外すること
- 新路線が設定されると既存路線の需要も変化するため、転移後の再計算が必要な場合がある
