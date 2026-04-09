# Anthropic 反复提的 "Harness"，我们用了六个月，今天开源

---

## 00

昨天 Anthropic 发布了 Managed Agents。

翻它的技术文档，有个词反复出现：**Harness**。

> 每个 Agent 请求都应该跑在受治理的环境里。

这不是新概念。我们在自己的项目里跑了六个月的 Harness。今天开源。

它叫 **wow-harness**。

一行命令装进你的项目，Claude Code 立刻从"一个人蛮干"变成"一个有流程、有审查、有兜底的工程组织"。

---

## 01 先说一下什么是 Harness

Harness 这个词最近火了，但很多人还没搞清楚它是什么。

简单说：**AI 很会干活，但不会自我管理。Harness 就是帮它自我管理的外围系统。**

类比：你招了一个特别聪明的实习生。写代码很快，理解力强，但是——

- 你让他别碰生产数据库，他有时候忘
- 你让他做完跑测试，他说"跑了"但其实没跑
- 你让他改一个 bug，他顺手改了三个你没让改的文件

这个实习生需要什么？不是更详细的手册，是**流程、规范、检查机制**。

这就是 Harness。

Anthropic 的 Managed Agents 是**云端托管 Harness**——他们帮你管沙箱、状态、重试。

我们做的 wow-harness 是**本地开发 Harness**——管的是代码质量、审查流程、完成验证。

两个不同层面，但核心理念一样：**AI 的可靠性不能靠 AI 自己保证。**

---

## 02 一个改变一切的数字

我们在生产项目里积累了 6 个月的数据。其中一个数字改变了我们对 AI 开发的理解：

<!-- [图 ①：六层治理体系] -->

> **CLAUDE.md 指令遵从率：约 20%**
>
> **Hook 执行率：100%**

你在 CLAUDE.md 里写的规则，AI 只在 20% 的情况下持续遵守。不是因为它不想听——是 LLM 的结构性约束。

但 Hook 执行率是 100%。因为 Hook 不是请求，是**物理约束**。

红绿灯不是建议。是机械装置。

**wow-harness 就是把你项目里该有的红绿灯、检查站、隔离带，一次性帮你装好。**

---

## 03 开箱即用：一行命令，拎包入住

```bash
python3 scripts/install/phase2_auto.py /path/to/your/project --tier drop-in
```

装完之后，你的项目里多了这些：

```
your-project/
├── .claude/
│   ├── settings.json    ← Hook 注册（追加模式，不覆盖你已有的）
│   ├── skills/          ← 16 个专业化 Agent 行为
│   │   ├── lead/        ← 8-Gate 流程管控
│   │   ├── arch/        ← 架构设计
│   │   ├── guardian-fixer/  ← Bug 修复流程
│   │   ├── crystal-learn/   ← 失败模式自学习
│   │   ├── bug-triage/      ← Bug 分诊
│   │   └── ...12 more
│   └── rules/           ← 路径作用域规则（编辑文件时自动加载）
├── scripts/
│   ├── hooks/           ← 16 个生命周期 Hook
│   │   ├── stop-evaluator.py    ← 阻止草率退出
│   │   ├── risk-tracker.py      ← 风险棘轮
│   │   ├── loop-detection.py    ← 循环检测
│   │   ├── deploy-guard.py      ← 部署拦截
│   │   └── ...12 more
│   └── checks/          ← 15 个自动化验证器
│       ├── check_api_types.py   ← API 类型一致性
│       ├── check_doc_freshness.py ← 文档新鲜度
│       ├── check_security.py      ← 安全模式检查
│       └── ...12 more
└── CLAUDE.md            ← 自动生成的项目治理指南
```

**不需要配置。不需要改代码。装完就生效。**

装完之后 Claude Code 打开你的项目，所有 Hook 自动挂载，所有 Skill 自动可用。

---

## 04 装完之后：一个 session 是什么样的

你打开 Claude Code，开始一个 session。

### Session 开始那一刻

三个 Hook 自动触发：
- `session-start-reset-risk.py` → 重置风险状态，干净起跑
- `session-start-magic-docs.py` → 加载你项目的上下文文档
- `session-start-toolkit-reminder.py` → 告诉 AI 有哪些 Skill 可用

**你什么都不用做。**

### 你让 AI 写代码

每次 AI 调用 Edit / Write 工具，三个 Hook 联动：
- `guard-feedback.py` → 根据被编辑的文件路径，自动注入那个领域的规则（比如编辑部署脚本就注入部署安全规则，编辑后端路由就注入路由规范）
- `loop-detection.py` → 检测 AI 是不是在同一个文件上改来改去（循环编辑是漂移的早期信号）
- `risk-tracker.py` → 追踪文件变更的风险等级

