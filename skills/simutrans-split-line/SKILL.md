---
name: simutrans-split-line
description: 既存の長大路線を指定したインデックスで2つに分割し、全車両を進行方向を完全に維持したまま各新路線に自動で振り分ける。
argument-hint: "<分割元路線名> <往路の境界インデックス>"
allowed-tools: mcp__simutrans__run_squirrel
---

# Simutrans 路線分割 (simutrans-split-line)

引数 `$ARGUMENTS` を `"<路線名> <往路の境界インデックス>"` の形式で受け取り、路線を「A路線（始点〜境界）」と「B路線（境界〜終点）」に安全に分割します。

既存の `simutrans-transfer-convoys` では距離計算を用いてインデックスを推定するため、往復路線のように同じ座標を2回通る場合にUターンバグが発生します。本スキルは元のインデックスからの1対1数学的マッピングを行うため、**進行方向が逆転するバグが絶対に発生しません**。

## 実装手順

### Step 1: パラメータのパース

引数文字列から路線名と境界インデックスを取得し、Squirrelコードに埋め込むか、以下のスクリプト先頭でパースします。

### Step 2: 分割スクリプトの実行

以下のSquirrelコードを実行します（`$ARGUMENTS` はエージェント側で置換または処理してください）。

```squirrel
local pl = player_x(0);
// 例: arg = "(1) 13" のような形式をパース
local arg = "$ARGUMENTS";
local parts = [];
local current_str = "";
for(local i=0; i<arg.len(); i++) {
    if(arg[i] == ' ') {
        if(current_str != "") parts.append(current_str);
        current_str = "";
    } else {
        current_str += arg[i].tochar();
    }
}
if(current_str != "") parts.append(current_str);

if(parts.len() < 2) return "Usage: <LineName> <BoundaryIndex>";
local boundary_idx = parts[parts.len()-1].tointeger();
local target_line_name = arg.slice(0, arg.len() - parts[parts.len()-1].len() - 1);

local orig_line = null;
foreach(ln in pl.get_line_list()) {
    if(ln.get_name().find(target_line_name) != null) {
        orig_line = ln;
        break;
    }
}
if(!orig_line) return "Line not found: " + target_line_name;

local orig_sched = orig_line.get_schedule();
local orig_entries = orig_sched.entries;
local total_len = orig_entries.len();

// 復路の境界インデックスを座標から自動検索
local b_entry = orig_entries[boundary_idx];
local return_idx = -1;
for(local i = boundary_idx + 1; i < total_len; i++) {
    local e = orig_entries[i];
    if(e.x == b_entry.x && e.y == b_entry.y && e.z == b_entry.z) {
        return_idx = i;
        break;
    }
}
if(return_idx == -1) return "Error: Return boundary not found (Not a loop schedule?)";

// 元のspacing（発車間隔）を保存
local orig_spacing = ("spacing" in orig_entries[0]) ? orig_entries[0].spacing : 0;

// === A路線の作成 ===
local entries_A = [];
for(local i=0; i<=boundary_idx; i++) entries_A.append(orig_entries[i]);
for(local i=return_idx+1; i<total_len; i++) entries_A.append(orig_entries[i]);
if(entries_A.len() > 0 && orig_spacing > 0) entries_A[0].spacing = orig_spacing;

pl.create_line(orig_sched.waytype);
local lines = pl.get_line_list();
local line_A = lines[lines.get_count()-1];
local sched_A = line_A.get_schedule();
sched_A.entries = entries_A;
line_A.change_schedule(pl, sched_A);
line_A.set_name(orig_line.get_name() + "_A");

// === B路線の作成 ===
local entries_B = [];
for(local i=boundary_idx; i<return_idx; i++) entries_B.append(orig_entries[i]);
if(entries_B.len() > 0 && orig_spacing > 0) entries_B[0].spacing = orig_spacing;

pl.create_line(orig_sched.waytype);
lines = pl.get_line_list();
local line_B = lines[lines.get_count()-1];
local sched_B = line_B.get_schedule();
sched_B.entries = entries_B;
line_B.change_schedule(pl, sched_B);
line_B.set_name(orig_line.get_name() + "_B");

// === 車両のインデックス完全維持マッピング ===
local convoys = [];
foreach(cnv in orig_line.get_convoy_list()) convoys.append(cnv);

local moved_A = 0;
local moved_B = 0;

foreach(cnv in convoys) {
    local orig_curr = cnv.get_schedule().current;
    
    if(orig_curr <= boundary_idx || orig_curr > return_idx) {
        // Line A に所属
        cnv.set_line(pl, line_A);
        local sched = line_A.get_schedule();
        if(orig_curr <= boundary_idx) {
            sched.current = orig_curr;
        } else {
            sched.current = orig_curr - (return_idx + 1) + (boundary_idx + 1);
        }
        cnv.change_schedule(pl, sched);
        moved_A++;
    } else {
        // Line B に所属 (orig_curr は boundary_idx + 1 から return_idx の間)
        cnv.set_line(pl, line_B);
        local sched = line_B.get_schedule();
        if(orig_curr >= boundary_idx + 1 && orig_curr < return_idx) {
            sched.current = orig_curr - boundary_idx;
        } else if(orig_curr == return_idx) {
            // 復路で境界に戻ってきた車両は、B路線のスタート地点 (index 0) へ
            sched.current = 0;
        }
        cnv.change_schedule(pl, sched);
        moved_B++;
    }
}

return "Split successful!\nLine A (" + line_A.get_name() + "): " + moved_A + " convoys\nLine B (" + line_B.get_name() + "): " + moved_B + " convoys\nOriginal Line is now empty.";
```

### Step 3: 確認事項

実行後、結果として `Line A convoys: 25`, `Line B convoys: 27` のように自然分配された車両数が返されます。
この結果が、それぞれの路線の所要時間に対して適切な配分となっているか、必要に応じて `/simutrans-convoy-count` と連携してユーザーに報告してください。
元の路線は所属車両ゼロとなるため、ユーザーに手動削除を促してください。
