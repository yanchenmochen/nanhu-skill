# 常见工作流

`nanhu` 与 `nanhu-cli` 命令等价，下文统一写 `nanhu`。

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
nanhu --cluster wuxi resources promotions --project-id <projectId>
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
nanhu --cluster x10000 logs prefetch --job-id <id> --pod-names <podName> --step 10
nanhu --cluster x10000 logs download --job-id <id> --pod-names <podName> -o /tmp/out.log
```

无锡集群查日志（`logs get`）时补 `--zone`。`logs prefetch` 不要求 zone。

## D. 停止 / 重启

```bash
nanhu --cluster wuxi jobs stop --job-id <id>          # 预览
nanhu --cluster wuxi jobs stop --job-id <id> --submit
nanhu --cluster wuxi jobs restart --job-id <id> --submit   # 不变配
```

部署变配重启（保持 jobId）：

```bash
nanhu --cluster wuxi jobs restart-deploy --config deploy.yaml   # 含 uuid
nanhu --cluster wuxi jobs restart-deploy --config deploy.yaml --submit
```

失败 POD 重启：

```bash
nanhu --cluster wuxi jobs restart-pod --job-id <id> --pod-names a,b
nanhu --cluster wuxi jobs restart-pod --job-id <id> --pod-names a,b --submit
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

## F. 算法 / 镜像写操作与共享

```bash
nanhu --cluster wuxi algorithms create --config algo.yaml
nanhu --cluster wuxi algorithms update --config algo.yaml --uuid <uuid>
nanhu --cluster wuxi algorithms publish --uuid <uuid> --submit
nanhu --cluster wuxi algorithms share --uuid <uuid> --user-name 001254 --submit
nanhu --cluster wuxi images share --uuid <id> --source z1120 --user-name 002084 --submit
```

## G. 海纳数据集 PVC

```bash
nanhu --cluster x10000 seahold list
nanhu --cluster x10000 seahold create --config seahold.yaml
nanhu --cluster x10000 seahold destroy --uuid <uuid> --ak <ak> --sk <sk> --submit
```

失败开发环境销毁 PVC 建议在作业结束后至少 7 天（见平台说明）。

## H. Agent 约定

- 默认集群不明确时，先问用户 `wuxi` 还是 `x10000`。
- 任何 `--submit` 前必须展示 dry-run JSON 并得到确认。
- 不要把 `credentials.env`、token、密码、海纳 AK/SK 写入仓库或聊天记录的可持久化附件。
- WebSocket 实时日志不在本 Skill 范围内。
