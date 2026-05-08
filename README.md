# simutrans-agent-skills

[Claude Code](https://claude.ai/code) と [Simutrans MCP サーバ](https://github.com/akimuhirai/simutrans-busplay) を使って、Simutrans のゲーム内操作を自然言語で行うためのスキル集です。

## スキル一覧

| スキル | 説明 |
|---|---|
| `simutrans-find-halt` | 停留所名（部分一致）で座標を検索する |
| `simutrans-add-stop` | 往復路線に新しい停留所を挿入する |
| `simutrans-convoy-count` | 路線の必要編成数を所要時間から算出する |
| `simutrans-transfer-convoys` | 編成を別の路線へ付け替える |
| `simutrans-start-convoy` | 指定したデポの編成を出庫させる |
| `simutrans-gradual-start` | デポからの出庫を段階的に行う監視スクリプトを起動する |

## インストール

`skills/` ディレクトリを Claude Code のスキルディレクトリに配置（またはシンボリックリンク）してください。

```
.claude/skills -> /path/to/simutrans-agent-skills/skills
```
