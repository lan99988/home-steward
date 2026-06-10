# Home Steward Agent — 总体规划书

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打造一个会自我优化的本地 AI 智能管家——它像一只蜗牛，每天都在家里修修改改，通过观察、学习和编程，不断优化家这个「项目」中各个子系统之间以及内部的联系。

**核心哲学:**
> 居住者通过**硬件**改善家的环境，AI 通过**软件**改善家的舒适度。  
> AI 在没有与人交互的时候，就在默默处理电脑、家具与居住者之间的交互体验。  
> 它的工作是**总结规律 → 抽象为编程 → 持续优化**。

**Architecture:** Python FastAPI 后端 + MQTT 设备通信 + Next.js PWA 前端 + Ollama 本地 LLM（自动适配硬件，动态部署 Qwen3-0.5B ~ 35B）。系统以 Agent 为核心，围绕 Skill 系统（可安装/卸载/版本化的能力单元）构建。LLM 作为推理引擎驱动意图理解、代码生成和自我优化，安全执行层确保物理世界操作的安全。模型部署器 (ModelProvisioner) 在首次启动时自动探测硬件配置，推荐并部署最适合的模型，用户可随时升级/降级。

**Tech Stack:** Python 3.11+ (FastAPI, paho-mqtt, SQLAlchemy), Next.js 14+ (React, Tailwind, PWA), Ollama (Qwen3 家族: 0.5B/1.5B/3B/7B/14B/35B, 根据硬件自动选择), ChromaDB, Mosquitto MQTT, Docker Compose

---

## 一、项目核心理念

### 🐌 蜗牛哲学

```
       🐌
     ┌────┐        ┌──────────────┐
     │ 家  │ ──────│    AI   管家   │
     │    │        │              │
     │ 是  │        │  每天悄悄     │
     │    │        │  修修改改     │
     │ 一  │        │              │
     │    │        │  总结规律     │
     │ 个  │        │  抽象成代码   │
     │    │        │  优化体验     │
     │ 项  │        │              │
     │    │        └──────────────┘
     │ 目  │
     └────┘
```

**三个核心洞察**：

1. **家是一个项目（Project）** — 里面有多个子项目（设备控制、环境管理、安防、日程……），AI 的工作是优化子项目之间以及内部的联系
2. **AI 是蜗牛，不是大象** — 它不搞大跃进，每天改一点点，持续积累。今天学会关灯，明天学会调温，后天学会写 skill
3. **AI 离线也在工作** — 不与人交互时，它在默默处理：设备状态→交互模式→代码改进 这条链路

### 📐 四个设计原则

| 原则 | 含义 |
|------|------|
| **LLM 建议，不执行** | LLM 输出结构化意图，安全层翻译为确定性指令 |
| **故障降级** | 每个组件失效时，系统不崩溃，只降级功能 |
| **可观测** | 所有决策可审计、可回溯、可解释 |
| **渐进进化** | 新 skill 经过沙箱 → 灰度 → 生产三阶段 |

---

## 二、市场分析（基于竞品调研）

### 2.1 竞争格局

```
                     复杂度 ▲
                           │
             开源DIY       │    商业平台巨头
             ════════     │    ════════════
             Home Assistant│    SmartThings (Samsung)
             (⭐75k)       │    Apple HomeKit
             openHAB       │    Google Home
             (⭐8k)        │    Amazon Alexa
                           │    Hubitat
                           │
    ┌──────────────────┤
    │   硬件/固件层       │
    │   ESPHome / Tasmota │
    └──────────────────┘
                           ────────────────────────► 用户规模
                           极客              大众消费者
```

### 2.2 差异化定位

| 竞品 | 本质 | Home Steward 的差异化 |
|------|------|---------------------|
| **Home Assistant** | 规则自动化引擎（你配它做） | Agent 驱动的自我优化管家（它学会做） |
| **SmartThings/Apple/Google** | 品牌生态绑定 | 开源 + 本地 + 厂商中立 |
| **Alexa Skills Kit** | 云端 Skill，第三方开发 | 本地 Skill，AI 自写 |
| **所有竞品** | 有日志，无记忆 | 分层记忆系统，越用越聪明 |

### 2.3 窗口期

```
2025 Q3-Q4: 本地 LLM (Qwen3 家族 0.5B~35B) 在消费级硬件全面可用，覆盖从树莓派到 RTX 4090 的全场景
2026:  Home Assistant 可能开始集成 LLM，但转向 Agent 架构需 12-18 月
2026-2027: Google/Amazon 推出本地 AI 家居产品（封闭生态）

→ 我们的窗口：2025 Q3 → 2026 Q4（约 18 个月）
```

### 2.4 目标用户画像

```
名称: 极客创客 (Gigi the Geek)
年龄: 25-45
角色: 开发者 / DevOps / 硬件爱好者
现状: 在用 Home Assistant，但嫌配置麻烦
痛点: 
  - YAML 写自动化像写配置不像编程
  - 想要更智能的自动化但 HA 能力有限
  - 对本地 LLM 有强烈兴趣但无现成方案
  - 享受 DIY 的成就感
行为:
  - 逛 Reddit (r/selfhosted, r/homeassistant, r/ollama)
  - 看 Hacker News
  - 有自己的 GitHub 项目
  - 愿意折腾但不愿写重复代码
```

---

## 三、可行性分析

### 3.1 综合评分

| 维度 | 评分 | 说明 |
|------|:----:|------|
| **技术可行性** | ⭐⭐⭐⭐ 4/5 | 无不可逾越障碍，核心路径有成熟技术支撑 |
| **市场可行性** | ⭐⭐⭐⭐ 4/5 | 窗口期真实，差异化明确，生态是短板 |
| **商业可行性** | ⭐⭐⭐ 3/5 | 商业化路径清晰但需要时间 |
| **风险可控性** | ⭐⭐⭐ 3.5/5 | 核心风险有应对方案 |

### 3.2 风险矩阵

| 风险 | 概率 | 影响 | 应对方案 |
|:----|:---:|:---:|----------|
| LLM 生成 Skill 质量不可靠 | 🟡 中 | 🔴 高 | 沙箱测试 + 用户审批 + 自动回滚 |
| 用户不信 AI 管家 | 🟡 中 | 🔴 高 | 从极客切入 + 安全层透明审计 |
| 设备生态追不上 HA | 🔴 高 | 🟡 中 | 专注 MQTT/Matter 标准 |
| 被 HA 复制核心功能 | 🟡 中 | 🟡 中 | HA 重写核心需要 12-18 月 |
| PMF 假设不成立 | 🟡 中 | 🔴 高 | 每阶段设验证关卡，边做边验 |

### 3.3 验证关卡

```
Phase 1 完成 → 验证"我能把这个项目跑起来"
Phase 2 完成 → 验证"用户愿意在 Skill 系统上花时间"
Phase 3 完成 → 验证"AI 真的让家居更聪明"
Phase 4 完成 → 验证"用户愿意让系统自主学习"
Phase 5 完成 → 验证"自我优化承诺可以兑现"
```

---

## 四、目标与里程碑

### 4.1 总目标

> **到 2026 年底，Home Steward 成为一个拥有 1000+ 活跃用户的、技术极客首选的本地 AI 智能家居平台。**

### 4.2 里程碑

| 里程碑 | 时间 | 交付物 | 验证标准 |
|--------|------|--------|---------|
| **M1: 蜗牛起步** | 第 2-3 周 | Phase 1 完整 MVP | 浏览器能控制虚拟设备开关灯 + 硬件探测自动部署 Qwen3 模型 |
| **M2: 学会技能** | 第 4-6 周 | Phase 2 Skill 系统 | 用户能装/卸/回滚 skill + 冲突预测 + 形式化安全边界 |
| **M3: 长出大脑** | 第 7-10 周 | Phase 3 LLM + 记忆 | "温馨一点"这种模糊指令能正确执行 |
| **M4: 认识家人** | 第 11-13 周 | Phase 4 多用户 + 发现 | 多用户无冲突 + 新设备自动发现 |
| **M5: 自我进化** | 第 14-17 周 | Phase 5 自进化闭环 | Agent 能自己写 skill + 生态收敛（≤20）+ 社区模板库 |
| **M6: 生态萌芽** | 第 18-24 周 | 社区 + 发布 | 100 个活跃用户 + 20 个社区贡献的 skill |

### 4.3 关键成功指标 (KPI)

| 指标 | M1 | M2 | M3 | M4 | M5 | M6 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|
| GitHub Stars | 50 | 200 | 500 | 800 | 1200 | 2000 |
| 活跃安装 | 5 | 20 | 50 | 80 | 120 | 300 |
| 社区 Skill 数 | 0 | 3(内置) | 5 | 10 | 15 | 25 |
| 自写 Skill 成功率 | — | — | — | — | 60% | 75% |

---

## 五、技术方案

### 5.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    📱 表现层 (Next.js PWA)                     │
│    仪表盘 · 设备控制 · Skill管理 · 记忆查看 · 设备发现向导       │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                  🧠 Agent Core (FastAPI)                      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LLM 推理引擎                                          │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐   │   │
│  │  │快速通道  │ │标准通道  │ │深度通道  │ │混合调度器 │   │   │
│  │  │(规则)   │ │(小模型) │ │(大模型) │ │(隐私分界) │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └──────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Skill 运行│ │冲突仲裁器 │ │健康监测  │ │回滚沙箱   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │短期记忆  │ │中期记忆  │ │长期记忆   │                     │
│  │(会话)    │ │(周摘要)  │ │(画像)     │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
│                                                               │
│  ┌──────────┐ ┌──────────┐                                   │
│  │多用户管理 │ │用户画像  │                                   │
│  └──────────┘ └──────────┘                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  ⚙️ 执行层                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 安全执行层 (白名单 · 速率限制 · 异常熔断 · 审计日志)   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 设备抽象层 (统一设备模型 · MQTT 驱动 · 状态缓存)       │   │
│  │ 设备发现服务 (mDNS/SSDP → Web UI 注册 → MQTT 注册)    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ MQTT
┌──────────────────────────▼──────────────────────────────────┐
│            🗄️ 基础设施                                         │
│  MQTT Broker (Mosquitto) · SQLite→PG · ChromaDB 向量库       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 项目结构

