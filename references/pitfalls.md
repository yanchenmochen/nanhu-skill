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

`stop` / `restart` / `create-*` / `devenv create|restart|save-image` **不加 `--submit` 不会发请求**，只打印：

```json
{"dry_run": true, "method": "...", "path": "...", "query": {...}, "body": {...}}
```

Agent 切勿把 dry-run 当成“已创建成功”。

## 5. 成功码兼容 `0` 与 `200`

平台响应 `code` 可能是 `0` / `"0"` / `200` / `"200"`。判断成功时不要只认其中一个。

## 6. 日志 `zone` header

`logs get` 必填 `zone`。`x10000` 集群会映射为 `X10000`；`wuxi` 当前无内置映射，必须显式 `--zone`。

## 7. `isPublic` 用小写

算法/镜像列表的 query 需要 `true`/`false`（小写）。CLI `--is-public true|false` 已规范化。

## 8. 凭据与密钥

- 只放 `config/credentials.env`（已 gitignore）或环境变量。
- 可按集群拆分 `credentials.wuxi.env` / `credentials.x10000.env`。
- **永远不要** commit 真实凭据或 token 缓存。

## 9. V2 / V3 创建差异

- Train/Deploy V2 路径通常带 `bizType`；V3 默认不带（除非显式非默认 biz）。
- 不确定时先 dry-run，对照 `path`/`query` 再 `--submit`。
