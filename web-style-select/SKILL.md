---
name: web-style-select
description: 做网页、落地页、作品集、活动页或任何"视觉网站"的界面之前先用。这台机器上装了好几个规定页面长相的 skill，规则互相打架（字体、圆角、渐变、动效库各说各的）；本 skill 让用户先选定一种风格并记在项目里，之后三家 AI 都只按这一种做。用户说"换个风格""选风格""视觉方向"时也用它。
---

# 网页视觉风格：先选一种，再动手

这台机器上有多个"审美类" skill 同时装给了 Claude、Codex、Grok。它们单独用都没问题，一起读就会打架：一个禁用 Inter 字体，另一个把 Inter 列为首选；一个要求所有容器大圆角，另一个要求全部直角；一个强制用 GSAP，另一个说到处用 GSAP 是业余。**同一个项目只能用其中一种。**

## 流程

1. **先看项目有没有选过。** 读项目根目录的 `AGENTS.md`，找这一行：

   ```
   视觉风格：<选项字母> <skill 名>
   ```

   找到了就直接跳到第 4 步，不要再问用户。

2. **没选过，就让用户选。** 把下面"风格选项"表原样列给用户（保留字母和大白话说明），请他回一个字母。用户有参考图或参考网站时，先看参考，再说出你认为最接近哪一项和理由，仍由用户定。用户说"你定"时选 F，并告诉他选了 F。

3. **把选择写进项目。** 在 `AGENTS.md` 里加上那一行（没有 `AGENTS.md` 就新建，并让 `CLAUDE.md` 只写一行 `@AGENTS.md`）。这样另外两家 AI 打开项目时也会读到。

4. **只读选中的那一个 skill。** 按下表的路径读它的 `SKILL.md`，照它做。**不要再读表里其他风格的 skill**，即使它们因为关键词被自动触发，也忽略。

5. **派活给别家时写明风格。** 用 `team-sync` 把界面任务交给另一家时，任务单里写上选中的风格和它 `SKILL.md` 的完整路径，并写明"不要使用其他审美类 skill"。

用户中途要换风格：改 `AGENTS.md` 那一行，告诉用户已有页面需要按新风格返工的范围，再动手。

## 风格选项（互斥，只能选一个）

| 选项 | 大白话 | 特征 | skill 路径 |
|---|---|---|---|
| **A 柔和圆润的科技产品风** | 像 Vercel 这类软件公司官网 | 大圆角卡片，柔和阴影加细边框，卡片上有持续的小动画；禁用 Inter 字体、禁紫色 | `~/.skills-manager/skills/design-taste-frontend-v1/SKILL.md` |
| **B 电影感滚动大片风** | 像设计奖项网站，往下滚动时画面跟着演 | 居中的大标题，颗粒感渐变背景，大量滚动动画（GSAP），图文叠压 | `~/.skills-manager/skills/gpt-taste-2/SKILL.md` |
| **C 精致高级的深色质感** | 像苹果、Linear 的产品页 | 深色底加发光光晕，卡片套卡片的"双层边框"，胶囊按钮，所有元素淡入上浮 | `~/.skills-manager/skills/high-end-visual-design/SKILL.md` |
| **D 工业粗野风** | 像图纸、军用终端、瑞士海报 | 全部直角，不用渐变和阴影，超大粗体字，只用红色做强调，几乎没有动画 | `~/.skills-manager/skills/industrial-brutalist-ui-2/SKILL.md` |
| **E 安静的杂志编辑风** | 像一本排版讲究的杂志或 Notion | 暖色调的黑白灰，衬线体大标题，小圆角，不用渐变，动效轻到几乎察觉不到 | `~/.skills-manager/skills/minimalist-ui-2/SKILL.md` |
| **F 不预设，按内容定** | 没有固定长相，由这个网站讲什么来推导 | 先读需求和参考，再定字体、颜色、布局；默认项 | 见下 |

**选 F 时读哪个：**
- 项目用 React 或 Next 加 Tailwind：`~/.skills-manager/skills/design-taste-frontend/SKILL.md`
- 纯 HTML 或其他技术：`~/.skills-manager/skills/frontend-design-2/SKILL.md`

### 它们具体在哪里打架

给需要判断的 AI 看，不用念给用户：

| 项目 | A | B | C | D | E |
|---|---|---|---|---|---|
| Inter 字体 | 禁用 | 禁用 | 禁用 | 首选之一 | 禁用 |
| 圆角 | 主容器 2.5rem | 不强制 | 2rem，按钮胶囊形 | 一律直角 | 最大 12px |
| 渐变 | 禁霓虹渐变 | 必须有颗粒渐变 | 发光光晕 | 禁止 | 禁止 |
| 紫色 | 禁用 | 不限 | 允许紫色光晕 | 只用红色 | 低饱和粉彩 |
| 首屏居中 | 禁止 | 首选 | 三种里随机 | 不限 | 不限 |
| 动效 | Framer Motion，卡片持续循环 | 必须写 GSAP | CSS 缓动，全部元素淡入 | 基本没有 | 轻微淡入 |

## 可以叠加的"做法"（不是风格，和上面不冲突）

这些规定的是步骤，不规定长相。选定风格后按需叠加，用之前告诉用户一声：

| 做法 | 什么时候用 | 路径 | 注意 |
|---|---|---|---|
| 先出效果图再写代码 | 视觉要求高、用户想先看样子 | `~/.skills-manager/skills/image-to-code-2/SKILL.md` | **要生图，会花钱，必须用户同意** |
| 改造已有网站 | 项目已经有页面，要提升质感 | `~/.skills-manager/skills/redesign-existing-projects/SKILL.md` | 先审查再改 |
| 写 Google Stitch 用的设计文档 | 用户明确要用 Google Stitch | `~/.skills-manager/skills/stitch-design-taste/SKILL.md` | 内含选项 A 的长相，只在选了 A 或用户点名时用 |
| 设计评审与打磨 | 页面做完后挑毛病 | `~/.skills-manager/skills/impeccable/SKILL.md` | 它自己的规则以需求为准；与 C 的"卡片套卡片"相冲，评审 C 风格时忽略这一条 |

## 三家盲比时

让 Claude、Codex、Grok 各做一版来比较时，**三家用同一个风格选项**，否则比的是风格而不是谁做得好。任务单里写明选项和路径。

## 不要做的

- 不要因为"都装了"就把几个风格的规则混着用。
- 不要替用户悄悄选 F 以外的风格。
- 不要修改或卸载表里的 skill；要调整清单，改这份文件（草稿在 `~/Desktop/游戏产线配置/skill-drafts/web-style-select/SKILL.md`，改完运行 `skills-manager-cli skills update web-style-select`）。