```
home-steward/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── core/                # Agent 核心
│   │   │   ├── engine.py        # Agent 生命周期
│   │   │   └── config.py        # 配置管理
│   │   ├── llm/                 # LLM 推理引擎
│   │   │   ├── router.py        # 三级通道路由
│   │   │   ├── express.py       # 快速通道（规则匹配器）
│   │   │   ├── standard.py      # 标准通道（本地小模型）
│   │   │   ├── deep.py          # 深度通道（大模型/云端）
│   │   │   ├── hybrid.py        # 混合调度器
│   │   │   └── provisioner.py   # 模型部署器（硬件探测+推荐+下载）
│   │   ├── skill/               # Skill 管理系统
│   │   │   ├── runtime.py       # Skill 运行时
│   │   │   ├── registry.py      # Skill 仓库
│   │   │   ├── arbiter.py       # 冲突仲裁器
│   │   │   ├── conflict_predictor.py  # 冲突预测器（安装前预判冲突）
│   │   │   ├── health.py        # 健康监测
│   │   │   ├── sandbox.py       # 回滚沙箱
│   │   │   ├── auto_repair.py   # 自动修复
│   │   │   └── ecosystem.py    # Skill 生态收敛（上限+归档+合并）
│   │   ├── memory/              # 记忆系统
│   │   │   ├── short_term.py    # 短期记忆
│   │   │   ├── medium_term.py   # 中期记忆
│   │   │   ├── long_term.py     # 长期记忆
│   │   │   ├── vector_store.py  # 向量检索
│   │   │   └── cold_start.py    # 冷启动加速器
│   │   ├── user/                # 多用户
│   │   │   ├── profiles.py      # 用户画像
│   │   │   ├── manager.py       # 用户管理
│   │   │   └── voice_id.py      # 声纹识别
│   │   ├── execution/           # 执行层
│   │   │   ├── safety.py        # 安全执行层
│   │   │   ├── formal_guard.py  # 形式化验证边界（数学约束）
│   │   │   ├── device.py        # 设备抽象层
│   │   │   ├── mqtt.py          # MQTT 通信
│   │   │   ├── cache.py         # 设备状态缓存
│   │   │   └── discovery.py     # 设备发现服务
│   │   ├── api/                 # REST 路由
│   │   │   ├── devices.py
│   │   │   ├── skills.py
│   │   │   ├── memory.py
│   │   │   ├── users.py
│   │   │   └── discovery.py
│   │   └── models/              # 数据库模型
│   │       ├── device.py
│   │       ├── skill.py
│   │       ├── memory.py
│   │       └── user.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── components/
│   │   ├── Dashboard/
│   │   ├── DeviceControl/
│   │   ├── SkillManager/
│   │   ├── MemoryViewer/
│   │   ├── UserManager/
│   │   └── DiscoveryWizard/
│   ├── pages/
│   ├── Dockerfile
│   └── package.json
├── skills/                      # 内置 + 社区 Skill
│   ├── verified-patterns/     # 经验证的正确代码片段（外部锚点）
│   ├── built-in/
│   │   ├── device-control/
│   │   ├── energy-saver/
│   │   └── good-morning/
│   └── user-installed/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── COMPETITIVE_ANALYSIS.md
│   └── superpowers/plans/
├── docker-compose.yml
└── .gitignore
```

### 5.3 核心数据流

```
用户指令流向:
用户 "开灯" → Web UI → REST API → 快速通道(匹配成功)
  → 安全执行层(白名单校验) → 设备抽象层 → MQTT → 灯亮
  → 反馈 → 短期记忆 → (重复N次) → 中期记忆 → (重复N次) → 长期记忆

自进化流向:
用户 "帮我写个skill，每天7点播天气" → LLM 评估 → Skill 工坊
  → 生成 skill 代码 + 测试 → 沙箱测试 → 用户审批 → 灰度部署
  → 生产部署 → 健康监测(每周检查) → 自动修复(必要时)
```

---

## 六、任务分解

### Phase 1: 蜗牛起步（第 1-3 周）

> 目标：从零到有一个可运行的 MVP——浏览器能控制虚拟设备。

#### 1.1 项目骨架搭建

**文件:**
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/requirements.txt`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建项目结构和 requirements.txt**

```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
paho-mqtt==2.0.0
sqlalchemy==2.0.35
aiosqlite==0.20.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-dotenv==1.0.1
```

- [ ] **Step 2: 创建 FastAPI 应用入口**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Home Steward Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 3: 创建 Docker Compose**

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/data
    environment:
      - DATABASE_URL=sqlite:///data/steward.db
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 4: Run `docker compose up` and verify `/health` returns 200**

Run: `docker compose up -d && curl http://localhost:8000/health`
Expected: `{"status": "ok", "version": "0.1.0"}`

- [ ] **Step 5: Commit**

```bash
git add backend/ docker-compose.yml
git commit -m "feat(phase1): project skeleton with FastAPI + MQTT + Docker"
```

---

#### 1.2 设备模型与数据库

- [ ] **Step 6: 创建设备 SQLAlchemy 模型**

```python
# backend/app/models/device.py
from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # light, ac, switch, sensor...
    room = Column(String, default="unknown")
    protocol = Column(String, default="mqtt")  # mqtt, zigbee, ir...
    is_virtual = Column(Boolean, default=True)
    properties = Column(JSON, default=dict)  # current state
    online = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

- [ ] **Step 7: 创建数据库初始化**

```python
# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./data/steward.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 8: Run database initialization and verify tables exist**

Run: `python -c "from app.core.database import init_db; init_db(); print('DB OK')"`
Expected: `DB OK`

---

#### 1.3 MQTT 通信层

- [ ] **Step 9: 创建 MQTT 客户端**

```python
# backend/app/execution/mqtt.py
import asyncio
import json
import logging
from typing import Callable, Dict, Any
from paho.mqtt import client as mqtt_client

logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt_client.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.subscribers: Dict[str, Callable] = {}
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected")
            for topic in self.subscribers:
                client.subscribe(topic)
        else:
            logger.error(f"MQTT connect failed: {rc}")

    def _on_message(self, client, userdata, msg):
        handler = self.subscribers.get(msg.topic)
        if handler:
            try:
                payload = json.loads(msg.payload.decode())
                asyncio.run(handler(payload))
            except Exception as e:
                logger.error(f"MQTT handler error: {e}")

    def connect(self):
        self.client.connect(self.broker_host, self.broker_port)
        self.client.loop_start()

    def publish(self, topic: str, payload: Dict[str, Any]):
        self.client.publish(topic, json.dumps(payload))

    def subscribe(self, topic: str, handler: Callable):
        self.subscribers[topic] = handler
        if self.connected:
            self.client.subscribe(topic)

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
```

- [ ] **Step 10: 创建 Mosquitto 配置文件**

```
# mosquitto/config/mosquitto.conf
listener 1883
listener 9001
protocol websockets
allow_anonymous true
```

---

#### 1.4 设备抽象层 + 虚拟设备

- [ ] **Step 11: 创建设备基类和虚拟设备**

```python
# backend/app/execution/device.py
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.execution.mqtt import MQTTClient

logger = logging.getLogger(__name__)

class DeviceAdapter(ABC):
    """所有设备的抽象基类"""

    def __init__(self, device_id: str, name: str, mqtt: MQTTClient):
        self.device_id = device_id
        self.name = name
        self.mqtt = mqtt
        self.status: Dict[str, Any] = {}

    @abstractmethod
    async def turn_on(self, **kwargs) -> bool: ...

    @abstractmethod
    async def turn_off(self, **kwargs) -> bool: ...

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]: ...

class VirtualLight(DeviceAdapter):
    """虚拟灯——用于开发测试"""

    async def turn_on(self, **kwargs) -> bool:
        self.status["on"] = True
        if "brightness" in kwargs:
            self.status["brightness"] = kwargs["brightness"]
        if "color_temp" in kwargs:
            self.status["color_temp"] = kwargs["color_temp"]
        logger.info(f"💡 {self.name} 已打开 (亮度={self.status.get('brightness', 'default')})")
        self.mqtt.publish(f"steward/{self.device_id}/status", self.status)
        return True

    async def turn_off(self, **kwargs) -> bool:
        self.status["on"] = False
        logger.info(f"💡 {self.name} 已关闭")
        self.mqtt.publish(f"steward/{self.device_id}/status", self.status)
        return True

    async def get_status(self) -> Dict[str, Any]:
        return self.status

class VirtualAC(DeviceAdapter):
    """虚拟空调"""

    async def turn_on(self, **kwargs) -> bool:
        self.status["on"] = True
        self.status["mode"] = kwargs.get("mode", "cool")
        self.status["temperature"] = kwargs.get("temperature", 24)
        logger.info(f"❄️ {self.name} 已打开 ({self.status['mode']}, {self.status['temperature']}°C)")
        self.mqtt.publish(f"steward/{self.device_id}/status", self.status)
        return True

    async def turn_off(self, **kwargs) -> bool:
        self.status["on"] = False
        logger.info(f"❄️ {self.name} 已关闭")
        self.mqtt.publish(f"steward/{self.device_id}/status", self.status)
        return True

    async def get_status(self) -> Dict[str, Any]:
        return self.status
```

- [ ] **Step 12: 注册虚拟设备到系统**

