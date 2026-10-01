# 常见坑（来自 slime 南湖提交实践）

## 1. 作业名必须小写

南湖拒绝含大写、下划线等字符的名称。规则：

```text
^[a-z][a-z0-9.-]*$
```

错误示例：`Slime_Train`、`my_job`。正确：`slime-train-20260330`。

友好 YAML 可用 `name_prefix`；CLI 未传 `--name` 时会生成 `<prefix>-YYYYmmdd-HHMMSS`。

## 2. `algorithmMountPath` 别漏

创建训练时若算法代码挂载路径缺失，作业可能起不来或找不到入口。友好 YAML：

```yaml
algorithm:
  uuid: ...
  name: ...
  mount_path: /mnt/algorithm   # → algorithmMountPath
```

## 3. 私网地址必须绕过代理

`wuxi` / `x10000` 的 `api_base` 均为 `10.x` 私网。本客户端对私网主机强制直连（`ProxyHandler({})`），避免继承工作站 HTTP(S)_PROXY 导致网关 **405** 等异常。

若外层脚本自行用 `urllib`/`requests`，同样不要对私网走代理。

## 4. 写操作默认 dry-run

`stop` / `restart` / `restart-deploy` / `restart-pod` / `create-*` / `devenv create|restart|save-image` /
`algorithms create|update|delete|publish|unpublish|share|unshare` / `images share|unshare` /
`seahold create|destroy` **不加 `--submit` 不会发请求**，只打印：

```json
{"dry_run": true, "method": "...", "path": "...", "query": {...}, "body": {...}}
```

Agent 切勿把 dry-run 当成“已创建成功”。

## 5. 成功码兼容 `0` 与 `200`

平台响应 `code` 可能是 `0` / `"0"` / `200` / `"200"`。判断成功时不要只认其中一个。

## 6. 日志 `zone` 与本地 `run.log` 降级

`logs get` 必填 `zone`。`x10000` 集群会映射为 `X10000`；`wuxi` 当前无内置映射，必须显式 `--zone`。

`logs prefetch`（时间窗口统计）**不要求** zone。

**平台日志不可用时（wuxi 常见）：** 从 `jobs detail` 取 `OUTPUT_DIR`（envVars），读本地 **`$OUTPUT_DIR/run.log`** 尾部判断训练是否正常，不要反复盲试 zone。

## 7. `isPublic` 用小写

算法/镜像列表的 query 需要 `true`/`false`（小写）。CLI `--is-public true|false` 已规范化。

## 8. 凭据与密钥

- 只放 `config/credentials.env`（已 gitignore）或环境变量。
- 可按集群拆分 `credentials.wuxi.env` / `credentials.x10000.env`。
- Token 默认落盘 `~/.cache/nanhu/token.json`（可用 `NANHU_TOKEN_CACHE=0` 关闭）。
- **永远不要** commit 真实凭据、token 缓存或海纳 AK/SK。
- CLI 输出会脱敏 `sshPwd` / `jupyterPwd` 等；仍勿把明文密码贴进聊天附件。

## 9. V2 / V3 创建差异

- Train/Deploy V2 路径通常带 `bizType`；V3 默认不带（除非显式非默认 biz）。
- 不确定时先 dry-run，对照 `path`/`query` 再 `--submit`。

## 10. 集群能力差异（尤其 wuxi）

无锡（wuxi）上部分接口常 **404** 或失败，例如：`dev-env/list`、`images`、`jobListAll`、日志 `zone` 映射。
新接口（`pre_fetch`、`promotion/list`、算法写、镜像共享、海纳 PVC 等）同样可能仅在 x10000 / 文档集群可用。

CLI 失败时返回结构化 JSON（含 `error` / `type`，已知缺口会带 `hint`）；Skill 不要假装无锡已支持全部 OpenAPI。
查 running 作业请优先 `jobs running` 或 `jobs list --job-type ...`，不要依赖 wuxi 上的 `jobListAll`。

## 11. WebSocket 实时日志不做

Apifox 中的 WebSocket 日志订阅与 REST 不同，本仓库明确 **不实现**。需要实时流式日志时请用平台 UI 或其他客户端。

## 12. 海纳 PVC 销毁时机

失败开发环境 POD 可能保留现场约 7×24 小时；销毁私有数据集 PVC 建议在开发环境结束后至少 7 天（见平台文档）。

## 13. `--status` 大小写

平台筛选多为小写（`running`）。CLI 已规范化；文档与 Skill 示例统一写小写，避免写成 `Running` 却仍依赖服务端大小写敏感行为。
