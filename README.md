# simutrans-agent-skills

[Simutrans MCP サーバ](https://github.com/teamhimeh/simutrans/wiki/MCP-Server) を使って、Simutrans のゲーム内操作をAIエージェントに行わせるためのskill集です。

## スキル一覧

随時更新します。

| スキル | 説明 |
|---|---|
| `simutrans-find-halt` | 停留所名（部分一致）で座標を検索する |
| `simutrans-add-stop` | 往復路線に新しい停留所を挿入する |
| `simutrans-convoy-count` | 路線の必要編成数を所要時間から算出する |
| `simutrans-transfer-convoys` | 編成を別の路線へ付け替える |
| `simutrans-start-convoy` | 指定したデポの編成を出庫させる |
| `simutrans-gradual-start` | デポからの出庫を段階的に行う監視スクリプトを起動する |

## インストール

Claude Codeの場合: `skills/` ディレクトリを Claude Code のスキルディレクトリに配置（またはシンボリックリンク）してください。

```
.claude/skills -> /path/to/simutrans-agent-skills/skills
```