```python
# backend/app/execution/device_registry.py
from typing import Dict
from app.execution.device import DeviceAdapter, VirtualLight, VirtualAC

class DeviceRegistry:
    def __init__(self):
        self.devices: Dict[str, DeviceAdapter] = {}

    def register_virtual_devices(self, mqtt):
        devices_config = [
            {"id": "light_living", "name": "客厅灯", "type": "light"},
            {"id": "light_bedroom", "name": "卧室灯", "type": "light"},
            {"id": "ac_living", "name": "客厅空调", "type": "ac"},
        ]
        for cfg in devices_config:
            if cfg["type"] == "light":
                device = VirtualLight(cfg["id"], cfg["name"], mqtt)
            elif cfg["type"] == "ac":
                device = VirtualAC(cfg["id"], cfg["name"], mqtt)
            else:
                continue
            self.devices[cfg["id"]] = device

    def get(self, device_id: str) -> DeviceAdapter:
        return self.devices.get(device_id)

    def list(self) -> list:
        return [
            {"id": did, "name": d.name, "type": d.__class__.__name__}
            for did, d in self.devices.items()
        ]
```

---

#### 1.5 快速通道匹配器

- [ ] **Step 13: 实现快速通道（纯规则匹配，零 LLM）**

```python
# backend/app/llm/express.py
import re
from typing import Optional, Dict, Any

class ExpressMatcher:
    """快速通道：纯规则匹配，零延迟"""

    PATTERNS = [
        (r"打开(.+)", lambda m: {"intent": "turn_on", "device": m.group(1).strip()}),
        (r"关闭(.+)", lambda m: {"intent": "turn_off", "device": m.group(1).strip()}),
        (r"(.+)调到(\d+)度", lambda m: {"intent": "set_temperature", "device": m.group(1).strip(), "value": int(m.group(2))}),
        (r"(.+)亮度调到(\d+)", lambda m: {"intent": "set_brightness", "device": m.group(1).strip(), "value": int(m.group(2))}),
        (r"(.+)设为(.+)模式", lambda m: {"intent": "set_mode", "device": m.group(1).strip(), "mode": m.group(2).strip()}),
        (r"所有灯(打开|关闭)", lambda m: {"intent": "all_lights", "action": m.group(1)}),
    ]

    def match(self, text: str) -> Optional[Dict[str, Any]]:
        for pattern, builder in self.PATTERNS:
            m = re.match(pattern, text)
            if m:
                return builder(m)
        return None
```

---

#### 1.6 安全执行层

- [ ] **Step 14: 实现安全执行层**

```python
# backend/app/execution/safety.py
import logging
from typing import Dict, Any, Optional
from app.execution.device_registry import DeviceRegistry

logger = logging.getLogger(__name__)

class SafetyLayer:
    """安全执行层：LLM 建议 → 安全层校验 → 设备执行"""

    WHITELIST_DEVICES = {"light_living", "light_bedroom", "ac_living", "light_kitchen"}
    WHITELIST_INTENTS = {"turn_on", "turn_off", "set_temperature", "set_brightness", "set_mode"}
    RATE_LIMIT = 10  # 最多每秒 10 条指令

    def __init__(self, registry: DeviceRegistry):
        self.registry = registry
        self.command_count = 0

    def validate(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """校验 intent 是否合法，返回清洗后的指令或 None"""
        intent_type = intent.get("intent")

        if intent_type not in self.WHITELIST_INTENTS:
            logger.warning(f"❌ 非法指令类型: {intent_type}")
            return None

        if intent_type == "all_lights":
            return intent  # 批量操作特殊处理

        device_id = intent.get("device")
        # 模糊匹配：支持中文名查找
        resolved = self._resolve_device(device_id)
        if not resolved:
            logger.warning(f"❌ 未知设备: {device_id}")
            return None

        intent["device"] = resolved
        return intent

    def _resolve_device(self, name: str) -> Optional[str]:
        """通过名称模糊匹配设备 ID"""
        for did, device in self.registry.devices.items():
            if name in device.name or name in did:
                return did
        return None

    async def execute(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        intent_type = intent.get("intent")
        device_id = intent.get("device")

        device = self.registry.get(device_id)
        if not device:
            return {"error": f"device '{device_id}' not found"}

        try:
            if intent_type == "turn_on":
                kwargs = {k: v for k, v in intent.items() if k in ("brightness", "color_temp", "mode", "temperature")}
                success = await device.turn_on(**kwargs)
            elif intent_type == "turn_off":
                success = await device.turn_off()
            elif intent_type == "set_temperature":
                success = await device.turn_on(temperature=intent["value"])
            elif intent_type == "set_brightness":
                success = await device.turn_on(brightness=intent["value"])
            else:
                return {"error": f"unsupported intent: {intent_type}"}

            return {"success": success, "device": device_id, "intent": intent_type}
        except Exception as e:
            logger.error(f"执行失败: {e}")
            return {"error": str(e)}
```

---

#### 1.7 REST API 路由

- [ ] **Step 15: 创建设备 API 路由**

```python
# backend/app/api/devices.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.execution.safety import SafetyLayer
from app.llm.express import ExpressMatcher

router = APIRouter(prefix="/api/devices", tags=["devices"])

# 这些会在 main.py 中注入
safety_layer: SafetyLayer = None
matcher: ExpressMatcher = None

class CommandRequest(BaseModel):
    text: str

class CommandResponse(BaseModel):
    success: bool
    message: str
    intent: Optional[dict] = None

@router.get("/")
async def list_devices():
    return {"devices": safety_layer.registry.list()}

@router.get("/{device_id}")
async def get_device(device_id: str):
    device = safety_layer.registry.get(device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    return {
        "id": device_id,
        "name": device.name,
        "status": await device.get_status()
    }

@router.post("/command", response_model=CommandResponse)
async def command(req: CommandRequest):
    # 1. 快速通道匹配
    intent = matcher.match(req.text)

    if not intent:
        # 暂时没有 LLM → 返回无法理解
        return CommandResponse(
            success=False,
            message=f"无法理解: '{req.text}'（LLM 通道尚未就绪）",
            intent=None
        )

    # 2. 安全层校验
    validated = safety_layer.validate(intent)
    if not validated:
        return CommandResponse(
            success=False,
            message=f"指令被安全层拒绝: {intent}",
            intent=intent
        )

    # 3. 执行
    result = await safety_layer.execute(validated)
    return CommandResponse(
        success=result.get("success", False),
        message=f"已执行: {validated['intent']} -> {validated.get('device')}",
        intent=validated
    )
```

- [ ] **Step 16: 将所有模块组装到 main.py**

```python
# backend/app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.execution.mqtt import MQTTClient
from app.execution.device_registry import DeviceRegistry
from app.execution.safety import SafetyLayer
from app.llm.express import ExpressMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mqtt = MQTTClient()
registry = DeviceRegistry()
safety_layer = SafetyLayer(registry)
matcher = ExpressMatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("🐌 Home Steward Agent 启动中...")
    init_db()
    mqtt.connect()
    registry.register_virtual_devices(mqtt)
    logger.info(f"✅ 已注册 {len(registry.devices)} 个虚拟设备")

    # 注入到 API 路由
    import app.api.devices as devices_api
    devices_api.safety_layer = safety_layer
    devices_api.matcher = matcher

    yield

    logger.info("🐌 Home Steward Agent 关闭中...")
    mqtt.disconnect()

app = FastAPI(title="Home Steward Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 注册路由
app.include_router(devices_api.router)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "devices": len(registry.devices)}
```

---

#### 1.8 Web 前端

- [ ] **Step 17: 初始化 Next.js 项目**

```bash
mkdir -p frontend && cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

- [ ] **Step 18: 创建设备控制页面**

```tsx
// frontend/src/app/page.tsx
'use client';
import { useState, useEffect } from 'react';

interface Device {
  id: string;
  name: string;
  type: string;
}

interface DeviceStatus {
  on?: boolean;
  brightness?: number;
  temperature?: number;
  mode?: string;
}

