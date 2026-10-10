---
name: game-interaction-usability-eval
description: Evaluate game UI interaction usability from screenshots, prototypes, Figma pages, recordings, flowcharts, or written descriptions. Use when the user asks in Chinese or English to analyze, inspect, diagnose, review, or evaluate a game interface or interaction flow, especially triggers such as "分析界面", "检查界面", "评估 UI", "界面诊断", "分析交互", "UX Review", or "易用性评估". Produces player-centered observations, severity and confidence labels, concrete improvement suggestions, implementation difficulty, and optional brief or full UX review reports.
---

# 游戏交互易用性评估

## 使用原则

先理解设计目标，再评价问题。先客观描述“看到了什么”，再判断“可能有什么体验影响”。静态截图无法证明动效、音效、触觉、Hover、状态切换或隐藏交互是否存在；对无法确认的内容使用“建议确认是否已设计”“当前无法从素材判断”“若未设计，则建议补充”。

评估语言要像真实游戏 UX Review：专业、自然、玩家感受优先。避免 checklist 式堆理论，也避免只写“优化层级”“增强反馈”这类抽象建议。每条建议都说明调整对象、调整方式、原因、预期收益和实现难度。

## 输入确认

正式评估前，确认或从上下文提取这些信息：

- 输入素材：截图、原型、Figma、流程图、录屏或文字描述。
- 游戏类型：如 MOBA、RPG、FPS、卡牌、SLG、MMO、模拟经营、休闲、生存建造。
- 目标平台：手机竖屏、手机横屏、PC 键鼠、主机手柄、Steam Deck 或跨平台。
- 评估范围：单一界面、交互流程、系统模块或整体 UI 体系。
- 报告模式：简报模式或完整模式；未指定时默认完整模式。
- 已有设计说明：如震动、音效、动效、引导、Hover、自动折叠、后期快捷操作。
- 专项方向：HUD 战斗、新手引导、商业化、抽卡、MMO 信息疲劳、战斗操作、背包养成、多端适配等；未指定时做通用易用性评估。

若缺少关键素材或游戏类型、平台、范围会显著影响判断，先简短询问。若用户只想快速看问题，可先基于已知信息评估，并明确置信度限制。

## 工作流程

1. 确认输入信息与评估边界。
2. 客观描述界面现状：布局、区域、视觉风格、信息层级、交互路径。
3. 推测设计目标与产品策略：曝光、商业化、沉浸、效率、新手留存等。
4. 按十大维度评分。
5. 分析新手、中度、硬核玩家的阶段差异。
6. 逐维度诊断问题，标注严重性、置信度、理论依据、实现难度。
7. 对照行业成熟方案或同品类竞品范式。
8. 做问题优先级排序。
9. 输出具体优化建议。
10. 总结值得保留的亮点。
11. 总结界面策略倾向与下一步素材需求。

## 评估框架

需要详细评分维度、严重性定义、置信度标记、报告模板和措辞规则时，读取 `references/evaluation-framework.md`。

核心维度包括：可学习性、可操作性、信息架构、视觉可用性、反馈系统、容错与恢复、效率与流畅性、情境适应性、无障碍支持、情感化设计。

严重性使用 P0/P1/P2/P3。置信度使用：确认、疑似、待确认。实现难度使用：低、中、高，并补充性能、多端适配和版本推进风险。

## 输出要求

简报模式包含：输入信息确认、界面现状概述、核心问题 Top 列表、总结建议。

完整模式包含：输入信息确认、客观描述、十大维度评分、玩家阶段差异、逐维度诊断、行业对比、优先级矩阵、亮点保留、总结与下一步、界面策略倾向总结。

无论哪种模式，都至少保留两类内容：一是客观观察，二是可执行建议。不要只输出评分表。
