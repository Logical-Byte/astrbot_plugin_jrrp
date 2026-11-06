# 今日人品

查询每日人品运势，支持今日、本周、本月和历史平均。移植自 AmiyaBot 插件 `src/jrrp`，数值算法与文案保持一致。

## 指令

无需唤醒前缀，直接发送以下任意一个词：

| 指令 | 别名 |
|---|---|
| `jrrp` | `今日人品`、`今日运势` |
| `weekjrrp` | `本周人品`、`本周运势`、`周运势` |
| `monthjrrp` | `本月人品`、`本月运势`、`月运势` |
| `alljrrp` | `总人品`、`平均人品`、`平均运势` |

## 回复形态

- **群聊**：`@发起人` + 文本 + 一行「查查我的」按钮
- **私聊**：不 @（QQ 的 C2C 消息不支持 `qqbot-at-user`，带上会整条发送失败），按钮保留
- 点「查查我的」按**点击者**重新计算，不是复读原主人的结果
- 桌面版 QQ 会在卡片顶部留一行空白，移动端没有；这是客户端渲染差异，不是消息内容多出的换行

## 算法

- 种子 = `int(YYMMDD) + int(用户ID)`，取值范围取运势区间配置的 `min` 最小值与 `max` 最大值
- 用 `random.Random(seed).randint(min, max)` 抽值 → 同一用户同一天结果固定，且与源插件一致
- 数值落在哪个区间就显示对应等级与描述；没有区间匹配时回退「未知 / 你进入了虚空之地」
- 本周按 ISO 周（年 + 周数）判定，本月按（年 + 月）判定；平均值为 `round(总和/天数, 1)`

## 存储

`data/plugin_data/astrbot_plugin_jrrp/jrrp.db`，表 `jrrp_data(user_id, value, date)`，`(user_id, date)` 唯一索引，当天重复查询不会重复写入。

## 配置

| 键 | 说明 |
|---|---|
| `ranges` | 运势区间 JSON 数组，默认与源插件 `config_default.yaml` 的 10 档一致 |
| `time_sync` | 启动时向 `bjtime.org.cn` 取 `Date` 头校时，失败静默回退本地时钟 |
| `sync_timeout` | 校时请求超时秒数 |
| `mention` | 回复时是否 `@` 发起人；QQ 官方卡片若出现多余空行可关掉 |

`ranges` 留空或写成非法 JSON 时使用内置 10 档：

| 区间 | 等级 |
|---|---|
| 100 | 超吉 |
| 76–99 | 大吉 |
| 66–75 | 吉 |
| 63–65 | 半吉 |
| 59–62 | 小吉 |
| 54–58 | 末小吉 |
| 19–53 | 末吉 |
| 10–18 | 凶 |
| 1–9 | 大凶 |
| 0 | 超凶（大寄） |

## 说明

- 非数字用户 ID（WebChat 等）会先转换成稳定的 63 位哈希，再参与种子计算；源插件在同样情况下会直接抛错
- 不依赖任何第三方库，仅用标准库 `sqlite3`、`random`、`urllib`

## 鸣谢

- [AmiyaBot / Amiya-Bot-plugins](https://github.com/AmiyaBot/Amiya-Bot-plugins)：今日人品的数值算法与文案来源
- [AstrBot](https://github.com/AstrBotDevs/AstrBot)：插件框架、消息平台适配与文转图服务
- [torappu.prts.wiki](https://torappu.prts.wiki)：明日方舟解包数据与资源镜像
- [data.akedata.wiki](https://data.akedata.wiki)：终末地数据与静态资源镜像

以上项目的作者与维护者让这个插件成为可能，数据与素材的版权归原作者及各游戏版权方所有。

## 许可证

[MIT](LICENSE)