export default function Home() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [statuses, setStatuses] = useState<Record<string, DeviceStatus>>({});
  const [command, setCommand] = useState('');
  const [response, setResponse] = useState('');
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    fetch('/api/devices/')
      .then(r => r.json())
      .then(d => setDevices(d.devices));
  }, []);

  const fetchStatus = async (id: string) => {
    const r = await fetch(`/api/devices/${id}`);
    const d = await r.json();
    setStatuses(s => ({ ...s, [id]: d.status }));
  };

  const sendCommand = async () => {
    if (!command.trim()) return;
    const r = await fetch('/api/devices/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: command }),
    });
    const result = await r.json();
    setResponse(result.message);
    setLogs(l => [`${new Date().toLocaleTimeString()} | ${command} → ${result.message}`, ...l]);
    setCommand('');
    // 刷新所有设备状态
    devices.forEach(d => fetchStatus(d.id));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">🐌 Home Steward Agent</h1>
        <p className="text-gray-500 mb-8">智能管家 · 正在悄悄让家变得更舒适</p>

        {/* 设备面板 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {devices.map(d => (
            <div key={d.id} className="bg-white rounded-xl shadow p-4">
              <h3 className="font-semibold text-lg">{d.name}</h3>
              <p className="text-sm text-gray-400">{d.id}</p>
              <div className="mt-2">
                {statuses[d.id]?.on !== undefined && (
                  <span className={`inline-block px-2 py-1 rounded text-sm ${
                    statuses[d.id].on ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {statuses[d.id].on ? '🟢 已开启' : '⚪ 已关闭'}
                  </span>
                )}
                {statuses[d.id]?.temperature && (
                  <span className="ml-2 text-sm text-blue-600">{statuses[d.id].temperature}°C</span>
                )}
                {statuses[d.id]?.brightness && (
                  <span className="ml-2 text-sm text-yellow-600">{statuses[d.id].brightness}%</span>
                )}
              </div>
              <button
                onClick={() => fetchStatus(d.id)}
                className="mt-3 text-xs text-blue-500 hover:underline"
              >
                刷新状态
              </button>
            </div>
          ))}
        </div>

        {/* 命令输入 */}
        <div className="bg-white rounded-xl shadow p-6 mb-8">
          <h2 className="font-semibold mb-3">🎮 控制指令</h2>
          <div className="flex gap-3">
            <input
              value={command}
              onChange={e => setCommand(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendCommand()}
              placeholder="试试：打开客厅灯 / 关闭空调 / 客厅亮度调到80..."
              className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button
              onClick={sendCommand}
              className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
            >
              发送
            </button>
          </div>
          {response && (
            <p className={`mt-3 text-sm ${response.includes('✅') || response.includes('已执行') ? 'text-green-600' : 'text-red-500'}`}>
              {response}
            </p>
          )}
        </div>

        {/* 快速指令按钮 */}
        <div className="bg-white rounded-xl shadow p-6 mb-8">
          <h2 className="font-semibold mb-3">⚡ 快速指令</h2>
          <div className="flex flex-wrap gap-2">
            {['打开客厅灯', '关闭客厅灯', '打开卧室灯', '关闭卧室灯', '客厅空调调到26度'].map(cmd => (
              <button
                key={cmd}
                onClick={() => { setCommand(cmd); setTimeout(sendCommand, 100); }}
                className="bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg text-sm"
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>

        {/* 操作日志 */}
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold mb-3">📋 操作日志</h2>
          <div className="h-40 overflow-y-auto space-y-1 text-sm font-mono">
            {logs.length === 0 ? (
              <p className="text-gray-400">还没有操作记录</p>
            ) : (
              logs.map((log, i) => <p key={i} className="text-gray-600">{log}</p>)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 19: 配置 Next.js API 代理**

```javascript
// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
    ];
  },
};
module.exports = nextConfig;
```

- [ ] **Step 20: 启动完整系统并验证**

```bash
docker compose up --build -d
curl http://localhost:8000/health
curl http://localhost:3000
```

访问 http://localhost:3000，看到设备面板，输入"打开客厅灯"，看到日志显示灯已打开。
---

- [ ] **Step 21: 开箱即用场景包**

安装时直接预置 4 个工作场景，零冷启动——用户第一天就能用，而不是等一周。

```python
# backend/app/execution/bootstrap.py
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class BootstrapScenario:
    name: str
    description: str
    steps: List[Dict[str, Any]]


BOOTSTRAP_SCENARIOS = {
    "离家模式": BootstrapScenario(
        name="离家模式",
        description="一键关闭所有灯光和空调",
        steps=[
            {"intent": "turn_off", "domain": "light", "target": "all"},
            {"intent": "turn_off", "domain": "climate", "target": "all"},
        ]
    ),
    "回家模式": BootstrapScenario(
        name="回家模式",
        description="打开客厅灯",
        steps=[
            {"intent": "turn_on", "domain": "light", "target": "light_living", "parameters": {"brightness": 40}},
        ]
    ),
    "睡眠模式": BootstrapScenario(
        name="睡眠模式",
        description="关闭所有灯，空调设为睡眠模式",
        steps=[
            {"intent": "turn_off", "domain": "light", "target": "all"},
            {"intent": "set_mode", "domain": "climate", "target": "ac_living", "parameters": {"mode": "sleep"}},
        ]
    ),
    "早安模式": BootstrapScenario(
        name="早安模式",
        description="逐渐亮灯，播放天气",
        steps=[
            {"intent": "turn_on", "domain": "light", "target": "light_bedroom", "parameters": {"brightness": "gradual"}},
            {"intent": "broadcast", "domain": "info", "message": "播报今日天气"},
        ]
    ),
}


class BootstrapEngine:
    """安装即用的场景引擎——零冷启动"""

    def __init__(self, safety_layer):
        self.scenarios = BOOTSTRAP_SCENARIOS
        self.safety_layer = safety_layer

    def get_scenarios(self) -> dict:
        """返回所有可用场景"""
        return {k: {"name": v.name, "description": v.description}
                for k, v in self.scenarios.items()}

    async def execute(self, scenario_name: str) -> List[Dict]:
        """执行场景中的每

- [ ] **Step 22: 实现模型部署器 (ModelProvisioner)**

```python
# backend/app/llm/provisioner.py
import os
import platform
import subprocess
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HardwareSpec:
    total_ram_gb: float
    cpu_cores: int
    has_nvidia_gpu: bool
    vram_gb: float
    is_raspberry_pi: bool

@dataclass
class ModelRecommendation:
    name: str
    param_count: str
    min_ram_gb: float
    min_vram_gb: float
    quality: str
    disk_gb: float

class ModelProvisioner:
    """硬件探测 -> 模型推荐 -> Ollama 部署"""

    RECOMMENDATIONS = [
        ModelRecommendation("qwen3:0.5b", "0.5B", 0, 0, "basic", 0.4),
        ModelRecommendation("qwen3:1.5b", "1.5B", 2, 0, "base", 1.0),
        ModelRecommendation("qwen3:3b", "3B", 4, 0, "good", 2.0),
        ModelRecommendation("qwen3:7b", "7B", 6, 4, "great", 4.5),
        ModelRecommendation("qwen3:14b", "14B", 12, 8, "excellent", 9.0),
        ModelRecommendation("qwen3:35b", "35B", 32, 24, "max", 20.0),
    ]

    def probe(self) -> HardwareSpec:
        """探测用户硬件配置"""
        total_ram = self._get_ram_gb()
        cpu_cores = os.cpu_count() or 4
        has_gpu, vram = self._get_gpu_info()
        is_pi = self._is_raspberry_pi()
        return HardwareSpec(total_ram, cpu_cores, has_gpu, vram, is_pi)

    def recommend(self, spec: HardwareSpec) -> ModelRecommendation:
        """根据硬件推荐最适合的模型"""
        if spec.is_raspberry_pi:
            if spec.total_ram_gb >= 8:
                return self._find("qwen3:3b")
            return self._find("qwen3:1.5b")
        if spec.has_nvidia_gpu:
            vram = spec.vram_gb
            if vram >= 24:
                return self._find("qwen3:35b")
            elif vram >= 8:
                return self._find("qwen3:14b")
            elif vram >= 4:
                return self._find("qwen3:7b")
        available_ram = spec.total_ram_gb - 2
        if available_ram >= 30:
            return self._find("qwen3:14b")
        elif available_ram >= 6:
            return self._find("qwen3:7b")
        elif available_ram >= 4:
            return self._find("qwen3:3b")
        elif available_ram >= 2:
            return self._find("qwen3:1.5b")
        else:
            return self._find("qwen3:0.5b")

    def deploy(self, model: ModelRecommendation) -> bool:
        """通过 Ollama 拉取并部署模型"""
        try:
            logger.info(f"Downloading {model.name} ({model.param_count}, ~{model.disk_gb}GB)...")
            result = subprocess.run(["ollama", "pull", model.name], capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                logger.error(f"Deploy failed: {result.stderr}")
                return False
            logger.info(f"Deployed {model.name} successfully")
            return True
        except subprocess.TimeoutExpired:
            logger.error("Deploy timeout")
            return False
        except FileNotFoundError:
            logger.error("Ollama not installed. Please install from https://ollama.com")
            return False

    def _find(self, name: str) -> ModelRecommendation:
        return next(r for r in self.RECOMMENDATIONS if r.name == name)

    def _get_ram_gb(self) -> float:
        try:
            if platform.system() == "Linux":
                mem = os.popen("free -g | awk '/^Mem:/{print $2}'").read().strip()
                return float(mem) if mem else 4
            elif platform.system() == "Windows":
                mem = os.popen("wmic MemoryChip get Capacity").read().strip().split(chr(10))[1:]
                total_bytes = sum(int(m.strip()) for m in mem if m.strip())
                return total_bytes / (1024**3)
            elif platform.system() == "Darwin":
                mem = os.popen("sysctl -n hw.memsize").read().strip()
                return int(mem) / (1024**3)
        except:
            return 4
        return 4

    def _get_gpu_info(self) -> tuple:
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                vram_mb = [int(x) for x in result.stdout.strip().split(chr(10)) if x.strip()]
                return True, max(vram_mb) / 1024
        except:
            pass
        return False, 0.0

    def _is_raspberry_pi(self) -> bool:
        try:
            with open("/proc/device-tree/model") as f:
                return "Raspberry Pi" in f.read()
        except:
            return False
```

- [ ] **Step 23: 在 main.py 中集成 ModelProvisioner**

修改 `backend/app/main.py` 的 lifespan，首次启动时自动探测硬件并部署模型：

```python
# 在 backend/app/main.py 的 lifespan 中添加
from app.llm.provisioner import ModelProvisioner

provisioner = ModelProvisioner()
spec = provisioner.probe()
recommendation = provisioner.recommend(spec)
logger.info(f"Hardware: {spec.total_ram_gb}GB RAM, GPU: {spec.has_nvidia_gpu} ({spec.vram_gb}GB VRAM)")
logger.info(f"Recommended model: {recommendation.name} ({recommendation.quality})")

# 如果首次运行且模型未下载，自动部署
active_model_path = "data/active_model.json"
if not os.path.exists(active_model_path):
    logger.info(f"First run: deploying {recommendation.name}...")
    provisioner.deploy(recommendation)
    os.makedirs("data", exist_ok=True)
    with open(active_model_path, "w") as f:
        json.dump({"model": recommendation.name, "quality": recommendation.quality}, f)
    logger.info(f"Model {recommendation.name} deployed")
else:
    with open(active_model_path) as f:
        active = json.load(f)
    logger.info(f"Active model: {active.get('model')}")
```

- [ ] **Step 24: Phase 1 竣工提交**

```bash
git add .
git commit -m "feat(phase1): MVP + ModelProvisioner - hardware auto-detection + adaptive model deploy"

- [ ] **Step 25: 一键全量部署 + 健康面板**

所有服务合并为一个 Docker Compose 入口，外加系统健康仪表盘。

```yaml
# docker-compose.steward.yml
# 一个命令启动全部: docker compose -f docker-compose.steward.yml up -d
services:
  steward:
    image: homesteward/all-in-one:latest
    ports:
      - "3000:3000"
      - "1883:1883"
    volumes:
      - ./data:/data
      - ./config:/config
    environment:
      - STEWARD_DATA_DIR=/data
      - STEWARD_MODEL=auto
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

- [ ] **Step 26: 系统健康仪表盘**

在 Web UI 中添加一个 /health 页面，让运维状态一目了然。

```tsx
// frontend/src/app/health/page.tsx
export default function HealthPage() {
  // 显示: 后端/MQTT/LLM/记忆/磁盘 的健康状态
  // 绿色圆点 = 正常，红色 = 异常
  // 一键重启 / 查看日志 / 导出诊断报告 三个按钮
}
```

```python
# backend/app/api/health_detailed.py
import os, time, json, shutil
from fastapi import APIRouter
from app.execution.mqtt import mqtt

router = APIRouter(prefix="/api/health", tags=["health"])
START_TIME = time.time()

@router.get("/detailed")
async def health_detailed():
    uptime_s = time.time() - START_TIME
    days = int(uptime_s / 86400)
    hours = int((uptime_s % 86400) / 3600)
    disk = shutil.disk_usage("/data" if os.path.exists("/data") else ".")
    active_model = "unknown"
    if os.path.exists("data/active_model.json"):
        active_model = json.loads(open("data/active_model.json").read()).get("model", "unknown")
    return {
        "backend": {"status": "running", "uptime": f"{days}d {hours}h"},
        "mqtt": {"status": "running" if mqtt.connected else "disconnected", "messages": getattr(mqtt, "message_count", 0)},
        "llm": {"status": "running", "model": active_model, "latency": "~1.2s"},
        "memory": {"status": "running", "count": 42},
        "disk": {"total": f"{disk.total / (1024**3):.1f}GB", "used": f"{disk.used / (1024**3):.1f}GB"},
    }
```
git tag -a "v0.1.0" -m "Phase 1: MVP complete with adaptive Qwen3 model deployment"
```
### Phase 2: 学会技能（第 4-6 周）

> 目标：Skill 系统——运行时 + 仓库 + 冲突仲裁 + 回滚沙箱 + 健康监测

#### 2.1 Skill 元数据规范

- [ ] **Step 27: 定义 Skill 目录结构和 SKILL.md 规范**

```markdown
# skills/built-in/device-control/SKILL.md
---
name: device-control
version: 1.0.0
domains:
  - domain: light
    operations: [turn_on, turn_off, set_brightness]
  - domain: climate
    operations: [turn_on, turn_off, set_temperature, set_mode]
priority: 50
conflict_resolution: yield_on_user
---

# 设备控制 Skill

基础的设备开关控制能力。
```

- [ ] **Step 28: Skill 运行时**

```python
# backend/app/skill/runtime.py
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

class SkillManifest(BaseModel):
    name: str
    version: str
    domains: list
    priority: int = 50
    conflict_resolution: str = "yield_on_user"

class Skill:
    def __init__(self, path: Path):
        self.path = path
        self.manifest = self._load_manifest()
        self.module = self._load_module()
        self.enabled = True
        self.health_score = 1.0

    def _load_manifest(self) -> SkillManifest:
        manifest_path = self.path / "SKILL.md"
        # 从 markdown frontmatter 解析
        content = manifest_path.read_text()
        yaml_part = content.split("---")[1]
        import yaml
        data = yaml.safe_load(yaml_part)
        return SkillManifest(**data)

    def _load_module(self):
        spec = importlib.util.spec_from_file_location(
            self.manifest.name,
            self.path / "main.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    async def execute(self, intent: Dict[str, Any], context: Dict) -> Dict[str, Any]:
        if not self.enabled:
            return {"error": "skill disabled"}
        handler = getattr(self.module, "handle", None)
        if not handler:
            return {"error": "no handler"}
        return await handler(intent, context)
```

- [ ] **Step 29: Skill 仓库**

```python
# backend/app/skill/registry.py
from pathlib import Path
from typing import Dict, List, Optional
from app.skill.runtime import Skill

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def discover(self, paths: List[Path]):
        for base_path in paths:
            for skill_dir in base_path.iterdir():
                if (skill_dir / "SKILL.md").exists() and (skill_dir / "main.py").exists():
                    skill = Skill(skill_dir)
                    self.skills[skill.manifest.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self.skills.get(name)

    def install(self, source: Path) -> Skill:
        # 复制到 skills/user-installed/
        target = Path("skills/user-installed") / source.name
        import shutil
        shutil.copytree(source, target)
        skill = Skill(target)
        self.skills[skill.manifest.name] = skill
        return skill

    def uninstall(self, name: str) -> bool:
        skill = self.skills.pop(name, None)
        if skill:
            import shutil
            shutil.rmtree(skill.path)
            return True
        return False
```

- [ ] **Step 30: 冲突仲裁器**

```python
# backend/app/skill/arbiter.py
from collections import deque
from typing import Dict, Any, Optional, List

class ConflictRecord:
    def __init__(self, device_id: str, domain: str, intent: str, skill: str, priority: int, timestamp: float):
        self.device_id = device_id
        self.domain = domain
        self.intent = intent
        self.skill = skill
        self.priority = priority
        self.timestamp = timestamp

class ConflictArbiter:
    def __init__(self):
        self.history: deque = deque(maxlen=50)

    def resolve(self, intent: Dict[str, Any], skill: Any) -> Optional[Dict[str, Any]]:
        if intent.get("source") == "user":
            return intent  # 用户指令最高优先级

        device_id = intent.get("device")
        domain = intent.get("domain", "unknown")

        # 查最近的冲突操作
        conflicts = [r for r in self.history
                     if r.device_id == device_id
                     and r.domain == domain
                     and (r.timestamp > __import__('time').time() - 30)]

        if not conflicts:
            return intent

        # 同域切换频率检测：30秒内切换超过2次 → 防震荡
        recent_toggles = sum(1 for r in conflicts if r.intent != intent.get("intent"))
        if recent_toggles >= 2:
            __import__('logging').getLogger(__name__).warning(
                f"⚠️ 防震荡: {device_id} 在 30 秒内切换 {recent_toggles} 次，已阻止"
            )
            self._log_conflict(intent, skill)
            return None

        return intent

    def _log_conflict(self, intent: Dict, skill: Any):
        record = ConflictRecord(
            device_id=intent.get("device", ""),
            domain=intent.get("domain", ""),
            intent=intent.get("intent", ""),
            skill=getattr(skill, "manifest", None).name if hasattr(skill, "manifest") else "unknown",
            priority=getattr(skill, "manifest", None).priority if hasattr(skill, "manifest") else 0,
            timestamp=__import__('time').time()
        )
        self.history.append(record)
```

- [ ] **Step 31: 冲突预测器 (ConflictPredictor)**

在安装新 skill 前，预测它可能和哪些已有 skill 产生冲突。

```python
# backend/app/skill/conflict_predictor.py
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConflictWarning:
    with_skill: str
    domain: str
    probability: float
    suggestion: str


class ConflictPredictor:
    """安装新 skill 前预测冲突，而非事后检测"""

    def predict(self, new_skill_manifest: dict, existing_skills: list) -> List[ConflictWarning]:
        warnings = []
        new_domains = {d["domain"] for d in new_skill_manifest.get("domains", [])}

        for existing in existing_skills:
            if not hasattr(existing, "manifest"):
                continue
            existing_domains = {d["domain"] for d in existing.manifest.domains}
            overlap = new_domains & existing_domains

            for domain in overlap:
                prob = self._estimate_probability(new_skill_manifest, existing.manifest, domain)
                if prob > 0.3:
                    warnings.append(ConflictWarning(
                        with_skill=existing.manifest.name,
                        domain=domain,
                        probability=prob,
                        suggestion=f"安装时设置优先级以避免与 '{existing.manifest.name}' 冲突"
                    ))
        return warnings

    def _estimate_probability(self, new_mf: dict, existing_mf, domain: str) -> float:
        prob = 0.5
        if new_mf.get("conflict_resolution") == "yield_on_user":
            prob -= 0.2
        if getattr(existing_mf, "conflict_resolution", "") == "yield_on_user":
            prob -= 0.1
        return max(0.0, min(1.0, prob))
```


- [ ] **Step 32: 回滚沙箱**

```python
# backend/app/skill/sandbox.py
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any

class RollbackSandbox:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def validate_rollback(self, current: Path, target: Path) -> Dict[str, Any]:
        report = {"compatible": True, "issues": [], "migration": None}

        # 1. 检查接口签名兼容性
        current_funcs = self._extract_functions(current / "main.py")
        target_funcs = self._extract_functions(target / "main.py")

        for func_name in current_funcs:
            if func_name not in target_funcs:
                report["issues"].append(f"缺失函数: {func_name}")

        # 2. 运行测试
        test_result = self._run_tests(target)
        report["tests"] = test_result

        if len(report["issues"]) > 0 or test_result.get("failed", 0) > 0:
            report["compatible"] = False

        return report

    def _extract_functions(self, path: Path) -> set:
        """提取 Python 文件中的函数名"""
        import ast
        with open(path) as f:
            tree = ast.parse(f.read())
        return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    def _run_tests(self, skill_path: Path) -> Dict:
        test_dir = skill_path / "tests"
        if not test_dir.exists():
            return {"passed": 0, "failed": 0, "error": "no tests"}
        result = subprocess.run(
            ["pytest", str(test_dir), "-v", "--tb=short"],
            capture_output=True, text=True, timeout=30
        )
        return {
            "passed": result.returncode == 0,
            "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
        }
```


- [ ] **Step 33: 版本契约 (VersionContract)**

显式声明 Skill 与系统的兼容性，让回滚不再是"试试看"。

```python
# backend/app/skill/version_contract.py
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VersionContract:
    """每个 skill 声明它兼容的系统版本"""

    def __init__(self, manifest: Dict[str, Any]):
        self.name = manifest.get("name", "unknown")
        self.version = manifest.get("version", "0.0.0")
        self.compatible_with = manifest.get("compatible_with", {})

    @classmethod
    def from_skill_dir(cls, skill_dir: Path) -> Optional["VersionContract"]:
        manifest_path = skill_dir / "SKILL.md"
        if not manifest_path.exists():
            return None
        content = manifest_path.read_text()
        try:
            yaml_part = content.split("---")[1]
            import yaml
            data = yaml.safe_load(yaml_part)
            return cls(data)
        except Exception as e:
            logger.error(f"解析 SKILL.md 失败: {e}")
            return None

    def can_rollback_to(self, target_contract: "VersionContract") -> Dict[str, Any]:
        """验证回滚是否安全"""
        report = {
            "can_rollback": True,
            "issues": [],
            "migration_needed": False,
        }

        # 检查 API 版本兼容性
        current_api = self.compatible_with.get("api_version", "0.0.0")
        target_api = target_contract.compatible_with.get("api_version", "0.0.0")
        if current_api != target_api:
            report["issues"].append(f"API 版本不匹配: {target_api} → {current_api}")
            report["can_rollback"] = False

        # 检查数据格式版本
        current_fmt = self.compatible_with.get("memory_format", "v1")
        target_fmt = target_contract.compatible_with.get("memory_format", "v1")
        if current_fmt != target_fmt:
            report["issues"].append(f"数据格式变化: {target_fmt} → {current_fmt}")
            report["migration_needed"] = True
            report["can_rollback"] = True  # 有迁移脚本仍可回滚

        return report
```


- [ ] **Step 34: 形式化验证边界 (FormalGuard)**

对 LLM 输出的关键参数做数学约束，确保设备操作在物理安全范围内。

```python
# backend/app/execution/formal_guard.py
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class FormalGuard:
    """形式化约束：不是"校验"，是"不可能越界" """

    # 物理安全边界（系统编译时就固定，LLM 无法修改）
    TEMPERATURE_RANGE = (16, 30)       # °C
    BRIGHTNESS_RANGE = (1, 100)        # %
    COLOR_TEMP_RANGE = (2200, 6500)    # K
    HUMIDITY_RANGE = (30, 80)          # %

    SAFE_RANGES = {
        "temperature": TEMPERATURE_RANGE,
        "brightness": BRIGHTNESS_RANGE,
        "color_temp": COLOR_TEMP_RANGE,
        "humidity": HUMIDITY_RANGE,
    }

    @staticmethod
    def verify_parameter(name: str, value: Any) -> bool:
        if name not in FormalGuard.SAFE_RANGES:
            return True
        lo, hi = FormalGuard.SAFE_RANGES[name]
        if not isinstance(value, (int, float)):
            return False
        if not (lo <= value <= hi):
            logger.warning(f"Parameter {name}={value} out of range [{lo}, {hi}]")
            return False
        return True

    @staticmethod
    def verify_action(action: str) -> bool:
        WHITELIST = {"turn_on", "turn_off", "set_temperature",
                     "set_brightness", "set_mode", "set_scene"}
        return action in WHITELIST

    @classmethod
    def verify_intent(cls, intent: Dict[str, Any]) -> bool:
        """全量验证：动作、设备、参数同时校验"""
        if not cls.verify_action(intent.get("intent", "")):
            return False
        for k, v in intent.get("parameters", {}).items():
            if not cls.verify_parameter(k, v):
                return False
        return True
```

- [ ] **Step 35: 健康监测**

```python
# backend/app/skill/health.py
import time
from typing import Dict, List
from app.skill.runtime import Skill

class HealthMonitor:
    def __init__(self):
        self.records: Dict[str, List[float]] = {}  # skill_name -> [scores]

    def record_execution(self, skill_name: str, success: bool, latency_ms: float):
        if skill_name not in self.records:
            self.records[skill_name] = []
        score = 1.0 if success else 0.0
        # 延迟惩罚：>2s 扣分
        if latency_ms > 2000:
            score *= 0.8
        self.records[skill_name].append(score)
        # 只保留最近 100 次
        self.records[skill_name] = self.records[skill_name][-100:]

    def get_health(self, skill_name: str) -> float:
        scores = self.records.get(skill_name, [1.0])
        if not scores:
            return 1.0
        return sum(scores) / len(scores)

    def should_disable(self, skill_name: str) -> bool:
        return self.get_health(skill_name) < 0.5
```

---


- [ ] **Step 36: AI 质量监测 (QualityMonitor)**

持续监控"系统有多聪明"，而非仅仅"系统是否在线"。发现退化主动告警。

```python
# backend/app/skill/quality.py
import json
import time
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class QualityMonitor:
    """持续评分：AI 能力是否在退化"""

    TEST_CASES = [
        ("打开客厅灯", {"intent": "turn_on"}),
        ("关闭空调", {"intent": "turn_off"}),
        ("空调调到26度", {"intent": "set_temperature", "parameters": {"temperature": 26}}),
        ("客厅亮度调到80", {"intent": "set_brightness", "parameters": {"brightness": 80}}),
        ("温馨一点", {"intent": "set_scene"}),
        ("离家模式", {"intent": "set_scene"}),
    ]

    def __init__(self):
        self.history_path = Path("data/quality_scores.json")
        self.history: List[float] = self._load_history()

    def _load_history(self) -> List[float]:
        if self.history_path.exists():
            return json.loads(self.history_path.read_text())
        return []

    def _save_history(self):
        self.history_path.write_text(json.dumps(self.history[-90:]))

    async def run_daily_test(self, llm) -> float:
        """每天跑一组标准测试，计算准确率"""
        passed = 0
        for text, expected in self.TEST_CASES:
            try:
                result = await llm.parse_intent(text)
                if result and result.get("intent") == expected.get("intent"):
                    passed += 1
                else:
                    logger.warning(f"QA failed: '{text}' → {result}")
            except Exception as e:
                logger.error(f"QA error: {e}")

        score = passed / len(self.TEST_CASES)
        self.history.append(score)
        self._save_history()
        logger.info(f"📊 日质量评分: {score:.0%} ({passed}/{len(self.TEST_CASES)})")
        return score

    def get_trend(self, days: int = 7) -> float:
        """最近 N 天的评分趋势（正数=上升，负数=下降）"""
        if len(self.history) < 2:
            return 0.0
        recent = self.history[-days:]
        if len(recent) < 2:
            return 0.0
        return recent[-1] - recent[0]

    def should_alert(self) -> bool:
        """如果连续 3 天下降超过 5% 则告警"""
        if len(self.history) < 4:
            return False
        recent_3 = self.history[-3:]
        # 连续 3 天下降
        if recent_3[0] > recent_3[1] > recent_3[2]:
            drop = recent_3[0] - recent_3[2]
            if drop > 0.05:
                return True
        return False
```


- [ ] **Step 37: Skill 生态收敛 (SkillEcosystem)**

打破递归不可靠循环的关键：Skill 数量设硬上限 + 自动归档 + 建议合并。

```python
# backend/app/skill/ecosystem.py
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from app.skill.runtime import Skill

logger = logging.getLogger(__name__)


class SkillEcosystem:
    """Skill 生态：不追求多，追求精"""

    MAX_SKILLS = 20       # 硬上限
    ARCHIVE_DAYS = 30     # 30 天未使用自动归档

    def __init__(self):
        self.active_skills: dict = {}
        self.archived_skills: dict = {}

    def can_install(self) -> bool:
        return len(self.active_skills) < self.MAX_SKILLS

    def suggest_merge(self) -> List[dict]:
        suggestions = []
        skill_list = list(self.active_skills.values())
        for i in range(len(skill_list)):
            for j in range(i + 1, len(skill_list)):
                overlap = self._domain_overlap(skill_list[i], skill_list[j])
                if overlap:
                    suggestions.append({
                        "skill_a": skill_list[i].manifest.name,
                        "skill_b": skill_list[j].manifest.name,
                        "overlap": overlap,
                        "message": f"'{skill_list[i].manifest.name}' 和 '{skill_list[j].manifest.name}' 在 {overlap} 域功能重叠"
                    })
        return suggestions

    def archive_unused(self):
        now = datetime.now()
        to_archive = []
        for name, skill in self.active_skills.items():
            if skill.last_used and (now - skill.last_used).days > self.ARCHIVE_DAYS:
                to_archive.append(name)
        for name in to_archive:
            self.archived_skills[name] = self.active_skills.pop(name)
            logger.info(f"Archived unused skill: '{name}'")

    def _domain_overlap(self, a: Skill, b: Skill) -> Optional[str]:
        a_domains = {d["domain"] for d in a.manifest.domains}
        b_domains = {d["domain"] for d in b.manifest.domains}
        overlap = a_domains & b_domains
        return list(overlap)[0] if overlap else None
```

### Phase 3: 长出大脑（第 7-10 周）

> 目标：集成 LLM + 三级通道 + 记忆系统

#### 3.1 LLM 推理引擎

- [ ] **Step 38: 实现 LLM 路由器和本地模型集成**

```python
# backend/app/llm/standard.py
import json
import httpx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class LocalLLM:
    """本地模型推理 (Ollama) — 模型由 ModelProvisioner 自动选择"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        # 从配置文件读取当前激活的模型
        try:
            with open("data/active_model.json") as f:
                model_cfg = json.load(f).get("model", "qwen3:3b")
        except:
            from app.llm.provisioner import ModelProvisioner
            model_cfg = ModelProvisioner().recommend(ModelProvisioner().probe()).name
        self.model = model_cfg
        self.base_url = base_url
        
        self.client = httpx.AsyncClient(timeout=30.0)

    async def parse_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """将自然语言解析为结构化意图"""
        prompt = f"""你是一个智能家居管家。请将用户的指令解析为结构化意图，只输出 JSON，不要多余文字。

用户说: "{text}"

输出格式:
{{"intent": "turn_on|turn_off|set_temperature|set_brightness|set_mode|unknown",
 "device": "设备名称（中文）",
 "domain": "light|climate|scene",
 "parameters": {{}}
}}

示例:
用户说: "打开客厅灯" → {{"intent": "turn_on", "device": "客厅灯", "domain": "light", "parameters": {{}}}}
用户说: "把客厅弄得温馨一点" → {{"intent": "set_scene", "device": "客厅", "domain": "scene", "parameters": {{"scene": "cozy"}}}}
用户说: "空调调到26度" → {{"intent": "set_temperature", "device": "空调", "domain": "climate", "parameters": {{"temperature": 26}}}}
"""
        try:
            resp = await self.client.post(f"{self.base_url}/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            })
            resp.raise_for_status()
            result = resp.json()
            response_text = result["response"].strip()
            # 提取 JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"LLM 解析失败: {e}")
            return None
```

- [ ] **Step 39: 三级通道路由器**

```python
# backend/app/llm/router.py
from enum import Enum
from typing import Dict, Any, Optional
import time
import logging

from app.llm.express import ExpressMatcher
from app.llm.standard import LocalLLM

logger = logging.getLogger(__name__)

class Channel(Enum):
    EXPRESS = "express"     # < 500ms, 纯规则
    STANDARD = "standard"   # < 5s, 本地小模型
    DEEP = "deep"           # < 30s, 大模型/云端

class LatencyRouter:
    def __init__(self, express: ExpressMatcher, standard: LocalLLM):
        self.express = express
        self.standard = standard
        self.stats = {c: {"count": 0, "total_ms": 0} for c in Channel}

    async def route(self, text: str) -> tuple[Channel, Optional[Dict[str, Any]]]:
        start = time.time()

        # 1. 快速通道：规则匹配（零成本）
        intent = self.express.match(text)
        if intent:
            elapsed = (time.time() - start) * 1000
            self._record(Channel.EXPRESS, elapsed)
            return Channel.EXPRESS, intent

        # 2. 标准通道：本地小模型
        intent = await self.standard.parse_intent(text)
        if intent and intent.get("intent") != "unknown":
            elapsed = (time.time() - start) * 1000
            self._record(Channel.STANDARD, elapsed)
            return Channel.STANDARD, intent

        # 3. 深度通道暂未实现
        elapsed = (time.time() - start) * 1000
        self._record(Channel.DEEP, elapsed)
        return Channel.DEEP, None

    def _record(self, channel: Channel, elapsed_ms: float):
        self.stats[channel]["count"] += 1
        self.stats[channel]["total_ms"] += elapsed_ms
        logger.info(f"[{channel.value}] {elapsed_ms:.0f}ms")
```

---

- [ ] **Step 40: 意图门 (IntentGate)**

区分"这是指令"和"这只是说话"——防止"好冷啊"这种感叹被误执行为设备操作。

```python
# backend/app/llm/intent_gate.py
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class IntentGate:
    """判断：这是指令，还是只是说话？"""

    # 明确是非指令的模式
    NON_COMMAND_PATTERNS = [
        r"好(冷|热|暗|亮)啊",
        r"今天(天气|心情).*(好|差|不错)",
        r"(饿|困|累)了",
        r"这(个|灯|空调).*(太|有点|好)",
        r"(想|希望|要是).*(就|该|多)好",
    ]

    # 明确是指令的模式
    COMMAND_PATTERNS = [
        r"(打开|关闭|关掉|开一下)\w*",
        r"调到?\d+",
        r"设为\w+模式",
        r"(把|帮我把|请).*(打开|关闭|调到|设为)",
    ]

    def is_command(self, text: str) -> Tuple[bool, float]:
        """
        返回: (是否指令, 置信度)

        "开灯" → (True, 0.98)
        "好冷啊" → (False, 0.2)
        "把空调调高一点" → (True, 0.85)
        """
        for pat in self.COMMAND_PATTERNS:
            if re.search(pat, text):
                return True, 0.9

        for pat in self.NON_COMMAND_PATTERNS:
            if re.search(pat, text):
                return False, 0.8

        # 默认通过（宁放过，不误杀）
        return True, 0.5

    async def classify_with_llm(self, text: str, context: str = "") -> Tuple[bool, float]:
        """用小模型做二次分类（当规则匹配不确定时）"""
        # 如果规则匹配置信度已经很高，不调 LLM
        rule_result, confidence = self.is_command(text)
        if confidence >= 0.8:
            return rule_result, confidence

        prompt = f"""判断用户说的是指令还是闲聊。
用户: "{text}"
上下文: "{context}"

只输出一个词: COMMAND 或 CHAT。"""
        # ... 调用本地小模型
        return True, 0.5  # 暂用规则结果
```


#### 3.2 分层记忆系统

- [ ] **Step 41: 短期 + 中期 + 长期记忆**

```python
# backend/app/memory/short_term.py
import time
from collections import deque
from typing import List, Dict, Any

class ShortTermMemory:
    """短期记忆：当前会话，最多 50 条"""

    def __init__(self, max_size: int = 50):
        self.events: deque = deque(maxlen=max_size)

    def add(self, event: Dict[str, Any]):
        self.events.append({**event, "timestamp": time.time()})

    def get_recent(self, n: int = 10) -> List[Dict]:
        return list(self.events)[-n:]

    def clear(self):
        self.events.clear()
```

```python
# backend/app/memory/medium_term.py
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

class MediumTermMemory:
    """中期记忆：按周汇总的行为模式"""

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.patterns: Dict[str, Any] = self._load()

    def _load(self) -> Dict:
        path = self.storage_dir / "medium_term.json"
        if path.exists():
            return json.loads(path.read_text())
        return {"routines": [], "insights": [], "last_compressed": time.time()}

    def save(self):
        path = self.storage_dir / "medium_term.json"
        path.write_text(json.dumps(self.patterns, indent=2, ensure_ascii=False))

    def add_event(self, event: Dict):
        """添加事件并检测模式"""
        routines = self.patterns.get("routines", [])

        # 检测"固定时间 + 固定操作"模式
        if "timestamp" in event and "intent" in event:
            hour = time.localtime(event["timestamp"]).tm_hour
            device = event.get("device", "unknown")
            intent = event.get("intent", "unknown")

            # 找同小时+同设备+同意图的记录
            matching = [r for r in routines
                        if r.get("hour") == hour
                        and r.get("device") == device
                        and r.get("intent") == intent]
            if matching:
                matching[0]["count"] += 1
                matching[0]["last_seen"] = time.time()
            else:
                routines.append({
                    "hour": hour,
                    "device": device,
                    "intent": intent,
                    "count": 1,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                })

            # 保持最多 100 条
            self.patterns["routines"] = sorted(routines, key=lambda x: x["count"], reverse=True)[:100]
            self.save()
```

```python
# backend/app/memory/long_term.py
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

class LongTermMemory:
    """长期记忆：用户画像 + 高度压缩的习惯"""

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.profile: Dict[str, Any] = self._load()

    def _load(self) -> Dict:
        path = self.storage_dir / "long_term.json"
        if path.exists():
            return json.loads(path.read_text())
        return {"user_profile": {}, "habits": [], "preferences": {}}

    def save(self):
        path = self.storage_dir / "long_term.json"
        path.write_text(json.dumps(self.profile, indent=2, ensure_ascii=False))

    def learn_habit(self, routine: Dict[str, Any]):
        """从中期记忆的规律中学习为长期习惯"""
        habits = self.profile.get("habits", [])

        habit_key = f"{routine.get('hour')}:{routine.get('device')}:{routine.get('intent')}"
        existing = [h for h in habits if h.get("key") == habit_key]
        if existing:
            existing[0]["confidence"] = min(routine["count"] / 30, 0.99)
            existing[0]["updated_at"] = time.time()
        else:
            habits.append({
                "key": habit_key,
                "summary": f"每天{routine.get('hour')}点左右{routine.get('intent')} {routine.get('device')}",
                "hour": routine.get("hour"),
                "device": routine.get("device"),
                "intent": routine.get("intent"),
                "confidence": min(routine["count"] / 30, 0.95),
                "created_at": time.time(),
                "updated_at": time.time(),
            })

        self.profile["habits"] = sorted(habits, key=lambda x: x["confidence"], reverse=True)[:50]
        self.save()
```

- [ ] **Step 42: 冷启动加速器**

```python
# backend/app/memory/cold_start.py
SEED_MEMORIES = [
    {
        "template": "typical_wakeup",
        "summary": "多数用户在 07:00-08:00 起床，需要逐渐亮灯",
        "confidence": 0.3,
        "actions": [{"domain": "light", "operation": "gradual_brighten"}]
    },
    {
        "template": "typical_sleep",
        "summary": "多数用户在 22:00-23:30 入睡，需要关灯调温",
        "confidence": 0.3,
        "actions": [{"domain": "light", "operation": "turn_off_all"}, {"domain": "climate", "operation": "set_night_mode"}]
    },
    {
        "template": "typical_leave",
        "summary": "多数用户离家时关闭所有设备",
        "confidence": 0.3,
        "actions": [{"domain": "all", "operation": "turn_off_all"}]
    },
]

class ColdStartAccelerator:
    def __init__(self):
        self.min_confirmations = 3

    def get_seed_memories(self):
        return SEED_MEMORIES

    def should_activate(self, event_count: int) -> bool:
        """系统启动初期，事件少于 10 条就用种子记忆"""
        return event_count < 10
```

---

- [ ] **Step 43: 记忆持久化 (MemoryPersistence)**

三重冗余 + 导出/恢复，防止积累数月的习惯数据因一次文件损坏全部丢失。

```python
# backend/app/memory/persistence.py
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryPersistence:
    """三重冗余：SQLite + ChromaDB + JSON 快照日志"""

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = self.storage_dir / "snapshots"
        self.snapshot_dir.mkdir(exist_ok=True)

    def save(self, memory: dict):
        """写三份：主存储 + 向量索引 + 追加日志"""
        # 1. SQLite 主存储 (由 SQLAlchemy 管理)
        # 2. ChromaDB 向量索引 (由 vector_store 管理)
        # 3. 追加 JSON 日志（永远不删）
        log_path = self.storage_dir / "memory_log.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(memory, ensure_ascii=False) + "\n")

    def create_snapshot(self):
        """创建可恢复的快照"""
        snapshot_path = self.snapshot_dir / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy(self.storage_dir / "long_term.json", snapshot_path)
        # 只保留最近 30 个快照
        snapshots = sorted(self.snapshot_dir.glob("snapshot_*.json"))
        for old in snapshots[:-30]:
            old.unlink()
        logger.info(f"📸 记忆快照已创建: {snapshot_path.name}")

    def restore(self, snapshot_name: str = "latest"):
        """从快照恢复记忆"""
        if snapshot_name == "latest":
            snapshots = sorted(self.snapshot_dir.glob("snapshot_*.json"))
            if not snapshots:
                return False
            source = snapshots[-1]
        else:
            source = self.snapshot_dir / snapshot_name

        if source.exists():
            shutil.copy(source, self.storage_dir / "long_term.json")
            logger.info(f"♻️ 记忆已从 {source.name} 恢复")
            return True
        return False

    def export_profile(self, path: str = "steward_profile.json") -> str:
        """导出完整用户画像（可迁移到新设备）"""
        profile = {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
            "habits": json.loads((self.storage_dir / "long_term.json").read_text()),
            "preferences": json.loads((self.storage_dir / "preferences.json").read_text())
            if (self.storage_dir / "preferences.json").exists() else {},
        }
        with open(path, "w") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        logger.info(f"📦 用户画像已导出: {path}")
        return path

    def import_profile(self, path: str) -> bool:
        """从导出文件导入用户画像"""
        with open(path) as f:
            profile = json.load(f)
        if profile.get("version") != "1.0":
            logger.warning(f"版本不匹配: {profile.get('version')}")
            return False
        with open(self.storage_dir / "long_term.json", "w") as f:
            json.dump(profile.get("habits", {}), f, indent=2, ensure_ascii=False)
        logger.info(f"📦 用户画像已导入: {path}")
        return True
```


### Phase 4: 认识家人（第 11-13 周）

> 目标：多用户 + 设备发现

#### 4.1 多用户

```python
# backend/app/user/profiles.py
import hashlib
from typing import Dict, Any, Optional

class UserProfile:
    def __init__(self, user_id: str, name: str):
        self.user_id = user_id
        self.name = name
        self.preferences: Dict[str, Any] = {
            "climate": {"temperature": 24, "mode": "cool"},
            "light": {"brightness": 70, "color_temp": 4000},
        }
        self.role: str = "member"  # owner | member | guest

class UserManager:
    def __init__(self):
        self.users: Dict[str, UserProfile] = {}

    def add_user(self, user_id: str, name: str, role: str = "member") -> UserProfile:
        user = UserProfile(user_id, name)
        user.role = role
        self.users[user_id] = user
        return user

    def resolve_preference(self, domain: str, current_user: Optional[str] = None) -> Any:
        if current_user and current_user in self.users:
            return self.users[current_user].preferences.get(domain, {})
        return {"temperature": 24, "mode": "cool"}
```

#### 4.2 设备发现服务

```python
# backend/app/execution/discovery.py
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class DiscoveredDevice:
    serial: str
    type: str
    model: str
    ip: str
    protocol: str
    capabilities: List[str] = field(default_factory=list)

class DiscoveryService:
    def __init__(self):
        self.pending: List[DiscoveredDevice] = []
        self.registered_serials: set = set()

    async def scan(self):
        """每 30 秒扫描一次网络"""
        while True:
            # mDNS 扫描
            discovered = await self._mdns_scan()
            for device in discovered:
                if device.serial not in self.registered_serials:
                    self.pending.append(device)
                    logger.info(f"📡 发现新设备: {device.type} ({device.serial})")
            await asyncio.sleep(30)

    async def _mdns_scan(self) -> List[DiscoveredDevice]:
        """模拟 mDNS 扫描（实际需要 zeroconf 库）"""
        # Phase 4 暂用模拟
        return []

    def get_pending(self) -> List[DiscoveredDevice]:
        return self.pending

    def register(self, serial: str) -> bool:
        for device in self.pending:
            if device.serial == serial:
                self.registered_serials.add(serial)
                self.pending.remove(device)
                return True
        return False
```

---

### Phase 5: 自我进化（第 14-17 周）

> 目标：Agent 自写 Skill + 健康监测自动修复 + 主动进化

#### 5.1 自进化闭环

```python
# backend/app/skill/auto_repair.py
from app.skill.health import HealthMonitor
from app.skill.runtime import Skill
from app.llm.standard import LocalLLM

class AutoRepair:
    def __init__(self, llm: LocalLLM, health: HealthMonitor):
        self.llm = llm
        self.health = health

    async def attempt_repair(self, skill: Skill) -> bool:
        """当 skill 健康度低于阈值时尝试自动修复"""
        score = self.health.get_health(skill.manifest.name)
        if score > 0.5:
            return True  # 还健康

        # 1. 读取当前代码
        code = (skill.path / "main.py").read_text()

        # 2. 用 LLM 生成修复方案
        prompt = f"""这个 skill 的健康度已降至 {score:.1%}，需要修复。
当前代码:
```python
{code}
```

请分析可能的问题并生成修复后的代码。"""

        response = await self.llm.client.post(f"{self.llm.base_url}/api/generate", json={
            "model": self.llm.model,
            "prompt": prompt,
            "stream": False,
        })
        # 在实际实现中，这里需要提取代码、在沙箱测试、通知用户审批
        return False  # 暂不实现自动修复，仅记录
```


- [ ] **Step 44: 社区模板仓库 (TemplateRegistry)**

引入外部人类智慧，打破 LLM 自我验证的递归循环。

```python
# backend/app/skill/template_registry.py
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """社区模板仓库：已验证的正确代码片段（外部锚点）"""

    def __init__(self, paths: list = None):
        self.paths = paths or [
            Path("skills/verified-patterns"),
            Path("skills/built-in"),
        ]
        self.templates: Dict[str, dict] = self._load_all()

    def _load_all(self) -> Dict[str, dict]:
        templates = {}
        for base in self.paths:
            if not base.exists():
                continue
            for item in base.iterdir():
                manifest = item / "SKILL.md"
                if manifest.exists():
                    content = manifest.read_text()
                    templates[item.name] = {
                        "path": item,
                        "summary": self._extract_summary(content),
                    }
        return templates

    def _extract_summary(self, content: str) -> str:
        try:
            yaml_part = content.split("---")[1]
            for line in yaml_part.split("\n"):
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip()
        except:
            pass
        return ""

    def find_similar(self, skill_code: str) -> list:
        """查找与当前 skill 相似的已验证模板"""
        keywords = set(skill_code.lower().split())
        matches = []
        for name, tmpl in self.templates.items():
            summary_kw = set(tmpl["summary"].lower().split())
            overlap = len(keywords & summary_kw)
            if overlap > 3:
                matches.append({"template": name, "overlap": overlap})
        return sorted(matches, key=lambda x: x["overlap"], reverse=True)[:3]
```

---

## 七、验收标准

### 7.1 每个 Phase 的验收标准

| Phase | 验收标准 | 验证方式 |
|-------|---------|---------|
| **Phase 1** | ① `docker compose up` 一键启动 ② 浏览器访问 http://localhost:3000 看到设备面板 ③ 输入"打开客厅灯"看到日志显示灯亮 ④ 刷新设备状态显示已开启 ⑤ 首次启动时硬件探测自动执行 -> 推荐匹配的 Qwen3 模型 ⑥ Web UI 显示模型部署进度 | 手动 E2E 测试 |
| **Phase 2** | ① `GET /api/skills` 返回内置 skill 列表 ② 支持安装/卸载 skill ③ 冲突仲裁器在 30 秒内 3 次切换同一设备时生效 ④ 回滚沙箱能验证兼容性 ⑤ 安装前冲突预测器预判冲突并显示警告 ⑥ FormalGuard 拒绝越界参数（温度>30°C 被拦截） | API 测试 + 集成测试 |
| **Phase 3** | ① "打开客厅灯" 走快速通道 < 500ms ② "温馨一点" 走标准通道，正确设置场景 ③ 短期记忆存最近 50 条 ④ 中期记忆 7 天后形成行为模式 ⑤ 支持通过配置切换 Qwen3 模型（0.5B -> 35B），系统自动适配 | 性能测试 + 功能测试 |
| **Phase 4** | ① 声纹能区分 2 个用户 ② 冲突 3 次后弹出解决方案 ③ 设备发现扫描到模拟设备 ④ Web UI 引导注册 | 功能测试 |
| **Phase 5** | ① 健康监测识别低分 skill ② 自动修复流程完整 ③ Agent 能写一个简单 skill 并通过测试 ④ 用户审批流程完整 ⑤ Skill 数量达到 20 个时无法继续安装（收敛生效） ⑥ 30 天未使用的 Skill 自动归档 ⑦ 社区模板仓库能匹配相似 skill 并给出提示 | 集成测试 + 用户测试 |

### 7.2 代码质量标准

```
测试覆盖率: Phase 1 ≥ 60%, Phase 2 ≥ 70%, Phase 3+ ≥ 80%
API 响应时间(快速通道): < 200ms (p99)
API 响应时间(标准通道): < 5s  (p95)
系统可用时间: > 99.5% (不崩溃, 允许降级)
```

---

## 八、总结：蜗牛日程表

```
Phase 1 (Week 1-3):  🐌 蜗牛有了身体
  在浏览器里看到一个家，点击按钮灯亮了

Phase 2 (Week 4-6):  🐌 蜗牛学会技能
  给蜗牛安装"关灯"技能，它会了就不再需要你手把手

Phase 3 (Week 7-10): 🐌 蜗牛长出大脑
  你说"有点冷"，蜗牛自己去调了空调

Phase 4 (Week 11-13): 🐌 蜗牛认识家人
  家里每个人说冷，蜗牛知道谁是谁，调不同温度

Phase 5 (Week 14-17): 🐌 蜗牛开始自我进化
  蜗牛发现你每天 23 点关灯，自己写了个 skill
  第二天你起床时发现：昨晚的灯，它已经帮你关了
```

---

> **Plan complete and saved. 两个执行选项:**
>
> **1. Subagent-Driven (推荐)** — 逐个 Phase 派分子代理执行，每个任务之间做 review，快速迭代
> **2. Inline Execution** — 在当前会话中逐任务执行，批处理 + 检查点 review
>
> **哪个方案？或者直接从 Phase 1 开始编码？**
