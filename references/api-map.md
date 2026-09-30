# API ↔ CLI 映射

集群 endpoint（`config/clusters.yaml`）：

| cluster | api_base |
|---------|----------|
| wuxi | `http://10.124.120.108:38080` |
| x10000 | `http://10.202.32.189:38080` |

鉴权：`POST /api/open/credentials` → header `accessToken`；查询普遍带 `userId`。

## jobs

| CLI | Method | Path |
|-----|--------|------|
| `jobs list` | GET | `/api/open/dros-ic-platform/open-job/jobList` |
| `jobs detail` | GET | `.../getJobDetail` |
| `jobs list-all` | GET | `.../jobListAll` |
| `jobs stop` | PUT | `.../stop` |
| `jobs restart` | POST | `.../restart` |
| `jobs create-train` v2 | POST | `.../create` |
| `jobs create-train` v3 | POST | `.../v3/create` |
| `jobs create-deploy` v2 | POST | `.../createInferenceJob` |
| `jobs create-deploy` v3 | POST | `.../v3/createInferenceJob` |

`jobType`：`AI_TRAIN` / `AI_ONLINE_INFERENCE_SERVICE`。默认 `bizType=DROS`。

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

`x10000` → zone `X10000`；`wuxi` 无默认映射，需显式 `--zone`。

## resources

| CLI | Path |
|-----|------|
| `resources specs` | `/api/open/dros-ic-platform/open-job/specs` |
| `resources projects` | `/api/open/resource-proxy/subMission/open-job/projects` |
| `resources sub-projects` | `.../subProjects` |

## algorithms / images

| CLI | Path |
|-----|------|
| `algorithms list` / `get` | `/api/open/dros-ic-platform/open-job/algorithms` |
| `images list` | `.../images` |
| `images tags` | `.../images/tags` |

`isPublic` 查询值为小写 `true`/`false`。
