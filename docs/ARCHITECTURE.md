# Home Steward Agent — 架构设计文档

> 版本: v0.1 | 状态: 设计阶段 | 最后更新: 2025-06-09

---

## 目录

1. [系统总览](#1-系统总览)
2. [8 个优化问题的解决方案](#2-8-个优化问题的解决方案)
   - [2.1 Skill 冲突管理](#21-skill-冲突管理)
   - [2.2 响应分级与延迟隔离](#22-响应分级与延迟隔离)
   - [2.3 记忆系统冷启动](#23-记忆系统冷启动)
   - [2.4 多用户偏好分歧](#24-多用户偏好分歧)
   - [2.5 Skill 健康监测与自动维护](#25-skill-健康监测与自动维护)
   - [2.6 回滚的完整性问题](#26-回滚的完整性问题)
   - [2.7 MQTT 单点依赖](#27-mqtt-单点依赖)
   - [2.8 设备发现 UX](#28-设备发现-ux)
3. [模块规格](#3-模块规格)
4. [数据流全景](#4-数据流全景)
5. [落地路线图](#5-落地路线图)

---

## 1. 系统总览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Presentation Layer                               │
│   Next.js PWA (Web + Mobile) · WebSocket · REST API · 语音输入 (Web Speech)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ HTTP / WS
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Core Layer                                  │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                         LLM 推理引擎                                   │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌────────────┐                     │   │
│  │  │ 本地推理     │  │ 混合调度器    │  │ 云端适配器   │                     │   │
│  │  │ Ollama+Llama│  │ (隐私分界)    │  │ (脱敏后)    │                     │   │
│  │  └────────────┘  └──────────────┘  └────────────┘                     │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                        Skill 管理系统                                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │   │
│  │  │ 运行时    │ │ 仓库     │ │ 冲突仲裁器 │ │ 健康监测  │ │ 回滚沙箱  │    │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                        记忆系统                                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │   │
│  │  │ 短期记忆  │ │ 中期记忆  │ │ 长期记忆  │ │ 向量索引  │                  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                    多用户管理                                          │   │
│  │  用户画像 · 声纹识别 · 权限 · 偏好隔离                                   │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Execution Layer                                     │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  安全执行层                                                           │   │
│  │  ● 意图验证 (白名单校验)  ● 速率限制  ● 异常熔断  ● 操作日志           │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  设备抽象层                                                           │   │
│  │  ● 统一设备模型  ● MQTT 驱动  ● 本地降级缓存  ● 设备发现服务           │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ MQTT / HTTP
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Device Layer                                        │
│   WiFi 设备  ·  Zigbee 网关  ·  红外发射器  ·  虚拟设备  ·  后续扩展协议     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 含义 |
|------|------|
| **LLM 建议，不执行** | LLM 输出结构化意图，安全层翻译为确定性指令 |
| **故障降级** | 每个组件失效时，系统不崩溃，只降级功能 |
| **可观测** | 所有决策可审计、可回溯、可解释 |
| **渐进进化** | 新 skill 经过沙箱 → 灰度 → 生产三阶段 |
| **隐私分界** | 隐私数据不出本地，脱敏后可选择上云 |

---

## 2. 8 个优化问题的解决方案

### 2.1 Skill 冲突管理

#### 问题

多个 skill 在同一时间操作同一设备域，产生冲突指令循环。

#### 解决方案：三层仲裁器

```
用户指令 "关灯" ──────────► 第一层: 用户指令优先
                                  │
节能 skill "关灯" ──────────► 第二层: 静态优先级裁决
舒适 skill "开灯" ──────────►       (优先级数值比较)
                                  │
                                  ▼
                           第三层: 动态裁决
                           (检查最近 N 条操作历史，
                            避免 5 秒内重复切换)
                                  │
                                  ▼
                           最终指令 → 安全执行层
```

#### 实现规格

**Skill 声明域 (manifest)**

```yaml
# skill 的元数据声明
name: energy-saver
version: 1.0.0
domains:           # 声明此 skill 操作的设备域
  - domain: climate
    operations: [set_temperature, set_mode]
  - domain: light
    operations: [set_brightness]
priority: 30       # 1-100，数字越大优先级越高
                   # 用户手动指令固定为 100
conflict_resolution: "yield_on_user"  # 遇到用户指令自动让位
```

**冲突仲裁器算法**

```python
class ConflictArbiter:
    def __init__(self):
        self.operation_history = deque(maxlen=50)  # 近 N 条操作
    
    def resolve(self, intent: DeviceIntent, skill: SkillManifest) -> Optional[DeviceIntent]:
        # 1. 用户指令最高优先级 (固定 100)
        if intent.source == "user":
            return intent  # 直接放行
        
        # 2. 查与该 intent 冲突的最近操作
        conflicting = self._find_conflicts(intent)
        if not conflicting:
            return intent  # 无冲突，放行
        
        # 3. 优先级比较
        highest_priority = max(c.priority for c in conflicting)
        if skill.priority > highest_priority:
            return intent
        elif skill.priority < highest_priority:
            return None  # 被更高优先级的 skill 覆盖
        else:
            # 4. 同优先级 → 检查切换频率
            recent_toggles = self._count_toggles(intent.device_id, intent.domain)
            if recent_toggles > 2:  # 近 30 秒切换超过 2 次
                self._log_conflict(intent, conflicting)
                return None  # 防止震荡
            return intent
```

**用户可见的冲突报告**

冲突不会默默发生——Web UI 上会展示冲突记录，用户可以调整优先级。

```
┌─────────────────────────────────────────────┐
│  ⚠️ 设备冲突记录                              │
│                                              │
│  今日 14:23 空调 26°C                        │
│    ← 节能模式 (优先级 30)                    │
│    ← 舒适模式 (优先级 25) → 被覆盖           │
│                                              │
│  [调整优先级]  [设为默认]  [忽略]             │
└─────────────────────────────────────────────┘
```

---

### 2.2 响应分级与延迟隔离

#### 问题

本地 LLM 推理延迟 5-30s，让简单操作（开灯）也变得迟钝。

#### 解决方案：三级响应通道

```
用户输入
    │
    ├─► 快速通道 (Express, <500ms)
    │   └─ 意图匹配器匹配已知模式 → 直接执行
    │       "开灯" → {"intent": "turn_on", "domain": "light"}
    │       完全不走 LLM，纯规则匹配
    │
    ├─► 标准通道 (Normal, <5s)
    │   └─ 需要简单理解的指令 → 本地小模型推理
    │       "把客厅弄得温馨一点" → 本地 LLM 解析 → 安全层执行
    │
    └─► 深度通道 (Deep, <30s)
        └─ 复杂任务 → 本地大模型 / (脱敏后)云端
            "写一个 skill: 每天根据天气预报决定是否浇花"
```

#### 实现规格

**快速通道匹配器**

```python
class ExpressMatcher:
    """快速通道：纯规则匹配，零延迟"""
    
    PATTERNS = {
        # 正则 → 结构化意图
        r"打开(.+)": {"intent": "turn_on", "confidence": "exact"},
        r"关闭(.+)": {"intent": "turn_off", "confidence": "exact"},
        r"(.+)调到(\d+)度": {"intent": "set_temperature", "confidence": "exact"},
        r"(.+)设为(.+)模式": {"intent": "set_mode", "confidence": "exact"},
    }
    
    def match(self, text: str) -> Optional[DeviceIntent]:
        """如果匹配快速模式，直接返回意图；否则返回 None"""
        for pattern, template in self.PATTERNS.items():
            m = re.match(pattern, text)
            if m:
                return DeviceIntent.from_template(template, m.groups())
        return None  # 无法匹配 → 走 LLM 通道
```

**延迟监控与动态路由**

```python
class LatencyRouter:
    def __init__(self):
        self.channel_stats = {
            "express": {"avg_ms": 50, "p99_ms": 150},
            "normal": {"avg_ms": 2500, "p99_ms": 8000},
            "deep": {"avg_ms": 12000, "p99_ms": 30000},
        }
    
    def route(self, text: str) -> Channel:
        # 快速通道试匹配（零成本）
        intent = ExpressMatcher.match(text)
        if intent:
            return Channel.EXPRESS, intent
        
        # 标准通道：本地小模型试解析
        normal_result = self.local_small_llm.try_parse(text, timeout_ms=500)
        if normal_result.confidence > 0.8:
            return Channel.NORMAL, normal_result
        
        # 深度通道
        return Channel.DEEP, text
```

**紧急通道 (紧急通道独立于上述三级)**

安防告警（烟雾报警、门窗异常打开）走**硬件直连路径**，不经过任何软件层：

```
烟感传感器触发
    │
    ├─► MQTT 紧急主题 (QoS 2, 最高优先级)
    │       │
    │       ▼
    ├─► 本地告警器直连 (GPIO/继电器)
    │
    └─► Agent 通知层 (异步)
            → Web 推送
            → 语音播报
```

---

### 2.3 记忆系统冷启动

#### 问题

新装系统前几周记忆库为空，LLM 在盲猜用户偏好。

#### 解决方案：种子记忆 + 主动画像 + 快速收敛

**种子记忆库**

系统出厂自带一套通用家庭模板，覆盖 80% 家庭的典型场景：

```json
{
  "seed_memories": [
    {
      "template": "typical_wakeup",
      "summary": "多数用户在 07:00-08:00 起床",
      "confidence": 0.3,
      "tags": ["routine", "morning"],
      "actions": [
        {"domain": "light", "operation": "gradual_brighten", "reason": "模拟日出"}
      ]
    },
    {
      "template": "typical_sleep",
      "summary": "多数用户在 22:00-23:30 入睡",
      "confidence": 0.3,
      "tags": ["routine", "night"],
      "actions": [
        {"domain": "light", "operation": "turn_off_all"},
        {"domain": "climate", "operation": "set_night_mode"}
      ]
    }
  ]
}
```

**主动画像流程**

```
首次启动
    │
    ├─► 引导问卷 (Web UI 首次访问时弹出)
    │   ┌──────────────────────────────────────┐
    │   │  ✨ 让 Home Steward 认识你            │
    │   │                                      │
    │   │  你一般几点起床？ [____]              │
    │   │  你一般几点睡觉？ [____]              │
    │   │  家里有几口人？  [____]               │
    │   │  你希望系统主动还是被动？ [主动/被动]   │
    │   │  已有设备？ [灯光/空调/窗帘/安防...]    │
    │   │                                      │
    │   │  [跳过] → 使用通用模板                │
    │   └──────────────────────────────────────┘
    │
    ├─► 冷启动策略：前 7 天只观察记录，不主动建议
    │
    └─► 第 7 天合并观察结果 → 生成第一批高信度记忆
```

**快速收敛机制**

```python
class ColdStartAccelerator:
    def __init__(self):
        self.observation_buffer = []
        self.MIN_CONFIRMATIONS = 3   # 观察到 3 次即可形成习惯
    
    def observe(self, event: DeviceEvent):
        self.observation_buffer.append(event)
        
        # 检测重复模式
        pattern = self._detect_pattern(event)
        if pattern and pattern.count >= self.MIN_CONFIRMATIONS:
            # 快速生成记忆（比常规周期压缩快 10 倍）
            memory = Memory(
                summary=pattern.summary,
                confidence=pattern.calculate_confidence(),
                created=now(),
                source="cold_start_accelerator"
            )
            MemorySystem.commit(memory)
            self.observation_buffer.clear_pattern(pattern)
```

**冷启动期间的行为变化**

| 天数 | 记忆库状态 | 系统行为 |
|------|-----------|---------|
| 第 1 天 | 仅种子记忆 (置信度 0.3) | 只响应指令，不主动建议 |
| 第 3 天 | ~5 条观察记忆 (0.5-0.7) | "我发现你每晚 11 点关灯，需要设自动关灯吗？" |
| 第 7 天 | ~15 条确认记忆 (0.7-0.9) | 开始主动建议 |
| 第 14 天 | ~30 条稳定记忆 (0.85+) | 正常运作 |
| 第 30 天 | 全量画像 | 完全个性化 |

---

### 2.4 多用户偏好分歧

#### 问题

家庭多人共享系统，每个用户有不同偏好，当前架构把「用户」当单数处理。

#### 解决方案：多用户画像 + 操作者识别 + 冲突策略

**用户模型**

```python
class UserProfile:
    user_id: str
    name: str
    voice_embedding: List[float]  # 声纹特征向量（本地提取，不传出）
    
    # 偏好域
    preferences: Dict[str, Any] = {
        "climate": {"temp": 24, "mode": "cool"},
        "light": {"brightness": 70, "color_temp": 4000},
    }
    
    # 学习到的习惯
    habits: List[Memory] = []
    
    # 权限等级
    role: str = "member"  # "owner" | "member" | "guest"
```

**操作者识别策略**

```
用户说话/操作
    │
    ├─► 语音交互 → 本地声纹提取 → 匹配用户画像
    │    (whisper + 本地 embedding 模型，全程不传出)
    │
    ├─► Web 界面 → 登录态 → 直接绑定用户
    │
    ├─► 无法识别 → 标记为 "unknown"
    │    (用"最近一次操作者"或"默认配置"临时处理)
```

**多用户场景下的行为规则**

```python
class MultiUserManager:
    def resolve_preference(self, domain: str, current_user: Optional[str]) -> Any:
        if current_user:
            # 已知用户 → 用该用户的偏好
            return self.get_user(current_user).preferences[domain]
        
        # 未知用户 → 用"最近活跃用户"的偏好
        last_active = self.get_last_active_user(minutes=30)
        if last_active:
            return last_active.preferences[domain]
        
        # 完全无法判定 → 用"家庭默认"配置
        return self.family_defaults[domain]
    
    def on_conflict(self, domain: str, user_a: str, user_b: str) -> None:
        # 记录冲突，不阻塞执行
        conflict = UserConflict(
            domain=domain,
            user_a=user_a, value_a=...,
            user_b=user_b, value_b=...,
            resolved_by="last_active_wins"  # 当前策略
        )
        self.conflict_log.append(conflict)
        
        # 如果同一对用户在同一域冲突超过 3 次
        if self._conflict_count(user_a, user_b, domain) >= 3:
            # 弹出"长期解决方案"建议
            self.suggest_resolution(domain, user_a, user_b)
```

**长期冲突解决建议**

```
┌──────────────────────────────────────────────────┐
│  ⚠️ 你和小明在空调温度上经常有不同意见              │
│                                                  │
│  你: 24°C  小明: 27°C                            │
│  过去一周冲突了 5 次                               │
│                                                  │
│  建议方案:                                        │
│  □ 设置"跟随当前操作者" (谁在房间听谁的)           │
│  □ 分区控制 (客厅你的偏好，卧室小明的偏好)          │
│  □ 设定家庭默认值 25°C，争议时用默认值              │
│                                                  │
│  [应用] [稍后再说]                                │
└──────────────────────────────────────────────────┘
```

---

### 2.5 Skill 健康监测与自动维护

#### 问题

自写 skill 在底层接口变化、设备更换、依赖升级后默默失效，无人知晓。

#### 解决方案：三层健康监测

```
Skill 健康监测
    │
    ├─► 被动监测 (每次调用时检查)
    │   ● 调用是否成功？   → 记录成功率
    │   ● 返回值是否异常？  → 记录异常类型
    │   ● 执行时间是否异常？ → 记录延迟变化
    │
    ├─► 主动监测 (定时运行)
    │   ● 运行 skill 自身测试用例
    │   ● 检查依赖接口是否可用
    │   ● 验证输出是否符合 schema
    │
    └─► 集成监测 (系统级)
        ● 跨 skill 调用链是否正常
        ● 有没有产生冲突/异常
        ● 数据一致性校验
```

#### 实现规格

**Skill 测试用例规范**

每个 skill 必须包含 `tests/` 目录，这是 skill 维护的生命线：

```yaml
# skill 的 test manifest
tests:
  unit:
    - name: "basic_turn_on"
      input: {"device": "light_1", "action": "turn_on"}
      expected: {"success": true}
    
    - name: "invalid_device"
      input: {"device": "nonexistent", "action": "turn_on"}  
      expected: {"error": "device_not_found"}
  
  integration:
    - name: "mqtt_connectivity"
      command: "ping mqtt_broker"
      expected: {"reachable": true}
```

**健康评分算法**

```python
class HealthMonitor:
    def score(self, skill: Skill) -> float:
        """返回 0.0 - 1.0 的健康评分"""
        factors = {
            "success_rate": self._success_rate(skill),         # 调用成功率
            "test_pass_rate": self._test_pass_rate(skill),      # 测试通过率
            "latency_health": self._latency_health(skill),      # 延迟健康度
            "dep_health": self._dependency_health(skill),       # 依赖健康度
            "conflict_rate": self._conflict_rate(skill),        # 冲突率
        }
        
        weights = {
            "success_rate": 0.35,
            "test_pass_rate": 0.30,
            "latency_health": 0.10,
            "dep_health": 0.15,
            "conflict_rate": 0.10,
        }
        
        return sum(factors[k] * weights[k] for k in weights)
    
    def on_score_below_threshold(self, skill: Skill, score: float):
        if score < 0.5:
            # 自动停用
            skill.disable()
            self.notify_user(f"⚠️ Skill '{skill.name}' 健康度降至 {score:.1%}，已自动停用")
            
            # 尝试自动修复
            self._attempt_auto_repair(skill)
```

**自动修复流水线**

```python
class AutoRepair:
    def attempt_repair(self, skill: Skill) -> bool:
        # 1. 收集诊断信息
        diagnostic = {
            "failures": self._get_recent_failures(skill),
            "interface_changes": self._detect_interface_changes(skill),
            "test_output": self._run_tests_detailed(skill),
        }
        
        # 2. 给 LLM 发送修复请求（脱敏后的技术信息）
        fix_request = {
            "skill_name": skill.name,
            "skill_code": skill.code,
            "failures": diagnostic["failures"],
            "test_results": diagnostic["test_output"],
        }
        
        # 3. LLM 生成修复方案（本地或脱敏后云端）
        fix_plan = self.llm.generate_fix(fix_request)
        
        # 4. 在沙箱中验证修复
        patched_skill = skill.apply_patch(fix_plan)
        if self.sandbox.validate(patched_skill):
            # 5. 通知用户审批
            self.notify_user(
                f"🔧 已自动修复 skill '{skill.name}'，"
                f"修改内容：{fix_plan.summary}，是否部署？"
            )
            return True
        
        return False  # 自动修复失败，等待人工介入
```

---

### 2.6 回滚的完整性问题

#### 问题

回滚到旧版 skill 时，数据类型、接口签名、外部依赖可能已变化，直接回滚造成数据损坏。

#### 解决方案：回滚沙箱

```
用户请求回滚 skill v2 → v1
    │
    ├─► 步骤 1: 快照当前状态
    │    ● 备份 skill 当前版本
    │    ● 备份 skill 关联数据
    │    ● 记录当前系统状态
    │
    ├─► 步骤 2: 在沙箱中加载 v1
    │    ● 创建隔离环境 (临时数据库 + 模拟设备)
    │    ● 运行 v1 的测试用例
    │    ● 用当前生产数据验证兼容性
    │    ├── 兼容 ✅ → 继续
    │    └── 不兼容 ❌ → 生成迁移脚本
    │
    ├─► 步骤 3: 执行回滚
    │    ● 应用迁移脚本（如果需要）
    │    ● 替换为 v1
    │    ● 验证基本功能
    │
    └─► 步骤 4: 记录回滚结果
         ● 成功 → 通知用户
         ● 失败 → 自动恢复到 v2（回滚的回滚）
```

#### 实现规格

```python
class RollbackSandbox:
    def __init__(self):
        self.sandbox_db = Database(":memory:")
        self.mock_devices = MockDeviceRegistry()
    
    def validate_backward_compatibility(
        self, new_skill: Skill, old_skill: Skill
    ) -> ValidationReport:
        report = ValidationReport()
        
        # 1. 接口签名对比
        report.add_check("接口兼容性", self._check_interface(old_skill, new_skill))
        
        # 2. 数据格式对比
        test_data = self._sample_production_data(new_skill)
        old_result = old_skill.execute(test_data)
        new_result = new_skill.execute(test_data)
        report.add_check("数据往返", old_result == new_result)
        
        # 3. 反向兼容测试：用旧 skill 读取新格式数据
        try:
            with self.sandbox_db.load_schema(old_skill.schema):
                old_skill.execute(test_data)
            report.add_check("反向读取", True)
        except SchemaError:
            migration = self._generate_migration_script(
                from_schema=new_skill.schema,
                to_schema=old_skill.schema
            )
            report.add_check("反向读取", False, migration=migration)
        
        return report
    
    def generate_migration_script(
        self, from_schema: Schema, to_schema: Schema
    ) -> str:
        """自动生成数据迁移脚本"""
        prompt = f"""
        数据结构从 v2 回滚到 v1 需要转换。
        v2 schema: {from_schema}
        v1 schema: {to_schema}
        生成 Python 迁移脚本。
        """
        return self.llm.generate_migration(prompt)
```

**用户看到的回滚界面**

```
┌─────────────────────────────────────────────────────┐
│  ⏪ 回滚 skill: energy-saver                         │
│                                                     │
│  当前版本: v2 (2025-06-08)                           │
│  回滚目标: v1 (2025-05-20)                           │
│                                                     │
│  ┌─ 沙箱验证结果 ─────────────────────────────┐     │
│  │  ✅ 接口兼容性: 通过                         │     │
│  │  ⚠️ 数据格式: 不兼容                        │     │
│  │     → 已生成迁移脚本 (3 行变更)              │     │
│  │  ✅ 测试用例: 全部通过 (5/5)                 │     │
│  └────────────────────────────────────────────┘     │
│                                                     │
│  [确认回滚]  [取消]                                 │
└─────────────────────────────────────────────────────┘
```

---

### 2.7 MQTT 单点依赖

#### 问题

MQTT Broker 是整个设备通信的单一故障点。它挂了，所有设备控制瘫痪。

#### 解决方案：三层降级策略

```
正常状态:
  Agent ←→ MQTT Broker ←→ Devices

MQTT 断开 (第 1 层):
  Agent ──→ 本地状态缓存 (只读)
  Agent ──→ 重试连接 (指数退避)
  用户看到: "设备状态可能不是最新的"

MQTT 长时间断开 (第 2 层):
  Agent ──→ 设备直连通道 (如果协议支持 HTTP API / 本地 SDK)
  各设备 adapter 尝试切换协议
  用户看到: "部分设备在直连模式，功能受限"

MQTT 恢复:
  Agent ──→ 状态同步 (重放离线期间的操作)
  Agent ──→ 通知用户 "设备连接已恢复"
```

#### 实现规格

**设备状态缓存**

```python
@dataclass
class CachedDeviceState:
    device_id: str
    status: str  # "online" | "offline" | "unknown"
    properties: Dict[str, Any]  # 最后一次已知状态
    last_seen: datetime
    cached_at: datetime
    
class DeviceStateCache:
    def __init__(self):
        # 内存缓存 + SQLite 持久化
        self.memory_cache: Dict[str, CachedDeviceState] = {}
        self.db = SQLiteDB("device_cache.db")
    
    def update(self, device_id: str, properties: Dict):
        """每次收到 MQTT 状态更新时调用"""
        state = CachedDeviceState(
            device_id=device_id,
            status="online",
            properties=properties,
            last_seen=now(),
            cached_at=now(),
        )
        self.memory_cache[device_id] = state
        self.db.upsert(state)
    
    def get(self, device_id: str) -> Optional[CachedDeviceState]:
        """读取缓存（MQTT 断开时只能读到这个）"""
        if device_id in self.memory_cache:
            return self.memory_cache[device_id]
        return self.db.get(device_id)
    
    def get_staleness(self, device_id: str) -> timedelta:
        """返回缓存数据的陈旧程度"""
        state = self.get(device_id)
        if not state:
            return timedelta.max
        return now() - state.last_seen
```

**MQTT 故障时的降级策略选择**

```python
class MQTTCircuitBreaker:
    def __init__(self):
        self.state = "closed"  # closed | open | half_open
        self.failure_count = 0
        self.last_failure_time = None
        self.THRESHOLD = 3      # 连续 3 次失败熔断
        self.RETRY_INTERVAL = 30  # 30 秒后重试
    
    def on_publish_failure(self):
        self.failure_count += 1
        self.last_failure_time = now()
        if self.failure_count >= self.THRESHOLD:
            self.state = "open"
            self._switch_to_degraded_mode()
    
    def _switch_to_degraded_mode(self):
        """切换到降级模式"""
        # 1. 通知各 adapter 尝试直连
        for adapter in self.adapters:
            adapter.try_direct_mode()
        
        # 2. 通知用户界面
        self.broadcast_to_ui({
            "type": "connection_status",
            "status": "degraded",
            "message": "设备通信降级中，部分功能可能受限"
        })
        
        # 3. 缓存最近操作，恢复后重放
        self.operation_buffer = OperationBuffer()
    
    def try_reconnect(self):
        """尝试重连 MQTT"""
        try:
            await self.mqtt_client.reconnect()
            self.state = "closed"
            self.failure_count = 0
            # 重放离线操作
            await self.operation_buffer.replay()
            self.broadcast_to_ui({"status": "restored"})
        except:
            self.state = "open"
            schedule_retry(self.RETRY_INTERVAL)
```

**设备直连协议适配器接口**

```python
class DeviceAdapter(ABC):
    """所有设备 adapter 的基类"""
    
    @abstractmethod
    async def connect(self):
        """建立连接（MQTT 优先，降级时切换直连）"""
        pass
    
    @abstractmethod
    async def direct_control(self, command: DeviceCommand) -> bool:
        """MQTT 不可用时，通过直连协议发送指令"""
        pass
    
    @abstractmethod
    def supports_direct_mode(self) -> bool:
        """此设备类型是否支持直连降级"""
        return False  # 默认不支持，由具体 adapter 重写
```

---

### 2.8 设备发现 UX

#### 问题

用户买了一个新设备，如何让它出现在 Home Steward 中？如果每次都要手动配置，不是真正的"智能"。

#### 解决方案：自动化发现 + Web UI 引导

**设备发现协议**

```
新设备接入网络
    │
    ├─► mDNS 广播 ("我是新插座，支持 MQTT")
    │   │
    │   ▼
    ├─► Agent 的 Discovery Service 收到广播
    │   │
    │   ▼
    ├─► 查询设备能力 (通过 HTTP GET /steward/info)
    │   │   返回: {"type": "plug", "model": "v1", 
    │   │           "capabilities": ["switch", "power_monitor"]}
    │   │
    │   ▼
    ├─► 注册到设备注册表
    │   │   分配 device_id, 注册 MQTT topic
    │   │
    │   ▼
    └─► Web UI 推送通知
```

**Web UI 发现流程**

```
┌──────────────────────────────────────────────────┐
│  📡 发现新设备                                    │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │                                          │    │
│  │      [智能插座 - SN:ABC123]              │    │
│  │      ● 支持: 开关控制 · 电量监测          │    │
│  │      ┌────────────────┐                  │    │
│  │      │  给它起个名字:  [客厅台灯____]     │    │
│  │      └────────────────┘                  │    │
│  │      [确认添加]  [忽略]  [稍后再说]       │    │
│  │                                          │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  还可以手动添加: [输入设备地址] [扫描二维码]       │
└──────────────────────────────────────────────────┘
```

#### 实现规格

**Discovery Service**

```python
class DiscoveryService:
    def __init__(self):
        self.protocols = [
            mDNSProtocol(),
            SSDPProtocol(),
            BluetoothProtocol(),
        ]
        self.pending_devices: List[DiscoveredDevice] = []
    
    async def scan(self):
        """持续扫描网络中的新设备"""
        while True:
            for protocol in self.protocols:
                devices = await protocol.discover()
                for device in devices:
                    if not self._is_registered(device.serial):
                        self.pending_devices.append(device)
                        await self._notify_user(device)
            await asyncio.sleep(30)  # 每 30 秒扫描一次
    
    async def _query_device_capabilities(
        self, device: DiscoveredDevice
    ) -> DeviceCapabilities:
        """查询设备能力清单"""
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(
                    f"http://{device.ip}/steward/info",
                    timeout=5
                )
                return DeviceCapabilities(**await resp.json())
        except:
            return DeviceCapabilities(protocols=[device.protocol])
    
    async def register_device(
        self, device: DiscoveredDevice, name: str
    ):
        """用户确认后注册设备"""
        device_id = f"{device.type}_{uuid4().hex[:8]}"
        
        # 1. 分配 MQTT topic
        mqtt_topics = {
            "control": f"steward/{device_id}/control",
            "status": f"steward/{device_id}/status",
        }
        
        # 2. 注册到设备注册表
        DeviceRegistry.register(
            Device(
                id=device_id,
                name=name,
                type=device.type,
                ip=device.ip,
                protocol=device.protocol,
                capabilities=device.capabilities,
                mqtt_topics=mqtt_topics,
            )
        )
        
        # 3. 通知设备它的 topic 分配
        await self._notify_device(device, mqtt_topics)
        
        # 4. 从待处理列表移除
        self.pending_devices.remove(device)
```

**手动添加设备界面**

```python
# 当自动发现不可用时（设备不支持 mDNS）
"""
手动添加设备:

方法 1: 输入 IP 地址
  [192.168.1.______:____]

方法 2: 选择已知设备类型
  [智能插座 ▼]
  [WiFi 灯泡 ▼]
  [红外空调 ▼]
  [...更多...]
  
方法 3: 扫码添加
  [📷 扫描设备二维码]
"""
```

---

## 3. 模块规格

### 3.1 模块清单与状态

| 模块 | 说明 | MVP | 扩展 | 解决哪条问题 |
|------|------|-----|------|------------|
| `agent/core/` | Agent 内核、生命周期管理 | ✅ | ✅ | — |
| `agent/llm/` | LLM 推理引擎（本地+云端混合） | ✅ | ✅ | 响应分级 #2 |
| `agent/skill/` | Skill 管理系统 | ✅ | ✅ | #1 #5 #6 |
| `agent/memory/` | 分层记忆系统 | ✅ | ✅ | #3 |
| `agent/user/` | 多用户管理 | — | ✅ | #4 |
| `execution/safety/` | 安全执行层 | ✅ | ✅ | — |
| `execution/device/` | 设备抽象层 + MQTT | ✅ | ✅ | #7 |
| `execution/discovery/` | 设备发现服务 | — | ✅ | #8 |
| `web/` | Next.js PWA 界面 | ✅ | ✅ | — |

### 3.2 核心 API 设计

```
REST API:

  GET    /api/devices                    → 设备列表
  POST   /api/devices/:id/command        → 发送设备指令
  GET    /api/devices/:id/status          → 设备状态
  
  GET    /api/skills                     → Skill 列表
  POST   /api/skills                     → 安装新 skill
  POST   /api/skills/:id/execute         → 执行 skill
  DELETE /api/skills/:id                 → 卸载 skill
  POST   /api/skills/:id/rollback        → 回滚 skill
  
  GET    /api/memory                     → 记忆查询
  POST   /api/memory/recall              → 按需检索记忆
  
  GET    /api/users                      → 用户列表
  POST   /api/users/:id/preferences      → 更新用户偏好
  
  GET    /api/discovery/pending          → 待发现设备
  
  GET    /api/health/skills/:id          → Skill 健康状态

WebSocket:
  /ws/events  → 实时推送设备事件、告警、发现通知
```

---

## 4. 数据流全景

### 用户指令流

```
用户: "把客厅弄得温馨一点"
    │
    ▼
[Web UI / 语音] → HTTP POST /api/devices/command
    │
    ▼
[快速通道匹配器] → 匹配失败 ("温馨"不是简单指令)
    │
    ▼
[标准通道] → 本地小模型解析
    │ 解析结果: {"domain": "scene", "scene": "cozy", "room": "living"}
    │
    ▼
[冲突仲裁器] → 检查有无冲突 skill → 无冲突
    │
    ▼
[安全执行层] → 校验意图白名单 → 通过
    │
    ▼
[设备抽象层] → 分解为 3 条 MQTT 指令
    │  ├─ light_strip → set_color_temp(2700), set_brightness(60)
    │  ├─ ac → set_temperature(24), set_mode(cool)
    │  └─ curtain → set_position(50)
    │
    ▼
[MQTT Broker] → 设备执行
    │
    ▼
[反馈循环] → 记录设备状态 → 更新记忆系统
    │  "用户喜欢温馨场景 (living, 22:00)"
    │
    ▼
[记忆系统] → 模式提取 → 如果重复多次 → 生成习惯
```

### Skill 自进化流

```
用户: "帮我写个skill，每天8点自动播放天气"
    │
    ▼
[LLM 评估] → "这是一个新需求，需要创建 skill"
    │
    ▼
[/writing-skills] → 生成 skill 代码 + 测试用例
    │
    ▼
[沙箱] → 在隔离环境运行测试 → 5/5 通过
    │
    ▼
[用户审批] → "新 skill 'morning-weather' 已通过测试，是否安装？"
    │ 用户: 确认
    │
    ▼
[灰度部署] → 只读模式运行 48 小时
    │ 监测异常率 → 0%
    │
    ▼
[生产部署] → Skill 入库 → 可用
    │
    ▼
[健康监测] → 每周自动检查一次 → 持续正常
    │
    ▼
[记忆系统] → "用户用了这个 skill 37 次" → 增加记忆权重
```

---

## 5. 落地路线图

### 阶段划分

```
Phase 1: 基础设施 (2-3 周)
┌──────────────────────────────────────────────┐
│  ● 项目骨架 (Python FastAPI + 项目结构)       │
│  ● MQTT Broker (Mosquitto Docker)            │
│  ● 基础设备模型 + 虚拟设备                    │
│  ● 快速通道匹配器                            │
│  ● 安全执行层 (白名单 + 速率限制)              │
│  ● Next.js PWA 基础框架                      │
│  ▶ 可运行: 通过 Web 控制虚拟设备开关灯         │
└──────────────────────────────────────────────┘

Phase 2: Skill 系统 (2-3 周)
┌──────────────────────────────────────────────┐
│  ● Skill 运行时 + 仓库                        │
│  ● 冲突仲裁器                                │
│  ● 回滚沙箱                                 │
│  ● Skill 健康监测                            │
│  ● 内置基础 skill: 设备控制                    │
│  ▶ 可运行: 安装/卸载/回滚 skill               │
└──────────────────────────────────────────────┘

Phase 3: 智能层 (3-4 周)
┌──────────────────────────────────────────────┐
│  ● LLM 推理集成 (Ollama + 本地模型)           │
│  ● 标准通道/深度通道路由                      │
│  ● 隐私分界 + 云端脱敏适配器                   │
│  ● 分层记忆系统 (短期+中期+长期)              │
│  ● 冷启动种子记忆 + 引导问卷                   │
│  ● 种子记忆 → 快速收敛                        │
│  ▶ 可运行: "温馨一点" 这种模糊指令能正常工作    │
└──────────────────────────────────────────────┘

Phase 4: 多用户 & 发现 (2-3 周)
┌──────────────────────────────────────────────┐
│  ● 多用户画像 + 声纹识别                       │
│  ● 偏好冲突管理                               │
│  ● 设备发现服务 (mDNS/SSDP)                  │
│  ● 设备注册 Web UI 流程                       │
│  ● 自动修复流水线 (LLM 修复失败 skill)         │
│  ▶ 可运行: 多人使用 + 新设备自动发现           │
└──────────────────────────────────────────────┘

Phase 5: 自进化 (持续)
┌──────────────────────────────────────────────┐
│  ● /writing-skills 集成到 Agent 流程           │
│  ● Skill 导出/导入 (生态共享)                  │
│  ● 主动进化: "我发现一个规律，要写 skill 吗？"  │
│  ● 性能优化 + 压力测试                        │
│  ▶ 可运行: Agent 能自己写 skill 并部署         │
└──────────────────────────────────────────────┘
```

### 技术栈确认

| 层 | 技术 | 版本 | 理由 |
|----|------|------|------|
| 后端框架 | FastAPI | >=0.110 | 原生 async, 自动 API 文档, WebSocket |
| ASGI 服务 | Uvicorn | >=0.29 | FastAPI 官方推荐 |
| MQTT 客户端 | paho-mqtt | >=2.0 | Python MQTT 事实标准 |
| 数据库 | SQLAlchemy + SQLite → PostgreSQL | — | 平滑迁移 |
| 向量存储 | ChromaDB (轻量) | — | 本地运行，零配置 |
| 语音 STT | Whisper (本地) | — | 隐私优先 |
| 本地 LLM | Ollama + Qwen2.5 | — | 本地推理，性能均衡 |
| 前端 | Next.js + Tailwind CSS | — | PWA 支持 Web+移动端 |
| 容器化 | Docker Compose | — | 一键部署 |

---

> **下一阶段**: 如果你认可这份架构设计，我们将进入 Phase 1 的实现，从项目骨架 + 虚拟设备控制开始编码。
