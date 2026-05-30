---
name: simutrans-detect-backtrack
description: 特定の乗換停留所で、来た方向と逆に折り返す「V字経路」旅客を検出する。帯広BTで松本方面に折り返すような非効率なルーティングを発見し、直通路線の需要根拠とする。事前に simutrans-collect-cargo を実行しておくこと。
argument-hint: "<乗換停留所名（部分一致OK）> [目的地キーワード（省略時は全目的地を表示）]"
allowed-tools: mcp__simutrans__run_squirrel, Bash(python3 *), Bash(test *)
---

# Simutrans V字経路（折り返し）旅客の検出

特定の乗換停留所に集まる旅客のうち、「そこを経由しなくても行けるはずの目的地」に向かっている旅客を検出する。

## V字経路とは

例：所沢から松本に行く旅客が、現状ルートでは  
`所沢 → (路線5) → 帯広BT → (路線2) → 松本`  
という遠回りをしている場合。  
帯広BT は終点（東端）なのに、そこから逆方向（西側）の松本に向かうのは非効率。  
直通の「所沢-松本線」があればこの迂回が解消できる。

## Step 1: データ確認

```bash
test -f /tmp/simutrans_cargo.csv && echo "exists" || echo "missing"
```

ファイルが存在しない場合は `simutrans-collect-cargo` を先に実行するよう案内して終了する。

## Step 2: 引数の解釈

`$ARGUMENTS` をスペースで分割する：
- 第1トークン: 乗換停留所名（部分一致）
- 第2トークン以降: 目的地フィルタキーワード（省略可）

例: `帯広バスターミナル 松本` → 帯広BTで、松本を含む目的地への旅客を検出

## Step 3: 対象乗換点を確定

引数の停留所名（部分一致）でCSVの `next_halt` 列を検索し、一致する停留所名の全候補を列挙する。
複数候補がある場合はユーザーに確認する。

## Step 4: 乗車路線ごとの「どこから来てどこへ行くか」を分析

```python
import csv, io
from collections import defaultdict

HUB_KEYWORD = "帯広バスターミナル"  # Step 2 で決めた停留所名（完全一致または部分一致）
DEST_FILTER = ""                     # 目的地フィルタ（空なら全目的地）

with open('/tmp/simutrans_cargo.csv', encoding='utf-8') as f:
    data = f.read()

# ハブ経由の旅客を抽出
hub_passengers = []  # (line, dest, amount)
reader = csv.DictReader(io.StringIO(data.strip()))
for row in reader:
    if HUB_KEYWORD in row['next_halt']:
        if not DEST_FILTER or DEST_FILTER in row['dest']:
            hub_passengers.append((row['line'], row['dest'], int(row['amount'])))

# 路線別・目的地別に集計
by_line = defaultdict(int)
by_dest_area = defaultdict(int)
by_line_dest = defaultdict(lambda: defaultdict(int))

for line, dest, amt in hub_passengers:
    by_line[line] += amt
    # 目的地エリア（最初の地名）
    area = dest.split()[0]
    by_dest_area[area] += amt
    by_line_dest[line][area] += amt

total = sum(by_line.values())

print(f"=== {HUB_KEYWORD} 経由の旅客 ===")
print(f"総計: {total}人")
print()

print("乗車路線別:")
for line, amt in sorted(by_line.items(), key=lambda x: -x[1]):
    print(f"  {line}: {amt}人")

print()
print("目的地エリア別（上位15件）:")
for area, amt in sorted(by_dest_area.items(), key=lambda x: -x[1])[:15]:
    print(f"  {area:10}: {amt:>5}人")

print()
print("路線×目的地エリア クロス集計（上位）:")
for line, dest_map in sorted(by_line_dest.items(), key=lambda x: -sum(x[1].values())):
    line_total = sum(dest_map.values())
    top_dests = sorted(dest_map.items(), key=lambda x: -x[1])[:5]
    dest_str = ", ".join(f"{a}({n})" for a, n in top_dests)
    print(f"  {line}: {line_total}人 → {dest_str}")
```

## Step 5: V字経路の判定と提言

出力結果を見て以下を判断する：

1. **V字経路の証拠**: ハブ到着路線と目的地の方向性が逆の場合（例：東方向から来て西方向の目的地へ）
2. **迂回距離の推定**: 経由しなくて済む停留所数・距離を路線スケジュールから確認
3. **直通路線の提案**: V字解消に有効な新路線を具体的に提案

**参考質問**:
- そのハブに到着する路線の出発地（始発停留所）はどこか？
- 目的地と出発地の間に既存の直通路線はあるか？
- 直通路線を設定した場合の転移量は？ → `simutrans-transfer-impact` で確認

## 注意事項

- フェリー港（明石港・益田港など）は V字経路でなく正常なモード乗り換えのため除外する
- 同じ路線が往復で同じハブを通る場合、往路と復路の需要を混同しないよう注意
- V字かどうかは地理的配置（路線スケジュールの停留所順）を確認して判断する
