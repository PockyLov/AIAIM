
---

# 4. Agent / Subagent Team 设计

不要过度复杂。AIAIM 需要的是一个**小型、分层、偏工程落地的 Agent Team**。

## 推荐 Agent Team

| Agent | 角色定位 | 主要职责 |
|---|---|---|
| Main Architect Agent | 总架构 / 产品负责人 | 控制 Phase 边界、拆任务、审查方案是否过度复杂、决定模块边界。 |
| Vision/Data Agent | YOLO / 数据集负责人 | 负责后续截图数据集、标注格式、YOLO 训练、模型评估、误检漏检分析。 |
| Screen/Capture Agent | 截图 / 前台窗口负责人 | 负责 AIMLAB 前台验证、截图稳定性、全屏坐标、DPI、采集流程。 |
| Control/Safety Agent | 鼠标控制 / 安全负责人 | 负责 dry-run、真实移动开关、点击 gate、紧急停止、日志、安全边界。 |
| QA/Validation Agent | 验收 / 测试负责人 | 负责每个 Phase 的验收标准、测试清单、失败复现、回归测试。 |
| Docs/Report Agent | 文档 / 报告负责人 | 负责 README、Phase Report、Runbook、决策记录、下一阶段 Prompt。 |

---

## 每个 Agent 的具体职责

### 1. Main Architect Agent

负责：

1. 判断当前 Phase 应该做什么。
2. 防止 Codex 跨 Phase 乱做。
3. 控制模块边界。
4. 把复杂任务拆成可验证的小交付。
5. 评估方案是否过度工程化。
6. 决定哪些内容进入代码，哪些只进入文档。

适合参与所有 Phase。

---

### 2. Vision/Data Agent

负责：

1. YOLO 数据集结构设计。
2. 黄球标注规则。
3. 训练集 / 验证集拆分。
4. YOLO 格式 label 规范。
5. 后续模型训练参数规划。
6. 检测结果评估。
7. 误检、漏检、置信度阈值分析。

Phase 0 只做规划。

Phase 2、3、4 是主要负责人。

---

### 3. Screen/Capture Agent

负责：

1. AIMLAB 是否前台。
2. 全屏截图稳定性。
3. 截图频率。
4. 多显示器风险。
5. DPI 缩放风险。
6. 窗口坐标和屏幕坐标区别。
7. 自动采集真实截图流程。

Phase 1、2 是主要负责人。

---

### 4. Control/Safety Agent

负责：

1. dry-run 默认策略。
2. 鼠标移动是否允许。
3. 点击是否允许。
4. 前台窗口 gate。
5. 紧急停止机制。
6. 真实控制日志。
7. 防止误点击桌面、浏览器、其他窗口。
8. 防止 Codex 删除安全机制。

Phase 5、6、7 是主要负责人。

---

### 5. QA/Validation Agent

负责：

1. 每个 Phase 的完成标准。
2. 测试清单。
3. dry-run 验收。
4. 运行日志验收。
5. 失败复现路径。
6. 回归测试。
7. 判断是否可以进入下一 Phase。

每个 Phase 都需要参与。

---

### 6. Docs/Report Agent

负责：

1. 写 Phase 报告。
2. 维护文档。
3. 记录每个 Phase 做了什么。
4. 记录没做什么。
5. 记录已知问题。
6. 生成下一 Phase 的 Codex Prompt。
7. 保持项目长期可接续。

每个 Phase 都需要参与。

---

## 什么时候需要并行 Subagent？

适合并行的情况：

| 场景 | 是否适合并行 | 原因 |
|---|---:|---|
| Phase 0 文档体系搭建 | 一般不需要 | 单 Agent 即可完成，避免文档风格混乱。 |
| Phase 1 截图方案调研 | 可以轻度并行 | Capture Agent 设计方案，QA Agent 设计验收。 |
| Phase 2 数据集设计 | 适合并行 | Vision Agent 设计数据集，Capture Agent 设计采集，QA Agent 设计验收。 |
| Phase 3 YOLO 训练 | 适合并行 | Vision Agent 训练，QA Agent 评估，Docs Agent 写报告。 |
| Phase 5 坐标映射 | 适合并行 | Capture Agent 查坐标，Safety Agent 查 gate，QA Agent 设计验证。 |
| Phase 6/7 真实控制 | 必须多 Agent 审查 | Control/Safety Agent 和 QA Agent 必须参与，避免危险行为。 |

---

## 哪些任务适合 Agent Team 互相讨论？

适合讨论的问题：

1. **截图像素坐标如何映射到鼠标坐标。**
2. **AIMLAB 全屏时是否需要窗口前台 gate。**
3. **YOLO 置信度阈值如何设置。**
4. **真实鼠标移动前需要哪些安全条件。**
5. **点击前是否需要二次确认目标仍在原位置。**
6. **采集数据时是否自动保存负样本。**
7. **run logs 应该记录哪些字段。**
8. **某个 Phase 是否已经满足进入下一 Phase 的标准。**

不适合讨论的问题：

1. 很小的文档改动。
2. 创建目录。
3. 修改 README 小段文字。
4. 单一拼写修复。
5. Phase 0 中无核心逻辑的初始化任务。

---

# 5. Skills 规划

Phase 0 建议直接创建以下 6 个 Skill 文档。它们现在只是**规则和指导文档**，不是代码。

## Skills 总览

| Skill 名称 | 触发场景 | 指导 Codex 做什么 | Phase 0 是否创建 |
|---|---|---|---|
| `aiaim-phase-planner` | 每次开始新 Phase 或拆任务时 | 检查 Phase 边界、目标、完成标准、禁止事项 | 是 |
| `aiaim-yolo-dataset` | Phase 2/3 涉及数据集和 YOLO 时 | 规范截图、标注、YOLO 数据结构、训练/验证拆分 | 是 |
| `aiaim-coordinate-calibration` | Phase 5 以后涉及坐标映射时 | 区分截图坐标、屏幕坐标、DPI、鼠标坐标 | 是 |
| `aiaim-safety-click-gates` | Phase 5/6/7 涉及控制和点击时 | 约束 dry-run、安全 gate、真实移动、真实点击 | 是 |
| `aiaim-phase-report` | 每个 Phase 完成时 | 强制生成 Phase 报告 | 是 |
| `aiaim-debug-runbook` | 遇到截图、YOLO、坐标、控制异常时 | 指导 Codex 记录问题、复现路径、排障顺序 | 是 |

---

## Skill 1：`aiaim-phase-planner`

路径：

```text
.agents/skills/aiaim-phase-planner/SKILL.md
