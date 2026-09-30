---
name: nanhu-skill
description: >-
  通过 nanhu CLI 操作南湖（Nanhu）调度：查询/创建/停止训练与部署作业、开发环境、
  POD/日志、规格与项目、算法与镜像。集群仅 wuxi / x10000。在用户提到南湖、
  Nanhu、无锡集群、x10000、提交训练作业、查 job 状态/日志时使用。
---

# 南湖调度助手（nanhu-skill）

用 **`nanhu` CLI** 调用南湖 OpenAPI。写操作默认 dry-run；加 `--submit` 才真正执行。
stdout 为 JSON，便于解析。

## 何时使用

- 查/建/停/重启训练或部署作业
- 开发环境 CRUD、保存镜像
- 查 POD、资源监控、任务日志
- 查计算规格、项目/子项目、算法、镜像（创建作业前置）

不要用本 skill 处理海纳数据集 PVC、WebSocket 实时日志、非 wuxi/x10000 集群。

## 前置条件

```bash
cd /path/to/nanhu-skill
pip install -e .
cp config/credentials.env.example config/credentials.env
# 填入 NANHU_APP_KEY / NANHU_APP_SECRET / NANHU_USER_ID
# 可选按集群：config/credentials.wuxi.env / credentials.x10000.env
```

Cursor Skill 安装（symlink）：

```bash
mkdir -p ~/.cursor/skills
ln -sfn /path/to/nanhu-skill ~/.cursor/skills/nanhu-skill
```

## 全局参数

| 参数 | 说明 |
|------|------|
| `--cluster {wuxi,x10000}` | 目标集群（默认 `wuxi`） |
| `--credentials PATH` | 凭据文件覆盖 |
| `--submit` | 写操作真正调用 API（默认 dry-run） |

凭据也可经环境变量：`NANHU_APP_KEY` / `NANHU_APP_SECRET` / `NANHU_USER_ID`（`NANHU_API_BASE` 可选覆盖 endpoint）。

## 命令速查

```bash
# 作业
nanhu --cluster wuxi jobs list --job-type AI_TRAIN
nanhu --cluster wuxi jobs detail --job-id <id>
nanhu --cluster wuxi jobs list-all
nanhu --cluster wuxi jobs stop --job-id <id>              # dry-run
nanhu --cluster wuxi jobs stop --job-id <id> --submit
nanhu --cluster wuxi jobs restart --job-id <id> --submit
nanhu --cluster wuxi jobs create-train --config examples/train_job.yaml
nanhu --cluster wuxi jobs create-train --config job.yaml --submit
nanhu --cluster wuxi jobs create-deploy --config deploy.yaml --version v3

# 开发环境
nanhu --cluster wuxi devenv list
nanhu --cluster wuxi devenv detail --job-id <id>
nanhu --cluster wuxi devenv create --config examples/devenv.yaml
nanhu --cluster wuxi devenv restart --config devenv.yaml --uuid <uuid> --submit
nanhu --cluster wuxi devenv save-image --job-id <id> --repository repo/a --tag v1 --submit

# POD / 监控
nanhu --cluster wuxi pods list --job-id <id> --version v3
nanhu --cluster wuxi pods list --job-id <id> --version v2
nanhu --cluster wuxi pods monitor --job-id <id>
nanhu --cluster wuxi pods monitor --job-id <id> --pod-names p0 --start <ts> --end <ts>

# 日志（x10000 可自动映射 zone；无锡请显式 --zone）
nanhu --cluster x10000 logs get --job-id <id> --pod-names <pod>
nanhu --cluster wuxi logs get --job-id <id> --pod-names <pod> --zone <ZONE>
nanhu --cluster wuxi logs download --job-id <id> --pod-names <pod> -o /tmp/job.log

# 资源 / 算法 / 镜像
nanhu --cluster wuxi resources specs
nanhu --cluster wuxi resources projects
nanhu --cluster wuxi resources sub-projects --project-id <id>
nanhu --cluster wuxi algorithms list --is-public false
nanhu --cluster wuxi algorithms get --uuid <uuid> --is-public false
nanhu --cluster wuxi images list --is-public false
nanhu --cluster wuxi images tags --repository-name <name> --source <source>
```

## Agent 工作流（推荐）

1. **读操作**：直接跑 CLI，解析 stdout JSON。
2. **写操作**：先不加 `--submit`，把 dry-run 的 `path`/`query`/`body` 展示给用户确认；确认后再加 `--submit`。
3. **创建训练**：先用 `resources` / `algorithms` / `images` 拿到真实 UUID，再填 YAML（参考 `examples/train_job.yaml`）。
4. **查日志**：先 `pods list` 拿 `podName`，再 `logs get`。
5. **失败**：若 stdout 含 `"error"`，检查凭据、集群、zone、作业名规则（见 `references/pitfalls.md`）。

## 详细参考

- API 路径与 CLI 映射：`references/api-map.md`
- 端到端流程：`references/workflows.md`
- 常见坑：`references/pitfalls.md`