**你什么都不用做。规则自动到位。**

### AI 要执行 bash 命令

- `deploy-guard.py` → 如果命令包含 scp/rsync 等部署操作，直接拦截。exit 2。不是"提醒你确认"，是**物理阻断**
- `auto-python3.py` → 如果 AI 写了 `python` 而不是 `python3`，自动纠正
- `tool-call-counter.py` → 记录工具调用频率，用于事后分析

### AI 说"我做完了，要退出"

**这是最关键的时刻。** Stop hook 启动：

`stop-evaluator.py` 做三件事：

1. **机械化第一关** — 检查 `progress.json`，所有 feature 都 passing 了吗？没有就硬阻断，不管 AI 怎么说
2. **完成候选品检测** — 解析本 session 的 transcript，提取 Edit/Write 文件列表，和 git 未提交变更取交集。纯聊天？没有写操作？放行，不打扰。有未提交的编辑？触发审查
3. **注入检查清单** — 给 AI 一份结构化的完成自检清单，要求它逐项确认

**效果：AI 不能草率退出。但纯聊天时也不会被骚扰。**

### Session 结束

- `session-reflection.py` → 自动生成 session 总结
- `trace-analyzer.py` → 聚合本次 session 的行为数据
- `deploy-progress-on-session-end.py` → 持久化进度

**整个 session 从头到尾，你做的事情就是：告诉 AI 做什么，看最终结果，决定是否 accept。**

中间的质量保障、漂移检测、规则注入——全自动。

---

## 05 16 个 Skill：不是一个 AI 干所有事

<!-- [图 ②：Hook 生命周期] -->

大多数人用 Claude Code，是当成一个"全能选手"来用的。

wow-harness 的方式不同：**16 个 Skill = 16 个岗位**，各司其职。

| 类别 | Skill | 干什么 |
|------|-------|--------|
| **流程管控** | `lead` | 8-Gate 状态机，管整个开发流程 |
| **架构** | `arch` | 架构设计，变更传播分析 |
| **方案锁定** | `plan-lock` | 方案批准后不能偏离 |
| **任务拆分** | `task-arch` | 把方案拆成可执行的任务 |
| **Bug 修复** | `guardian-fixer` | 8 关流程修复，带验证 |
| **Bug 分诊** | `bug-triage` | 结构化分类定级 |
| **自学习** | `crystal-learn` | 从失败中提取不变量 |
| **开发** | `harness-eng` | 日常开发执行 |
| **测试** | `harness-eng-test` | 测试策略与执行 |
| **运维** | `harness-ops` | 部署、监控、排障 |
| **实验** | `harness-lab` | 探索性实验 |
| **品牌表达** | `harness-voice` | 项目文案和对外表达 |
| **开发指南** | `harness-dev` | 日常开发规范 |
| **交接** | `harness-dev-handoff` | AI 交接上下文 |
| **能力发现** | `skill-discovery` | 从工作模式中发现新 Skill |
| **Bug 流水线** | `bug-pipeline` | Bug 到 PR 全自动 |

每个 Skill 有 `{{PLACEHOLDER}}` 结构化槽位——安装时你可以填入自己项目的上下文，让 Skill 适配你的领域。

---

## 06 8-Gate 状态机：自己不能查自己

<!-- [图 ③：8-Gate 状态机] -->

每个重要变更必须经过 8 道门禁。

```
G0 问题  →  G1 设计  →  G2 审查★
  →  G3 方案  →  G4 审查+锁定★
  →  G5 任务拆分  →  G6 审查★
  →  G7 执行+日志  →  G8 终审★

★ = 自动 spawn 独立审查 Agent
```

偶数 Gate 的审查 Agent 有三个特点：

1. **独立上下文** — 不共享主 Agent 的对话历史
2. **只读工具集** — 物理上不能修改代码（Schema 级隔离）
3. **从头审查** — 不受之前工作的锚定效应影响

为什么不能自己查自己？

AI 问自己"做得好不好"，答案永远是"好"。换一个 AI 来问，答案就诚实了。

**审查不需要等人。但质量不打折。**

---

## 07 Schema 级隔离：不是"请不要"，是"不能"

<!-- [图 ⑤：Schema 级审查隔离] -->

这是整个系统**最关键的设计决策**。

| 方法 | 遵从率 |
|------|--------|
| 在提示词里写"不要修改文件" | ~70% |
| 从工具清单里删掉 Edit/Write | **100%** |

因为它**物理上调不了不存在的工具**。

