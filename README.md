<div align="center">

# 🐌 Home Steward Agent

**一个会自我优化的本地 AI 智能管家**

像一只蜗牛，每天都在家里修修改改——通过观察、学习和编程，不断优化家这个「项目」中各个子系统之间以及内部的联系。

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/26326Mm/home-steward?style=social)](https://github.com/26326Mm/home-steward)

---

[快速开始](#-快速开始) • [核心功能](#-核心功能) • [系统架构](#-系统架构) • [技术栈](#-技术栈) • [项目结构](#-项目结构) • [开发指南](#-开发指南) • [Roadmap](#-roadmap) • [贡献](#-贡献)

</div>

---

## 📖 项目简介

**Home Steward Agent** 是一个本地化部署的 AI 智能家居管家。不同于传统的智能家居系统（你配它做），Home Steward 会**观察、学习、主动优化**——它是一只蜗牛，每天在家里悄悄修修改改。

### 核心理念

| 原则 | 含义 |
|------|------|
| 🧠 **AI 原生** | LLM 是架构核心，不是附加组件。本地模型优先，云端模型作为脱敏后的增强选项 |
| 🛡️ **LLM 建议，不执行** | LLM 输出结构化意图，安全层翻译为确定性指令 |
| 📦 **Skill 系统** | 能力单元化——可写、可测、可装、可卸、可回滚、可共享 |
| 📐 **分层记忆** | 短期记忆(会话) → 中期记忆(周级摘要) → 长期记忆(用户画像)，越用越聪明 |
| 🔐 **隐私优先** | 所有数据本地处理，隐私数据不出网关 |
| 🏠 **家是一个项目** | 设备控制、环境管理、安防、日程等子项目通过 AI 持续优化它们之间的联系 |

### 与竞品对比

| 特性 | Home Assistant | SmartThings | Apple Home | **Home Steward** |
|------|:-------------:|:-----------:|:----------:|:----------------:|
| 开源 | ✅ | ❌ | ❌ | ✅ |
| 本地优先 | ✅ | ❌ | ✅ | ✅ |
| LLM 原生集成 | ❌ 桥接式 | ❌ | ❌ | ✅ **架构核心** |
| 自进化能力 | ❌ | ❌ | ❌ | ✅ **独有** |
| Skill 系统 | ❌ 蓝图/配置 | ✅ Apps | ❌ | ✅ **代码级 Skill** |
| 多用户 | ❌ 弱 | ✅ | ✅ | ✅ **设计级** |
| 记忆系统 | ❌ 仅有日志 | ❌ | ❌ | ✅ **三级记忆** |
| 隐私 + 云端混用 | ❌ | ❌ | ❌ | ✅ **脱敏许可制** |

---

## 🚀 快速开始

### 前置要求

- **Python 3.10+**
- **MQTT Broker**（可选，开发模式使用虚拟设备无需安装）
- **Ollama**（可选，装好后 AI 能力才会激活）

### 安装与运行

```bash
# 1. 克隆项目
git clone https://github.com/26326Mm/home-steward.git
cd home-steward

# 2. 安装依赖
cd backend
pip install -r requirements.txt

# 3. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. 打开浏览器
# → http://localhost:8000    前端仪表盘
# → http://localhost:8000/docs  API 文档
```

### 启动 AI 能力（可选）

```bash
# 安装 Ollama: https://ollama.com
ollama pull qwen3:7b
# 重启后端，AI 自动激活
```

系统首次启动时会自动探测你的硬件配置，推荐并部署最合适的 Qwen3 模型：

| 你的设备 | 推荐模型 |
|---------|---------|
| 树莓派 5 (8GB) | Qwen3-3B |
| NUC / 迷你主机 | Qwen3-7B |
| 旧 PC + GTX 1060 | Qwen3-14B |
| RTX 3090/4090 | Qwen3-35B |

### 使用 Docker（推荐）

```bash
docker compose up -d
# 访问 http://localhost:3000
```

---

## 🎯 核心功能

### 🏠 设备控制

支持通过自然语言控制设备，快速通道（纯规则，<500ms）处理精确指令，标准通道（本地 LLM）处理模糊意图。

```
"打开客厅灯" → ✅ 快速通道匹配 → 灯亮了
"空调调到26度" → ✅ 快速通道匹配 → 26°C
"温馨一点" → 🔄 标准通道(需 LLM) → 灯光变暖 + 空调调温
"好冷啊" → ❌ IntentGate 过滤 → 不执行(非指令)
```

### 🧩 Skill 系统

Skill 是自包含的能力单元，可以安装、卸载、版本管理、回滚。

```
skills/
├── built-in/              # 内置 Skill
│   └── device-control/    # 设备控制
│       ├── SKILL.md       # 元数据声明
│       ├── main.py        # 实现代码
│       └── tests/         # 测试用例
└── user-installed/        # 用户安装的 Skill
```

**Skill 生命周期**: 草稿 → 沙箱测试 → 用户审批 → 灰度部署 → 生产 → 健康监测 → 自动修复

### 📋 记忆系统

| 记忆类型 | 范围 | 存储 | 用途 |
|---------|:----:|:----:|------|
| 短期记忆 | 当前会话 (50 条) | 内存 | 上下文理解 |
| 中期记忆 | 周级行为模式 | JSON 文件 | 习惯学习 |
| 长期记忆 | 用户画像 | JSON + ChromaDB | 个性化服务 |

### 🛡️ 安全防护

```
用户输入 → IntentGate(非指令过滤) → 三级通道 → FormalGuard(数学约束)
          ↓                                              ↓
      "好冷啊"→ 不执行                             温度>30°C → 拒绝
```

### 🔄 自进化闭环

系统通过健康监测追踪每个 Skill 的表现，低分 Skill 自动停用并尝试修复。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    📱 表现层 (Next.js PWA)                     │
│    仪表盘 · 设备控制 · Skill管理 · 记忆查看 · 健康状态         │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                  🧠 Agent Core (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LLM 推理引擎                                          │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐   │   │
│  │  │快速通道  │ │标准通道  │ │深度通道  │ │混合调度器 │   │   │
│  │  │(规则)   │ │(小模型) │ │(大模型) │ │(隐私分界) │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └──────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Skill 运行│ │冲突仲裁器 │ │健康监测  │ │回滚沙箱   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │短期记忆  │ │中期记忆  │ │长期记忆  │ │持久化     │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  ⚙️ 执行层                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 安全执行层 · FormalGuard · IntentGate · 审计日志       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 设备抽象层 · MQTT 驱动 · 状态缓存 · 设备发现服务       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ MQTT
┌──────────────────────────▼──────────────────────────────────┐
│            🗄️ 基础设施                                         │
│        MQTT Broker · SQLite → PostgreSQL · ChromaDB            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **后端框架** | Python FastAPI | 原生 async, 自动 API 文档, WebSocket |
| **设备通信** | MQTT (paho-mqtt) | 设备控制事实标准，发布/订阅模式 |
| **数据库** | SQLAlchemy + SQLite | 平滑迁移到 PostgreSQL |
| **向量存储** | ChromaDB | 轻量级语义检索 |
| **AI 推理** | Ollama + Qwen3 | 0.5B ~ 35B 自动适配硬件 |
| **前端** | HTML/CSS/JS → Next.js | 渐进式增强 |
| **容器化** | Docker Compose | 一键部署 |
| **语音** | Web Speech API → Whisper | 渐进增强 |

---

## 📁 项目结构

```
home-steward/
├── backend/                     # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                 # REST API 路由
│   │   ├── core/                # 核心配置 & 数据库
│   │   ├── execution/           # 执行层（设备/MQTT/安全）
│   │   ├── llm/                 # LLM 推理引擎
│   │   ├── memory/              # 记忆系统
│   │   ├── skill/               # Skill 管理系统
│   │   ├── user/                # 多用户管理
│   │   ├── models/              # 数据库模型
│   │   └── main.py              # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # 前端界面
│   └── index.html               # 仪表盘（含设备面板+健康监控）
├── skills/                      # Skill 仓库
│   ├── built-in/                # 内置 Skill
│   └── verified-patterns/       # 已验证的模板代码
├── docs/                        # 文档
│   ├── ARCHITECTURE.md          # 完整架构设计（8 大问题解决方案）
│   ├── ARCHITECTURE_OVERVIEW.md # 系统架构总览
│   ├── COMPETITIVE_ANALYSIS.md  # 竞品分析报告
│   └── superpowers/plans/       # 实施计划书
├── docker-compose.yml           # Docker 编排
├── CLAUDE.md                    # AI 助手配置 + Skill 索引
└── .reasonix/skills/            # 24 个 Skills（开发 + 产品/市场）
```

---

## 📜 文档索引

| 文档 | 说明 | 适合读者 |
|------|------|---------|
| `docs/ARCHITECTURE_OVERVIEW.md` | 系统架构总览（9 个视图） | 所有人 |
| `docs/ARCHITECTURE.md` | 全量架构设计（8 个核心问题解决方案） | 技术决策者 |
| `docs/COMPETITIVE_ANALYSIS.md` | 竞品格局分析（开源+商业+AI 新兴赛道） | 产品和战略 |
| `docs/superpowers/plans/*.md` | 结构化的实施计划书（44 步任务分解） | 开发者 |
| `CLAUDE.md` | AI 开发助手配置 + 24 个 Skill 索引 | 开发者 |

---

## 🗺️ Roadmap

```
Phase 1 (第 1-3 周):   🐌 蜗牛起步      ✅ 已完成
  浏览器能控制虚拟设备 + 硬件探测自动部署 LLM

Phase 2 (第 4-6 周):   🐌 学会技能      📝 进行中
  Skill 系统 — 运行时/仓库/冲突仲裁/回滚沙箱/健康监测

Phase 3 (第 7-10 周):  🐌 长出大脑      ⏳ 待开始
  LLM 三级通道 + 分层记忆系统 + 冷启动加速

Phase 4 (第 11-13 周): 🐌 认识家人      ⏳ 待开始
  多用户管理 + 设备自动发现

Phase 5 (第 14-17 周): 🐌 自我进化      ⏳ 待开始
  Agent 自写 Skill + 健康监测自动修复 + 主动进化
```

---

## 🤝 贡献

欢迎贡献！无论是代码、文档还是反馈。

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交改动 (`git commit -m 'feat: 添加某个特性'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 项目 Skills

本项目配置了 24 个 AI 开发 Skills（见 `CLAUDE.md`），团队成员可直接通过 `/<skill-name>` 调用：

```
/ brainstorming       # 创意设计前必用
/ writing-plans      # 写实施计划
/ systematic-debugging # 系统性调试
/ test-driven-development # TDD 流程
/ customer-research  # 用户研究
/ pricing            # 定价策略
... 以及更多
```

---

## 📄 许可证

[Apache License 2.0](LICENSE)

---

<div align="center">

**🐌 Home Steward Agent** — 让家越来越懂你

</div>
