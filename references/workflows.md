# 常见工作流

## A. 查作业状态

```bash
nanhu --cluster wuxi jobs list --job-type AI_TRAIN --status Running
nanhu --cluster wuxi jobs detail --job-id <jobId>
```

从 JSON 的 `data` 取 `uuid` / `jobId` / `status`。

## B. 创建训练作业（推荐闭环）

1. 查资源与算法镜像 UUID：

```bash
nanhu --cluster wuxi resources projects
nanhu --cluster wuxi resources specs
nanhu --cluster wuxi algorithms list --is-public false
nanhu --cluster wuxi images list --is-public false
nanhu --cluster wuxi images tags --repository-name <name> --source <source>
```

2. 复制 `examples/train_job.yaml`，填入真实 UUID；设置 `algorithm.mount_path`（常为 `/mnt/algorithm`）。
3. Dry-run 检查 payload：

```bash
nanhu --cluster wuxi jobs create-train --config job.yaml
```

4. 用户确认后提交：

```bash
nanhu --cluster wuxi jobs create-train --config job.yaml --submit
```

5. 从响应取 `jobId`，再查详情 / POD / 日志。

## C. 查 POD → 日志

```bash
nanhu --cluster x10000 pods list --job-id <id> --version v3
# 取出 podName 后：
nanhu --cluster x10000 logs get --job-id <id> --pod-names <podName>
nanhu --cluster x10000 logs download --job-id <id> --pod-names <podName> -o /tmp/out.log
```

无锡集群查日志时补 `--zone`。

## D. 停止 / 不变配重启

```bash
nanhu --cluster wuxi jobs stop --job-id <id>          # 预览
nanhu --cluster wuxi jobs stop --job-id <id> --submit
nanhu --cluster wuxi jobs restart --job-id <id> --submit
```

## E. 开发环境

```bash
# 编辑 examples/devenv.yaml 后
nanhu --cluster wuxi devenv create --config examples/devenv.yaml
nanhu --cluster wuxi devenv create --config examples/devenv.yaml --submit
nanhu --cluster wuxi devenv list
nanhu --cluster wuxi devenv save-image --job-id <id> --repository my/repo --tag v1 --submit
```

变配重启：YAML 含完整创建字段 + `uuid`（或 CLI `--uuid`）。

## F. Agent 约定

- 默认集群不明确时，先问用户 `wuxi` 还是 `x10000`。
- 任何 `--submit` 前必须展示 dry-run JSON 并得到确认。
- 不要把 `credentials.env`、token、密码写入仓库或聊天记录的可持久化附件。
