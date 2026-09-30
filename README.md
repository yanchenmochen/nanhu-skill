# nanhu-skill

南湖（Nanhu）OpenAPI 的独立 Python CLI 客户端与 Cursor Skill。

当前支持集群：

- `wuxi` → `http://10.124.120.108:38080`
- `x10000` → `http://10.202.32.189:38080`

## 安装

```bash
cd /path/to/nanhu-skill
pip install -e ".[dev]"
```

安装后提供控制台命令 `nanhu`（见 `pyproject.toml` entry point）。

## 凭据

```bash
cp config/credentials.env.example config/credentials.env
# 填入：
#   NANHU_APP_KEY=
#   NANHU_APP_SECRET=
#   NANHU_USER_ID=
```

可选按集群拆分：

- `config/credentials.wuxi.env`
- `config/credentials.x10000.env`

也可用同名环境变量覆盖文件内容。`credentials.env` 已在 `.gitignore`，切勿提交。

## Cursor Skill 安装

把本仓库 symlink 到 Cursor skills 目录：

```bash
mkdir -p ~/.cursor/skills
ln -sfn "$(pwd)" ~/.cursor/skills/nanhu-skill
```

文档入口：`SKILL.md`；细节见 `references/`。

## CLI 快速示例

```bash
# 默认 dry-run；stdout 为 JSON
nanhu --cluster wuxi jobs list --job-type AI_TRAIN
nanhu --cluster wuxi jobs create-train --config examples/train_job.yaml
nanhu --cluster wuxi jobs create-train --config examples/train_job.yaml --submit

nanhu --cluster x10000 pods list --job-id <id> --version v3
nanhu --cluster x10000 logs get --job-id <id> --pod-names <pod>
```

命令全集见 `SKILL.md`。

## 开发与测试

```bash
pytest
```

单测 mock HTTP / API，不联调真实集群。

## 布局

- `src/nanhu/` — config / http / auth / client / api / cli
- `config/` — 集群与凭据模板
- `examples/` — 训练作业 / 开发环境 YAML 示例
- `references/` — API 映射、工作流、坑点
- `tests/` — 单测
- `SKILL.md` — Cursor Agent 使用说明