wow-harness 的审查 Agent 定义文件长这样：

```yaml
tools:
  - Read
  - Glob
  - Grep
  - WebFetch
  # Edit, Write, Bash → 不在清单里 → 物理上不可调用
```

整个 wow-harness 的设计哲学浓缩在一句话里：

> **凡是重要的事，不靠说，靠执行。**

---

## 08 Session 隔离：多个 AI 并行不污染

<!-- [图 ④：Session 隔离] -->

如果你同时开多个 Claude Code 窗口做不同的事呢？

wow-harness 的 Stop hook 通过 **transcript 隔离**解决这个问题：

- 每个 Claude Code session 有独立的 transcript 文件（`.jsonl`）
- Stop hook 只解析**当前 session** 的 transcript，提取这个 session 写过的文件
- 和 git 未提交变更取交集 → 只对**本 session 未提交的编辑**触发完成审查

Session A 编辑的文件不会影响 Session B 的 Stop 判定。零共享可变状态。

---

## 09 自学习：犯一次错，永久免疫

`crystal-learn` Skill 自动从失败中提取不变量。

**举例**：AI 改了后端 API 但忘了改前端调用。

传统做法：在 CLAUDE.md 里加一条"改 API 要同步改前端"。遵从率？20%。

wow-harness 做法：提取规则"**改契约必须 grep 所有消费者**"，机械化注入到执行层 Skill。下次同类操作时**自动触发提醒**。

不靠记住。靠机制。

---

## 10 一个真实故事：Stop Hook 被修了三轮

wow-harness 不是论文里的理想系统。它是被**现实打出来的**。

我们的 Stop hook 经历了三轮修复：

**第一轮**：AI 在纯聊天时也弹出完成检查清单 → 加了"是否有写操作"判断

**第二轮**：AI 编辑完文件 commit 了再聊天，还是触发 → 改为"编辑文件 ∩ git 未提交变更"交集

**第三轮**：两个 AI 并行工作，共享状态互相污染 → 改为基于独立 transcript 的 session 隔离

三轮。一个 Hook。

**每一条规则存在的理由都是：上一条规则被 AI 找到了漏洞。**

---

## 11 和其他方案的对比

| | 手写 CLAUDE.md | Cursor Rules | Managed Agents | **wow-harness** |
|---|---|---|---|---|
| 定位 | 指令文档 | 指令文档 | 云端 Agent 托管 | **本地开发治理** |
| 约束方式 | 文本 | 文本 | 云端执行 | **机械化 Hook** |
| 遵从率 | ~20% | ~20% | N/A | **100%** |
| 审查 | 自审 | 自审 | 无内置 | **独立 Agent + Schema 隔离** |
| 自学习 | ✗ | ✗ | ✗ | **✓** |
| 部署 | 手动写 | 手动写 | API 接入 | **一行命令** |
| 开箱即用 | ✗ | ✗ | ✓ | **✓** |
| 适用 | 所有 AI 编辑器 | Cursor | API 调用 | **Claude Code** |

CLAUDE.md 仍然有用。wow-harness 不替代它——**它执行它**。

---

## 12 三分钟装好

```bash
git clone https://github.com/NatureBlueee/wow-harness.git
cd wow-harness
python3 scripts/install/phase2_auto.py /path/to/your/project --tier drop-in
```

三个层级：

| 层级 | 信任度 | 效果 |
|------|--------|------|
| **drop-in** | 最低 | 原样安装。不读你的代码。先试试看 |
| **adapt** | 中等 | 读你的 README + 文档，把 Skill 适配到你的项目 |
| **mine** | 完全 | 读你的工作记录，深度适配到你的模式 |

安装器幂等——跑两次结果一样。不覆盖你已有的 CLAUDE.md 和 settings.json。

需要：Claude Code CLI + Python 3.9+ + Git。

---

## 来历

wow-harness 从 [Towow](https://towow.net)（通爻，一个 Agent 协作协议项目）6 个月的生产使用中提取出来。

我们在做 Towow 的过程中，不断被 AI 的各种创造性绕过逼着加规则、加 Hook、加隔离。加着加着发现，这套治理层本身比项目还有通用价值。

每个用 AI 辅助开发的项目都需要它。

**GitHub**: [NatureBlueee/wow-harness](https://github.com/NatureBlueee/wow-harness)

**License**: MIT

---

*Anthropic 说 Harness 是 Agent 的未来。*

*我们说 Harness 是被 Agent 逼出来的现在。*

*开箱即用。一行命令。16 个 Hook 自动挂载。*

*每一条规则背后，都有一个 AI 找到了绕过上一条规则的创造性方法。*
