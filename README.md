# nanhu-skill

南湖（Nanhu）OpenAPI 的独立 Python CLI 客户端与 Cursor Skill。

当前支持集群：

- `wuxi` → `http://10.124.120.108:38080`
- `x10000` → `http://10.202.32.189:38080`

## 快速开始

```bash
pip install -e ".[dev]"
cp config/credentials.env.example config/credentials.env
# 填入 NANHU_APP_KEY / NANHU_APP_SECRET / NANHU_USER_ID
```

## 开发

```bash
pytest
```

## 布局

- `src/nanhu/` — 客户端核心（config / http / auth / api）
- `config/` — 集群与凭据模板
- `tests/` — 单测（mock HTTP，不联调真实集群）
