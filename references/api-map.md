# API ↔ CLI 映射

集群 endpoint（`config/clusters.yaml`）：

| cluster | api_base |
|---------|----------|
| wuxi | `http://10.124.120.108:38080` |
| x10000 | `http://10.202.32.189:38080` |

鉴权：`POST /api/open/credentials` → header `accessToken`；查询普遍带 `userId`。

CLI 入口：`nanhu` 与 `nanhu-cli` 等价（同一 `nanhu.cli:main`）。

## jobs

| CLI | Method | Path |
|-----|--------|------|
| `jobs list` | GET | `/api/open/dros-ic-platform/open-job/jobList` |
| `jobs detail` | GET | `.../getJobDetail` |
| `jobs list-all` | GET | `.../jobListAll` |
| `jobs stop` | PUT | `.../stop` |
| `jobs restart` | POST | `.../restart` |
| `jobs restart-deploy` | POST | `.../restartInferenceJob` |
| `jobs restart-pod` | POST | `.../podRestart` |
| `jobs create-train` v2 | POST | `.../create` |
| `jobs create-train` v3 | POST | `.../v3/create` |
| `jobs create-deploy` v2 | POST | `.../createInferenceJob` |
| `jobs create-deploy` v3 | POST | `.../v3/createInferenceJob` |

`jobType`：`AI_TRAIN` / `AI_ONLINE_INFERENCE_SERVICE`。默认 `bizType=DROS`。

- `restart-deploy`：变配重启部署，body 含 `uuid` + 与创建部署类似字段；CLI 用 `--config`。
- `restart-pod`：失败 POD 重启，JSON body：`userId` / `jobId` / `jobPodNames`。

## devenv

| CLI | Method | Path |
|-----|--------|------|
| `devenv list` | GET | `.../dev-env/list` |
| `devenv detail` | GET | `.../dev-env/detail` |
| `devenv create` | POST | `.../dev-env/create` |
| `devenv restart` | POST | `.../dev-env/restart` |
| `devenv save-image` | POST | `.../dev-env/saveImage` |

`jobType` 固定 `JUPYTER`。

## pods / monitor

| CLI | Method | Path |
|-----|--------|------|
| `pods list --version v2` | GET | `.../getJobMetrics` |
| `pods list --version v3` / `pods monitor` | GET | `.../getJobMonitor` |
| `pods monitor` + pod/start/end | GET | `.../running-monitor` |

## logs

| CLI | Method | Path | 注意 |
|-----|--------|------|------|
| `logs get` | GET | `/api/open/job-service/log/info` | 必须 header `zone` |
| `logs download` | GET | `/api/open/job-service/log/download` | 原始字节；CLI 用 `-o` |
| `logs prefetch` | GET | `/api/open/job-service/log/pre_fetch` | 时间窗口日志量统计；不要求 zone |

`x10000` → zone `X10000`；`wuxi` 无默认映射，需显式 `--zone`（仅 `logs get`）。

## resources

| CLI | Method | Path |
|-----|--------|------|
| `resources specs` | GET | `/api/open/dros-ic-platform/open-job/specs` |
| `resources projects` | GET | `/api/open/resource-proxy/subMission/open-job/projects` |
| `resources sub-projects` | GET | `.../subProjects` |
| `resources promotions` | GET | `.../promotion/list` |

## algorithms

| CLI | Method | Path |
|-----|--------|------|
| `algorithms list` / `get` | GET | `/api/open/dros-ic-platform/open-job/algorithms` |
| `algorithms create` | POST | `.../algorithms` |
| `algorithms update` | PUT | `.../algorithms/{uuid}` |
| `algorithms delete` | DELETE | `.../algorithms/{uuid}` |
| `algorithms publish` | PUT | `.../algorithms/{uuid}/share` |
| `algorithms unpublish` | PUT | `.../algorithms/{uuid}/stop-share` |
| `algorithms share` | POST | `.../algorithms/{uuid}/share` |
| `algorithms unshare` | DELETE | `.../algorithms/{uuid}/share` |

`isPublic` 查询值为小写 `true`/`false`。写操作默认 dry-run。`unshare` 的 query `shareList` 为数组。

## images

| CLI | Method | Path |
|-----|--------|------|
| `images list` | GET | `.../images` |
| `images tags` | GET | `.../images/tags` |
| `images share` | POST | `.../images/share` |
| `images unshare` | DELETE | `.../images/share` |

共享 body：`uuid` + `source` + `userName`（增）/ `userNameList`（删）。

## seahold（海纳私有数据集 PVC）

| CLI | Method | Path |
|-----|--------|------|
| `seahold list` | POST | `.../seahold-dataset/list` |
| `seahold create` | POST | `.../seahold-dataset/create` |
| `seahold destroy` | POST | `.../seahold-dataset/destroy` |

仅限支持该能力的平台（文档标注 Zero2X）；部分集群可能 404。

## 明确不做

| 能力 | 说明 |
|------|------|
| WebSocket 实时日志 | Apifox「WebSocket日志接口」协议不同，本 CLI/Skill **不实现** |
