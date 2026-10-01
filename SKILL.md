---
name: nanhu-skill
description: >-
  通过 nanhu / nanhu-cli 操作南湖（Nanhu）调度：查询/创建/停止训练与部署作业、开发环境、
  POD/日志、规格与项目、算法与镜像。集群仅 wuxi / x10000。在用户提到南湖、
  Nanhu、nanhu-cli、/nanhu-cli、南湖 CLI、无锡集群、x10000、提交训练作业、查 job 状态/日志时使用。
---

# 南湖调度助手（nanhu-skill / nanhu-cli）

用 **`nanhu` 或 `nanhu-cli`**（等价）调南湖 OpenAPI。写操作默认 dry-run；加 `--submit` 才执行。
默认 stdout 为**紧凑 JSON**（密码已脱敏）；对人展示列表时加 `--format table`。

## 何时使用

- 查/建/停/重启训练或部署（含变配、失败 POD 重启）
- 开发环境、POD/监控、日志、规格/项目、算法/镜像、海纳 PVC
- 不要处理 WebSocket 实时日志、非 wuxi/x10000 集群

## 前置条件

```bash
cd /path/to/nanhu-skill && pip install -e .
cp config/credentials.env.example config/credentials.env   # 填 KEY/SECRET/USER_ID
mkdir -p ~/.cursor/skills
ln -sfn /path/to/nanhu-skill ~/.cursor/skills/nanhu-skill
ln -sfn /path/to/nanhu-skill ~/.cursor/skills/nanhu-cli
```

全局常用：`--cluster {wuxi,x10000}`（默认 wuxi）、`--format table|json`、`--pretty`、`--submit`。
Token 默认缓存 `~/.cache/nanhu/token.json`（`NANHU_TOKEN_CACHE=0` 可关闭）。

## 高频配方（优先用这些，勿再套 python -c 做表）

```bash
# 运行中作业（训练+部署一次拉齐）
nanhu --cluster wuxi --format table jobs running

# 仅训练 / 仅部署 running
nanhu --cluster wuxi --format table jobs list --job-type AI_TRAIN --status running
nanhu --cluster wuxi --format table jobs list --job-type AI_ONLINE_INFERENCE_SERVICE --status running

# 详情 / 停作业
nanhu --cluster wuxi jobs detail --job-id <id>
nanhu --cluster wuxi jobs stop --job-id <id>            # dry-run
nanhu --cluster wuxi jobs stop --job-id <id> --submit

# POD → 日志（x10000 可自动 zone；wuxi 需 --zone 或走本地降级）
nanhu --cluster x10000 pods list --job-id <id>
nanhu --cluster x10000 logs get --job-id <id> --pod-names <pod>

# 创建训练
nanhu --cluster wuxi jobs create-train --config job.yaml
nanhu --cluster wuxi jobs create-train --config job.yaml --submit
```

完整命令表见 `references/api-map.md`；端到端流程见 `references/workflows.md`。

## 对人回复模板（必须遵守）

**列表类：** 用 markdown 表，列优先 `状态 | 名称 | jobId | 时长 | 规格 | 创建时间`。无数据时明确写「当前无 …」。不要把整页 JSON 贴给用户。

```markdown
### 无锡 · 运行中作业（N）
| # | 状态 | 名称 | jobId | 时长 | 规格 |
|---|------|------|-------|------|------|
| 1 | running | ... | jb-... | ... | ... |
```

**写操作类：** 先展示 dry-run 摘要（method / path / 关键字段），用户确认后再 `--submit`。成功只回 `jobId` / `status` 等关键字段。

**排障类：** 平台 `logs get` 失败时，从 `jobs detail` 的 env（如 `OUTPUT_DIR`）读取本地 `OUTPUT_DIR/run.log` 尾部，不要空转试 zone。

## Agent 约定

1. 读操作直接跑 CLI；列表对人用 `--format table`。
2. 写操作必须先 dry-run 确认再 `--submit`。
3. `--status` 用小写（`running`）；CLI 会规范化大小写。
4. 失败若含 `hint`，优先按 hint 行动（见 `references/pitfalls.md`）。

## 详细参考

- API / CLI 映射：`references/api-map.md`
- 工作流（含日志降级）：`references/workflows.md`
- 常见坑：`references/pitfalls.md`
