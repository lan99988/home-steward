# Home Steward Agent

## 项目 Skills 总览

本项目预配置了两类 Skill，团队成员可直接使用 `/<skill-name>` 调用。

---

## 🎯 产品/市场 Skills（项目自带）

| Skill | 用途 | 调用方式 |
|-------|------|---------|
| **customer-research** | 用户研究、竞品声音挖掘、VOC 分析 | `/customer-research` |
| **competitor-profiling** | 深度竞品画像与对标分析 | `/competitor-profiling` |
| **competitors** | 竞品对比页面与竞争分析 | `/competitors` |
| **pricing** | 定价策略、分层、付费模式设计 | `/pricing` |
| **product-marketing** | 产品市场策略与定位 | `/product-marketing` |
| **content-strategy** | 内容策略规划 | `/content-strategy` |
| **marketing-plan** | 营销计划制定 | `/marketing-plan` |
| **launch** | 产品发布策略 | `/launch` |
| **docx** | Word 文档生成 | `/docx` |
| **pdf** | PDF 文档生成 | `/pdf` |
| **pptx** | PPT 演示文稿生成 | `/pptx` |
| **xlsx** | Excel 表格生成 | `/xlsx` |

## 🛠️ 开发工作流 Skills（全局，已绑定到项目）

| Skill | 用途 | 调用方式 |
|-------|------|---------|
| **brainstorming** | 创意工作前必用——探索用户意图、需求与设计方案 | `/brainstorming` |
| **writing-plans** | 编写结构化实施计划书，含任务分解与完整代码 | `/writing-plans` |
| **executing-plans** | 执行已有计划书，逐任务推进 | `/executing-plans` |
| **dispatching-parallel-agents** | 并行处理多个独立子任务 | `/dispatching-parallel-agents` |
| **systematic-debugging** | 系统性调试——先找根因再修 bug | `/systematic-debugging` |
| **test-driven-development** | TDD 流程——先写测试再实现 | `/test-driven-development` |
| **requesting-code-review** | 完成任务后请求代码审查 | `/requesting-code-review` |
| **receiving-code-review** | 收到代码审查反馈后按建议修改 | `/receiving-code-review` |
| **verification-before-completion** | 完成前验证——确认测试通过再提交 | `/verification-before-completion` |
| **finishing-a-development-branch** | 开发分支完成后选择合并/PR/清理 | `/finishing-a-development-branch` |
| **writing-skills** | 编写新的 Skill（供 Agent 自我进化使用） | `/writing-skills` |
| **find-skills** | 发现并安装更多 Skill 扩展能力 | `/find-skills` |
| **using-superpowers** | 会话开始时调用——确保所有 Skill 被正确使用 | `/using-superpowers` |
| **using-git-worktrees** | 使用 Git Worktree 隔离工作区 | `/using-git-worktrees` |



## 🎨 设计/UI Skills（impeccable）



| Skill | 用途 | 调用方式 |

|-------|------|---------|

| **impeccable** | 设计/迭代/审计前端界面——涵盖 UI 设计全流程 | `/impeccable` |

| craft | 端到端构建功能（从设计到代码） | `/impeccable craft <feature>` |

| shape | 写代码前规划 UX/UI 方案 | `/impeccable shape <feature>` |

| critique | UX 设计评审（含启发式评分） | `/impeccable critique <target>` |

| audit | 技术质量检查（无障碍/性能/响应式） | `/impeccable audit <target>` |

| polish | 发布前最终质量检查 | `/impeccable polish <target>` |

| bolder | 让平淡的设计更大胆 | `/impeccable bolder <target>` |

| quieter | 调低过度刺激的设计 | `/impeccable quieter <target>` |

| distill | 简化设计，去除冗余 | `/impeccable distill <target>` |

| harden | 生产级加固（错误态/国际化/边界情况） | `/impeccable harden <target>` |

| animate | 添加意图驱动的动画效果 | `/impeccable animate <target>` |

| colorize | 为单色 UI 添加策略性色彩 | `/impeccable colorize <target>` |

| typeset | 改善排版层级和字体 | `/impeccable typeset <target>` |

| layout | 修复间距、节奏和视觉层级 | `/impeccable layout <target>` |

| delight | 添加个性和令人难忘的细节 | `/impeccable delight <target>` |

| clarify | 改进 UX 文案、标签和错误信息 | `/impeccable clarify <target>` |

| adapt | 适配不同设备和屏幕尺寸 | `/impeccable adapt <target>` |

| live | 浏览器内视觉变体模式 | `/impeccable live` |

| init | 初始化项目设计上下文 | `/impeccable init` |



> 首次使用前需运行 `/impeccable init` 初始化设计上下文。



## 🚀 gstack

本项目使用 **gstack** 工作流框架。gstack skills 已配置到项目设置中，团队成员可直接通过 `/` 命令使用。

### gstack 可用命令

| 命令 | 用途 |
|------|------|
| `/browse` | Web 浏览需求（代替 mcp__claude-in-chrome__* 工具） |
| `/review` | 代码审查 |
| `/qa` | QA 测试 |
| `/design-consultation` | 设计咨询 |
| `/ship` | 发布部署 |
| `/plan-eng-review` | 工程评审计划 |
| `/plan-ceo-review` | CEO 评审计划 |
| `/gstack-upgrade` | gstack 升级 |
| `/investigate` | 问题调查 |
| `/retro` | 回顾总结 |

### 重要规则

- **所有 Web 浏览需求**使用 `/browse` skill，绝不使用 `mcp__claude-in-chrome__*` 工具
- 如需更多 Skill，请使用 `/find-skills` 发现并安装

---

## 使用方式

在对话中输入 `/<skill-name>` 加上你的需求即可调用对应的 Skill。例如：

```
/brainstorming 现在要做设备发现功能，帮我设计实现方案
/systematic-debugging MQTT 连接不稳定，帮我排查
/writing-plans 帮我写一份 Phase 2 Skill 系统的实现计划
```

## Notes

- All Phases 1-3 complete: Test coverage (94%), frontend UI, voice control, Sanitizer, comfort engine, reminder system, LLM health check
- Next: Phase 4 (multi-user, device auto-discovery) / Phase 5 (self-evolution)
