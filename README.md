# QQ Farm Copilot

基于 OpenCV + PyQt6 的 QQ 农场自动化工具，支持 PC 端 QQ和微信平台多开和后台运行。

## 预览

<img src="images/preview.png" alt="QQ Farm Copilot 预览" width="600" />

## 使用提示

- 本软件完全免费，若付费购买请立即退款。
- 请认准项目主页获取版本与说明，谨防二次售卖、捆绑分发与虚假收费。
- 项目地址：`https://github.com/490720818/qq-farm-copilot`
- 原项目地址：`https://github.com/megumiss/qq-farm-copilot`
- 本项目基于 [qq-farm-auto](https://github.com/Z7ANN/qq-farm-auto) 重构而来

## 已实现功能

- [x] 一键收获 / 务农
- [x] 自动购买种子
- [x] 自动播种（不会支持四格，占用四格土地收益太低，建议手动有机肥料速刷）
- [x] 自动施肥（通过作物剩余成熟时间判断后自动施肥并收获，需开启地块巡查）
- [x] 自动扩建土地
- [x] 自动升级土地
- [x] 仓库批量出售
- [x] 任务奖励领取
- [x] 分享奖励领取
- [x] 商城免费商品领取
- [x] QQSVIP礼包领取
- [x] 邮件领取
- [x] 月卡领取
- [x] 好友农场偷菜
- [x] 好友农场帮忙
- [x] 自动同步等级
- [x] 地块巡查
- [x] 任务调度时间自定义
- [x] 数据统计
- [x] 一键启动
- [x] 异常发送通知
- [x] 异常自动重启（QQ端可以选择优先修复重启）
- [x] 定时重启窗口（也可修复重启）
- [x] 支持QQ/微信平台后台运行
- [x] 支持QQ/微信平台多开
- [x] 通用活动（活动更新后适配，过时自动关闭）ps.一次性领取活动不作适配（如6.19粽叶活动）
- [x] 自动种草
- [x] 游戏窗口隐藏
- [x] 微信鼠标防占用
- [x] 神秘商人

## 当前实现概览

- 架构：`BotEngine` + `TaskExecutor` + UI 页面识别（`core/ui`）
- 异常恢复：`executor/runtime` 统一异常分支处理 + 内置 `restart` 任务重启窗口
- 定时重启：可配置任务 `restart`（默认关闭，间隔 `4` 小时；重启等待由实例设置控制）
- 调度：统一任务执行器，支持 `INTERVAL` / `DAILY`
- 实例配置：`%APPDATA%\QQFarmCopilot\instances\<instance_id>\configs\config.json` 中 `tasks` 为**动态字典**
- 配置清理：启动加载时会按 `configs/config.template.json` 自动清理 `tasks.<name>.features` 中模板未定义的历史字段并写回
- 全局设置：`%APPDATA%\QQFarmCopilot\app_settings.json` 支持 `logging.retention_days`（日志保留天数，单位天）
- 数据统计：`%APPDATA%\QQFarmCopilot\instances\<instance_id>\stats\daily_action_stats.csv` 按天累计 `harvest/operation/friend_steal/friend_help`
- 任务顺序：`executor.task_order`（使用 `>` 分隔，越靠左越先执行）
- UI：左侧实时截图、中间实例运行面板、最右侧竖向实例栏（新增/删除/切换/克隆/重命名）

当前内置任务（通过 `_run_task_*` 自动发现）：

- `main`：农场主流程（收获维护、神秘商人、播种、施肥、扩建、升级）。收获先处理普通作物的一键入口，再根据当前成熟标记逐块、多次收获四格作物；每次点击后重新截图，成熟标记连续消失 3 秒才确认结束，持续无响应时按 `safety.stuck_long_wait_seconds` 超时报错。
- `friend`：独立好友任务（支持 `features.blacklist`、`features.steal_stats`、`features.help_only_guard_dog`，以及偷菜/帮忙各自的 `enabled_time_range` 与 `limit_count`；主界面仅显示黑名单条目数，详情弹窗可维护名单）
- `grass`：自动种草任务（默认关闭；依次访问好友农场，先帮忙（若需要），从 `1-1` 开始检查地块，找到草/结束图标后拖拽草种到全部地块（成熟作物不显示草图标）；支持 `features.skip_probability: float`，默认 `0.2`，`1` 与 `0` 时不跳过，介于 `0` 与 `1` 之间才按概率跳过）
- `share`：独立分享任务（仅支持微信平台，通常配合每日触发）
- `reward`：独立任务奖励领取（默认每 6 小时执行一次）
- `gift`：物品领取任务（QQSVIP礼包、商城礼包、月卡领取（如有）、可选邮件领取；支持分项开关）
- `event`：通用活动任务（默认关闭；每日 `10:01` 执行；按配置资源依次点击，`use_coupon` 控制点券资源，`end_time` 到达后自动关闭）
- `sell`：独立出售任务（仓库批量出售）
- `land_scan`：地块巡查任务（默认关闭；每 30 分钟；按实例配置的左右滑动次数分段点击地块并 OCR 采集）
- `timed_harvest`：定时收获任务（默认开启；每日 `00:00` 启动计算；依赖地块巡查结果并按聚合时间生成后续收获执行点；复用普通与四格作物的统一收获流程，成功收获后继续观察聚合窗口；支持 `features.priority_window_seconds` 调度判断间隔）
- `restart`：定时重启任务（默认关闭；每 4 小时；重启窗口并收敛回主页面）

## 后台/多开说明

1. 启动程序后，右侧竖向实例栏可进行实例管理（新增/删除/切换/克隆/重命名）。
2. 每个实例有独立配置与运行目录：
   - `%APPDATA%\QQFarmCopilot\instances\<instance_id>\configs\config.json`
   - `%APPDATA%\QQFarmCopilot\instances\<instance_id>\logs\`
   - `%APPDATA%\QQFarmCopilot\instances\<instance_id>\screenshots\`
3. 切换实例后，中间面板显示并控制当前实例；开始/暂停/停止/立即执行仅作用于当前实例。
4. 多开场景建议先在每个实例的设置中手动选择窗口。
5. 微信选择后台模式运行时，有可能会把窗口拉到前台，暂不清楚原因

## 环境要求

- Windows 10/11 或 macOS 14+（Apple Silicon，源码运行；当前 macOS 27 已实测）
- PC 端手动打开 QQ 农场

## 下载安装运行

### 方式一：下载 Release（推荐）

下载链接：
- [https://github.com/490720818/qq-farm-copilot/releases/latest](https://github.com/490720818/qq-farm-copilot/releases/latest)

1. 打开上方链接，下载最新的：
   - `QQFarmCopilot-<tag>-windows-x64.exe`
2. 将 `exe` 放到任意目录后双击运行。
3. 首次运行会自动在用户目录生成实例元数据与默认实例配置：
   - `%APPDATA%\QQFarmCopilot\profiles.json`
   - `%APPDATA%\QQFarmCopilot\instances\default\configs\config.json`
4. 打开 QQ 农场窗口，点击程序内“开始”。

### 方式二：源码运行

1. 安装 `uv`，使用 Python `3.10`。所有依赖与环境位于项目内。
2. 在项目根目录执行：

```bash
uv sync --python 3.10
uv run main.py
```

`uv.lock` 锁定依赖，`uv sync` 按操作系统安装对应的平台依赖。

### macOS / Apple Silicon

在项目根目录运行（将 uv 管理的 Python 也放在项目内）：

```bash
UV_PYTHON_INSTALL_DIR="$PWD/.uv-python" uv sync --python 3.10
uv run main.py
```

- 手动在 QQ Mac 客户端打开“QQ经典农场”小程序，设置平台为 QQ，窗口关键词与实际标题一致。
- 在系统设置 → 隐私与安全性中，为启动程序的终端或 Codex 开启“辅助功能”和“屏幕与系统音频录制”；授权后重启程序。全局 F9/F10 还需要允许输入监控，否则快捷键仅在助手窗口内生效；Mac 键盘可能需同时按 Fn。
- Mac 可选择后台模式：QQ 窗口被其他窗口覆盖时可继续点击与拖拽，不抢前台焦点或系统鼠标。需保持桌面解锁、农场窗口未最小化；暂不支持透明隐藏或虚拟桌面移动。GUI 同时运行一个实例，保留独立配置与串行任务。前台模式会使用系统鼠标。
- 后台输入使用窗口所属 PID 定向事件及私有 `CGEventSetWindowLocation` 接口，已在当前 macOS 27 的 QQ Mac 小程序实测；系统更新后需重新验证，接口不可用时会明确报错。
- 种草保留 24 格网格算法；QQ Mac 单侧锚点使用实测间距 `(-369,39)`。从 `1-1`、`2-2` 开始检查现有网格，成熟作物不显示草图标时继续检查其他地块，确认弹窗后才拖拽；普通与四格合并作物均按生长阶段处理。
- 桌面锁定后任务会明确停止并提示解锁，不会把点击发送到锁屏界面。窗口移动/缩放后，每次截图都会同步当前内容区与输入坐标。
- Mac GUI 按 Qt 逻辑尺寸布局，默认大小限制在屏幕工作区内；状态页与标签栏支持滚动，缩小窗口时保留完整文字高度。
- Retina 截图先转换到逻辑点，再归一化为原算法的 `540×960`；点击与拖拽按实际内容区比例反向映射。窗口会按屏幕工作区调整，并检查内容区比例。
- 窗口截图使用 Apple ScreenCaptureKit 的 `SCScreenshotManager`，直接读取目标窗口并显式指定逻辑尺寸，不依赖旧的 `CGWindowListCreateImage`。
- 标题栏裁剪高度来自 `configs/nonclient_metrics.json` 的 `macos.title_height`（逻辑点，当前 QQ Mac 实测默认 40）。源码运行会复制到 `.dev_appdata/QQFarmCopilot/configs/nonclient_metrics.json`，校准时修改此用户副本并重启。截图预览应只包含游戏内容。
- Mac 源码运行配置、日志、截图、OCR 模型缓存在项目 `.dev_appdata/QQFarmCopilot/` 内。
- Mac 实测的背景树和左侧地块锚点模板放在 `templates/macos/qq/btn/`，仅覆盖宿主为 macOS 时的对应资源，Windows 继续使用原模板；定位、地块网格与任务算法保持原实现。
- QQ Mac 的辅助功能树按需加载。窗口后端按 [Electron 的辅助功能约定](https://github.com/electron/electron/blob/main/docs/tutorial/accessibility.md) 开启目标进程的 `AXManualAccessibility`，等待真实窗口节点就绪后再调整尺寸，不修改系统权限。
- 自动拉起/重启需要能直接打开小程序的 `.webloc` 启动文件；设置中可手动填写 `.app` 路径，但打开 QQ 客户端本身不等于打开农场。没有有效的小程序启动入口时，应手动打开窗口并关闭定时重启任务。
- 自动恢复尝试使用 Mac 辅助功能树中的“一键修复”和“确认”。客户端未暴露相应控件或 Mac 模板不同，需要基于实际画面校准，不能视为已验证功能。

运行迁移回归检查：`uv run pytest`。

真实 Mac GUI 布局检查（不启动农场任务）：`QQFARM_NATIVE_GUI_TEST=1 uv run pytest tests/test_gui_layout.py`。


### VSCode 调试使用独立实例目录

- 在 VSCode `launch.json` 的 `env` 设置 `QFARM_DEV=true`。
- 开启后实例元数据与实例目录会隔离到项目内：`.dev_appdata/QQFarmCopilot/`。
- 调试与发布版都使用实例配置路径：`<instances>/<instance_id>/configs/config.json`。
- Windows 设置 `QFARM_DEV=false`（或不设置）后，实例目录恢复到 `%APPDATA%\QQFarmCopilot\instances\`；macOS 源码运行仍保存在项目内。

### 首次运行建议检查

1. `window_title_keyword` 与实际窗口标题一致（默认 `QQ经典农场`）。
2. 可在设置里选择小程序“添加到桌面”后生成的快捷方式（`window_shortcut_path`，`.lnk`）。
3. 多窗口场景可在设置里指定“选择窗口”（保存匹配顺序，不保存句柄）。
4. 多屏场景可在“窗口位置”中指定目标屏幕（仅保存序号）与该屏幕内位置；也可指定目标虚拟桌面序号（`0` 表示不移动）。
5. `planting.window_platform` 与当前平台一致（QQ / 微信）。
6. 游戏窗口已打开且未最小化。

热键：

- `F9`：暂停 / 恢复
- `F10`：停止

## 配置说明

实例主配置文件（按实例隔离）：

- `%APPDATA%\QQFarmCopilot\instances\<instance_id>\configs\config.json`

应用级配置文件（全局）：

- `%APPDATA%\QQFarmCopilot\app_settings.json`
- `logging.retention_days`：日志保留天数（单位天，默认 `7`）；启动时与全局设置变更时会清理过期 `.log` 文件

核心字段：

- `window_title_keyword`：窗口标题关键词（默认 `QQ经典农场`）
- `window_shortcut_path`：小程序桌面快捷方式路径（`.lnk`）
- `window_shortcut_launch_delay_seconds`：快捷方式启动后延迟初始化窗口的秒数（默认 `3`）
- `window_restart_delay_seconds`：窗口重启流程中“关闭后到重新拉起前”的等待秒数（默认 `5`）
- `window_select_rule`：窗口选择规则（`auto` 或 `index:N`，`auto` 会按当前平台优先匹配）
- `safety`：运行方式、随机延迟、点击抖动、单轮点击上限、卡死判定阈值（`stuck_seconds` 默认 `60`、`stuck_long_wait_seconds` 默认 `120`）、`debug_log_enabled`
- `screenshot`：截图相关配置；`capture_interval_seconds` 控制最小截图间隔（秒，默认 `0.3`，`0` 表示不限制）
- `planting`：种植策略、等级、平台、窗口定位（`window_screen_index` 为目标屏幕序号，和显示器查询序号一致；`0` 表示默认主屏；`window_position` 为屏幕内位置；`virtual_desktop_index` 为目标虚拟桌面序号，`0` 表示不移动）、`warehouse_first`（仓库优先选种；按固定底色数字块识别最左种子）、`skip_event_crops`（与仓库优先同时开启时，按关闭仓库优先处理；固定排除作物始终生效）、等级 OCR 开关、`planting_stable_seconds`（播种稳定时间）、`planting_stable_timeout_seconds`（背景树锚点稳定等待超时）、`land_swipe_right_times/land_swipe_left_times`（土地相关流程右滑/左滑次数，地块巡查与土地升级共用，滑动坐标固定）
- `executor`：调度顺序与默认间隔配置；`min_task_interval_seconds`（任务最小执行间隔）
- `recovery`：异常恢复策略；`task_restart_attempts`（任务异常重启窗口次数）、`task_retry_delay_seconds`（重启后重试延迟秒数）、`window_launch_wait_timeout_seconds`（每轮等待窗口出现超时）、`startup_retry_step_sleep_seconds`（启动重试轮询步进）、`startup_stabilize_timeout_seconds`（启动收敛总超时）
- `notification`：异常通知配置；`exception_notify_enabled`（是否在异常停机时推送通知）、`win_toast_enabled`（是否发送 Windows 本地通知，依赖 `winotify`）、`onepush_config`（可选 OnePush YAML 配置文本）
- `executor.task_order`：任务固定顺序配置（示例：`land_scan>timed_harvest>main>friend>grass>sell>reward>gift>event>share>restart`）
- `land`：农场详情配置；`land.plots` 为 24 格地块状态列表（元素：`{ "plot_id": "1-1", "level": "unbuilt|normal|red|black|gold|amethyst", "maturity_countdown": "HH:MM:SS", "countdown_sync_time": "YYYY-MM-DD HH:MM:SS", "need_upgrade": false, "need_planting": false }`）；`countdown_sync_time` 为该地块倒计时采样时间；`land.profile` 为个人信息（`level/gold/coupon/exp`，由等级同步 OCR 回写）
- `tasks`：动态任务字典
- `tasks.<task>.next_run`：任务下次执行时间（持久化到配置，默认 `2026-01-01 00:00`）
- `tasks.<task>.enabled_time_range`：任务启用时间段（`HH:MM:SS-HH:MM:SS`，默认 `00:00:00-23:59:59`，仅 `INTERVAL` 生效）
- `tasks.<task>.daily_times`：每日触发时间点列表（`list[HH:MM]`，仅 `DAILY` 生效）

等级 OCR 相关（`planting`）：

- `level_ocr_enabled`：是否启用播种前等级 OCR（对应设置面板“等级”右侧“自动同步”开关）
- 等级 OCR 识别区域由统一代码常量维护（见 `tasks/main.py`，不区分平台）

`tasks` 示例：

```json
{
  "main": {
    "enabled": true,
    "trigger": "interval",
    "interval_seconds": 60,
    "enabled_time_range": "00:00:00-23:59:59",
    "daily_times": ["04:00"],
    "next_run": "2026-01-01 00:00",
    "failure_interval_seconds": 30,
    "features": {
      "auto_harvest": true,
      "auto_merchant": false,
      "auto_plant": false,
      "auto_expand": false,
      "auto_upgrade": false,
      "auto_fertilize": false,
      "maturity_threshold_seconds": 3600,
      "auto_buy_fertilizer": false,
      "fertilizer_purchase_threshold_seconds": 108000
    }
  },
  "friend": {
    "enabled": true,
    "trigger": "interval",
    "daily_times": ["04:00"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 1800,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 60,
    "features": {
      "auto_steal": false,
      "steal_enabled_time_range": "00:00:00-23:59:59",
      "steal_limit_count": 0,
      "steal_stats": false,
      "auto_help": true,
      "help_only_guard_dog": false,
      "help_enabled_time_range": "00:00:00-23:59:59",
      "help_limit_count": 0,
      "auto_accept_request": true,
      "blacklist": [
        "测试好友-张三",
        "测试好友-李四"
      ]
    }
  },
  "grass": {
    "enabled": false,
    "trigger": "interval",
    "daily_times": ["00:01"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 21600,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 300,
    "features": {
      "skip_probability": 0.2
    }
  },
  "share": {
    "enabled": true,
    "trigger": "daily",
    "daily_times": ["04:00", "12:00", "20:00"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 86400,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 300,
    "features": {}
  },
  "reward": {
    "enabled": true,
    "trigger": "interval",
    "daily_times": ["04:00"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 21600,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 300,
    "features": {
      "claim_growth_task": false,
      "claim_daily_task": true
    }
  },
  "gift": {
    "enabled": true,
    "trigger": "daily",
    "daily_times": ["04:00", "16:00"],
    "enabled_time_range": "00:00:00-23:59:59",
    "interval_seconds": 86400,
    "failure_interval_seconds": 300,
    "features": {
      "auto_svip_gift": true,
      "auto_mall_gift": true,
      "auto_mail": true
    }
  },
  "event": {
    "enabled": false,
    "trigger": "daily",
    "daily_times": ["10:01"],
    "enabled_time_range": "00:00:00-23:59:59",
    "interval_seconds": 86400,
    "failure_interval_seconds": 300,
    "features": {
      "activity_name": "",
      "resources": [],
      "use_coupon": false,
      "end_time": ""
    }
  },
  "land_scan": {
    "enabled": false,
    "trigger": "interval",
    "daily_times": ["04:00"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 1800,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 300,
    "features": {}
  },
  "timed_harvest": {
    "enabled": true,
    "trigger": "daily",
    "daily_times": ["00:00"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 86400,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 300,
    "features": {
      "aggregation_seconds": 60,
      "priority_window_seconds": 120
    }
  },
  "restart": {
    "enabled": false,
    "trigger": "interval",
    "daily_times": ["04:00"],
    "next_run": "2026-01-01 00:00",
    "interval_seconds": 14400,
    "enabled_time_range": "00:00:00-23:59:59",
    "failure_interval_seconds": 300,
    "features": {}
  }
}
```

`tasks.<task>.features` 字段说明：

- 布尔开关：`{ "feature_x": true }`
- 数值参数：`{ "feature_num": 5 }`
- 字符串参数（例如启用时段）：`{ "steal_enabled_time_range": "00:00:00-23:59:59" }`
- 列表项（例如好友黑名单）：`{ "blacklist": ["好友A", "好友B"] }`

调度规则：

- 到期任务按 `executor.task_order` 从左到右执行（`>` 分隔）
- 当 `timed_harvest` 被更早任务阻塞且 `next_run` 时间差不超过 `features.priority_window_seconds` 时，执行器会将阻塞任务 `next_run` 顺延至少 `1` 秒，再按 `executor.task_order` 选取任务，使 `timed_harvest` 优先执行
- 任务执行后按成功/失败间隔或 `TaskResult.next_run_seconds` 计算下一次执行
- `INTERVAL` 任务仅在 `enabled_time_range` 内执行；不在时间段内会跳过本轮并延迟到下个启用时段起点
- `interval_seconds` / `failure_interval_seconds` 生效下限为 `executor.min_task_interval_seconds`（默认 `5` 秒）
- 每次计算出的下次执行时间会回写到 `tasks.<task>.next_run`
- `DAILY` 与 `INTERVAL` 共用同一套执行器队列

## UI 面板

- 左侧：当前实例截图预览
- 中间：当前实例状态、日志、任务调度、任务设置、设置（保留原逻辑）
- 右侧实例栏（竖向）：新增、删除、切换、克隆、重命名
- 启停控制：仍在中间面板内，按当前实例执行

### UI 文案配置

- 任务/功能/状态面板文案读取 `configs/ui_labels.json`（内置配置）。
- 修改文案后需要重新运行程序，运行中不会热重建已创建面板。

> 说明：任务顺序统一由 `executor.task_order` 维护，任务面板不提供编辑控件。

## 新增任务（当前实现方式）

1. 在 `core/engine/bot/executor.py` 增加 `_run_task_<name>` 方法
2. 在实例配置 `instances/<instance_id>/configs/config.json` 的 `tasks` 增加 `<name>` 配置
3. 在任务代码中通过强类型入口读取参数：`self.task.<task_name>.feature.<field>`（任务 features）和 `self.config.planting.<field>`（播种配置）
4. 若新增或修改 `tasks.<name>.features` 字段，执行 `.\.venv\Scripts\python.exe tools\gen_task_views.py` 生成/更新 `models/task_views.py`
5. （可选）在 `configs/ui_labels.json` 增加任务与功能文案

执行器会自动发现 `_run_task_*` 并参与调度。

## 目录结构（当前）

```text
core/
  engine/
    bot/        # Bot 入口、运行态、执行器桥接、视觉桥接
    task/       # 通用任务执行器、任务模型、统计调度器
  platform/     # 窗口/截图/点击执行适配
  ui/           # 页面图、assets 按钮、UI 导航
  vision/       # CV 检测器
tasks/          # 业务任务实现
configs/
  config.template.json
  config.json
tools/
  template_collector.py
  button_extract.py
  import_seeds.py
```

## 免责声明

本项目仅供学习研究 OpenCV 视觉识别技术使用。自动化操作可能违反游戏服务条款，由此产生的一切后果由使用者自行承担。

## 许可证

本项目采用 `GNU General Public License v3.0 (GPLv3)`，详见根目录 [LICENSE](LICENSE)。

