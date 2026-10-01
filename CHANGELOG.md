# Changelog

## v1.1.0

相对 v1.0.0 的效率与回复格式优化：

- `docs(skill): 高频配方、回复模板与日志降级路径`
- `feat(cli): 为已知集群能力缺失补充错误提示`
- `feat(jobs): 新增 running 聚合查询并规范化 status`
- `feat(auth): 默认启用 Token 文件缓存`
- `feat(cli): JSON 默认紧凑并调小默认分页`
- `feat(cli): 支持 table 输出与列表字段投影脱敏`

要点：

- 全局 `--format table|json`；列表 table 投影固定字段；密码脱敏
- JSON 默认紧凑，`--pretty` 才缩进；列表默认 `page-size=20`
- Token 默认缓存 `~/.cache/nanhu/token.json`（可用环境变量关闭/改路径）
- `jobs running` 聚合 train+deploy；`--status` 规范化为小写
- 已知 wuxi 404 路径附加 `hint`
- Skill 高频配方、对人回复模板、`OUTPUT_DIR/run.log` 降级路径

## v1.0.0

基线：南湖 OpenAPI CLI + Cursor 双入口（nanhu / nanhu-cli）。

- 鉴权与私网 HTTP、wuxi/x10000 集群
- 作业/开发环境/POD/日志/资源/算法/镜像/海纳 PVC（REST）
- 写操作默认 dry-run；WebSocket 不在范围
