# wow-harness 在 Towow 的实践

> **本地展示**：双击打开 [`docs/practice.html`](./practice.html)（浅色主题，纯 HTML+CSS，不依赖任何渲染引擎）。
> 下面是同一份内容的 GitHub 在线版本（Mermaid 渲染）。

53 天 / 1137 commits / 93 万行 / 1992 测试 — 一个人 + AI 全自主交付。
两张图是 harness 当前真实在跑的样子。

---

## 图 1 · 你说一句话，AI 自己干完 8 关

```mermaid
flowchart LR
    U[你说<br/>我要做 X]:::user --> G0
    G0[Gate 0<br/>lead 锁问题]:::work --> G1
    G1[Gate 1<br/>arch 出架构]:::work --> G2
    G2[Gate 2<br/>独立审查 AI<br/>无 Edit/Write]:::review --> G34
    G34[Gate 3-4<br/>plan-lock 冻结<br/>独立审查]:::review --> G56
    G56[Gate 5-6<br/>task-arch 拆 WP<br/>独立审查]:::review --> G7
    G7[Gate 7<br/>harness-dev 写代码<br/>边写边记日志]:::work --> G8
    G8[Gate 8<br/>终审 + E2E]:::review --> PR
    PR[accept PR]:::user

    classDef user fill:#fff4d6,stroke:#d97706,color:#000
    classDef work fill:#dceefb,stroke:#1d4ed8,color:#000
    classDef review fill:#fde2ea,stroke:#be123c,color:#000
```

- 黄色 = 你的输入 / 你的决策
- 蓝色 = AI 执行（lead / arch / dev）
- 红色 = 独立审查 AI — 不共享之前对话从头看；tools 列表里物理移除 Edit / Write，**不是嘱咐它「只看不改」，是它根本调不出这两个工具**

---

## 图 2 · 三层 harness（v1 → v2 → v3）

```mermaid
flowchart TB
    subgraph V3[v3 · H 系列治理 · harness 自己出问题谁来修]
        H0[H0 元规约<br/>6+1 条款]
        H9[H9 多窗口邮箱<br/>取代人脑协调员]
        H1[H1 学习层复活<br/>crystal-learn]
        Hx[H2-H8<br/>身份/记忆/治理<br/>Gate/状态/合规]
    end
    subgraph V2[v2 · vNext 能力层 · 生命周期 + 契约]
        Mode[mode-toolkit<br/>/mode plan→build→verify→release]
        Review[review-toolkit<br/>reviewer + verify-gate<br/>+ review-contract.yaml]
    end
    subgraph V1[v1 · wow-harness 基底 · 机械化约束]
        Hooks[18 hooks<br/>7 个生命周期阶段]
        Skills[16 skills<br/>lead/arch/dev/reviewer<br/>crystal-learn ...]
        Checks[15 checks<br/>规则/编号/IO schema]
    end
    V1 ==基底==> V2 ==升级==> V3

    classDef v1 fill:#dceefb,stroke:#1d4ed8,color:#000
    classDef v2 fill:#fff4d6,stroke:#d97706,color:#000
    classDef v3 fill:#d6f0d8,stroke:#15803d,color:#000
    class Hooks,Skills,Checks v1
    class Mode,Review v2
    class H0,H9,H1,Hx v3
```

- **v1（蓝）一开始就有的**：hooks 物理拦截 + skills 各司其职 + checks 自动验证
- **v2（黄）长出来的能力**：让 harness 知道"现在该做什么阶段"，让审查变成契约驱动
- **v3（绿）兜底治理**：harness 自己跑出问题之后才补的（编号撞 / 记忆涨爆 / 协调员断线 / 修问题反而引入问题）。**v3 一直闭合不再开新站，本身就是稳态信号。**

---

## 想直接看实现的话

| 你想看 | 打开这个 |
|---|---|
| 审查 AI 物理上改不了代码 | [`.claude/plugins/towow-review-toolkit/agents/reviewer.md`](../.claude/plugins/towow-review-toolkit/agents/reviewer.md) — 看顶上 `tools:` 列表 |
| ADR 编号撞了 git 直接拒绝提交 | [`.githooks/pre-commit`](../.githooks/pre-commit)（22 行 shell）+ [`scripts/checks/check_adr_plan_numbering.py`](../scripts/checks/check_adr_plan_numbering.py) |
| AI 之间怎么传消息（H9 邮箱） | [`.towow/inbox/schema/message-v1.json`](../.towow/inbox/schema/message-v1.json) + 5 个 inbox hook |
| 16 个 skill 怎么分工 | [`.claude/skills/`](../.claude/skills/) |
| 所有 hook IO schema | [`scripts/hooks/_hook_output.py`](../scripts/hooks/_hook_output.py) — 16 个 helper API（ADR-058） |
