# Skill System Test Architecture v1.0

> **状态**: Frozen | **发布日期**: 2026-06-11  
> **作者**: Home Steward Agent Team

---

## 范围总览

| 阶段 | 模块 | 状态 | 测试数 |
|:----|:----|:----:|:------:|
| Phase 1 | 测试基础设施 (Fixtures + Helpers) | ✅ Frozen | 7 fixtures |
| Phase 2.1 | `arbiter.py` — 三层冲突仲裁 | ✅ Frozen | 28 |
| Phase 2.2 | `runtime.py` — Skill 运行时 | ✅ Frozen | 21 |
| Phase 2.3 | `registry.py` — Skill 仓库 | ✅ Frozen | 26 |
| **合计** | **核心模块** | **✅ 冻结** | **≈75** |

| 指标 | 当前 | 目标 |
|:----|:----:|:----:|
| 项目级覆盖率 (fail_under) | 31% (v1.0) | 30% → 60% → 80% |
| 核心模块 (arbiter/runtime/registry) | 98% / 99% / 94% | ≥ 90% |
| 下一版本 | — | v1.1 — health/quality/sandbox/integration |

---

## 1. 概述与背景

### 1.1 当前测试现状

Home Steward Agent 的 Skill 系统是 Phase 2 的核心子系统，共 11 个模块：

| 模块 | 文件 | 行数 | 当前测试 | 职责 |
|:----|:----|:----:|:--------:|------|
| `runtime.py` | Skill 加载/执行/生命周期 | ~120 | ❌ 0 | 核心 |
| `registry.py` | 注册/发现/安装/卸载 | ~120 | ❌ 0 | 核心 |
| `arbiter.py` | 三层冲突仲裁 | ~125 | ❌ 0 | 关键 |
| `health.py` | 三层健康监测 | ~100 | ❌ 0 | 关键 |
| `quality.py` | 日质量评分/趋势/告警 | ~95 | ❌ 0 | 重要 |
| `sandbox.py` | 回滚沙箱隔离验证 | ~130 | ❌ 0 | 重要 |
| `conflict_predictor.py` | 安装前冲突预测 | ~100 | ❌ 0 | 重要 |
| `version_contract.py` | 版本兼容性声明 | ~90 | ❌ 0 | 重要 |
| `auto_repair.py` | LLM 自动修复流水线 | ~85 | ❌ 0 | 辅助 |
| `ecosystem.py` | 数量上限/归档/合并建议 | ~100 | ❌ 0 | 辅助 |
| `template_registry.py` | 社区模板仓库 | ~110 | ❌ 0 | 辅助 |

现有测试仅有 `skills/built-in/device-control/tests/test_main.py` 的 2 个集成测试用例，且不覆盖任何 Skill 系统模块。无测试基础设施（无 conftest.py、无 fixture、无 mock 工具、无 pytest 配置）。

### 1.2 测试目标

1. **为核心模块建立 90%+ 覆盖率基线**，确保仲裁、运行时、注册三大核心逻辑可靠
2. **建立可复用的测试基础设施**，所有 fixture 遵循单向依赖、function scope、可组合原则
3. **接口契约优先** — 测试验证行为合约（awaitable 约束、幂等性、错误处理），而非实现细节
4. **混合测试策略** — 纯逻辑测试 + 真实文件系统测试分层，避免全 mock 遗漏真实加载问题

### 1.3 测试金字塔

| 层级 | 当前状态 | 目标比例 |
|:----|:--------:|:--------:|
| Unit (模块级) | 75 用例 | 主体 (≈80%) |
| Integration (跨模块) | v1.1 | 次重点 (≈15%) |
| E2E (全链路) | v1.1+ | 少量关键路径 (≈5%) |

Skill 系统遵循标准测试金字塔。优先保证 Unit Test 的深度与覆盖率，Integration Test 覆盖关键业务链路，E2E 仅覆盖最核心的用户路径。禁止在 Unit 覆盖率不达标的情况下堆叠 E2E 测试。

### 1.4 测试设计原则

| 原则 | 含义 |
|:----|------|
| **单向依赖** | fixture 依赖方向单一，禁止循环依赖 |
| **混合策略** | execute 层 mock，加载层 tmp_path，manifest 层 tmp_path |
| **幂等优先** | discover() 等操作必须幂等 |
| **契约测试** | 验证接口合约（返回类型、awaitable、错误格式），而非内部实现 |
| **function scope** | 所有有状态 fixture 默认 function scope，防止测试间污染 |
| **异常全覆盖** | 每个公共方法必须有正常路径 + 至少一条异常路径测试 |

---

## 2. 测试基础设施 (Phase 1)

### 2.1 目录结构

```
tests/
├── conftest.py                    # 顶层 fixtures + pytest 配置
├── fixtures/
│   ├── __init__.py
│   ├── skill_factory.py           # fake_skill() + skill_factory(profile=...)
│   ├── registry_factory.py        # registry()
│   ├── runtime_factory.py         # runtime(skill, safety, clock)
│   ├── mqtt_fake.py               # fake_mqtt_client()
│   ├── safety_fake.py             # fake_safety_layer()
│   ├── storage_fake.py            # fake_storage()
│   └── clock_fake.py              # fake_clock() — freezegun 封装
├── unit/
│   ├── test_arbiter.py
│   ├── test_runtime.py
│   ├── test_registry.py
│   ├── test_health.py             # v1.1
│   ├── test_quality.py            # v1.1
│   ├── test_sandbox.py            # v1.1
│   ├── test_conflict_predictor.py # v1.1
│   ├── test_version_contract.py   # v1.1
│   ├── test_auto_repair.py        # v1.1
│   ├── test_ecosystem.py          # v1.1
│   └── test_template_registry.py  # v1.1
├── integration/                   # v1.1
│   ├── conftest.py
│   ├── test_install_load_execute.py
│   ├── test_conflict_arbitration.py
│   ├── test_health_auto_repair.py
│   └── test_full_rollback_chain.py
├── e2e/                           # v1.1+
├── helpers/
│   ├── __init__.py
│   └── assertions.py              # assert_health_status(), assert_arbiter_resolution()
└── (pytest 配置见 pyproject.toml)
```

### 2.2 测试依赖与配置

**requirements-dev.txt:**

```txt
pytest>=8.0
pytest-asyncio>=0.24
pytest-mock>=3.14
pytest-cov>=5.0
freezegun>=1.5
hypothesis>=6.100              # 在 arbiter 中用于随机冲突组合测试
```

**pyproject.toml:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Unit tests for individual modules",
    "integration: Integration tests across multiple modules",
    "slow: Tests that take longer than 5 seconds",
]

[tool.coverage.run]
source = ["backend/app/skill"]
omit = ["*/__init__.py"]

[tool.coverage.report]
fail_under = 60
show_missing = true
skip_covered = false
```

### 2.3 Fixture 体系

| Fixture | 文件 | Scope | 依赖 | 职责 |
|---------|:----:|:-----:|:----:|------|
| `fake_skill()` | `skill_factory.py` | function | — | 返回 Skill 实例，可配置 name/version/priority/domains |
| `skill_factory(profile=...)` | `skill_factory.py` | — | — | 预设 8 种 Skill 类型（normal/missing_manifest/missing_main/crash/timeout/conflict/incompatible_version/unhealthy） |
| `registry()` | `registry_factory.py` | function | — | 空 SkillRegistry 实例，不预注册任何 Skill |
| `runtime(skill, safety, clock)` | `runtime_factory.py` | function | skill_factory, safety_fake, clock_fake | Skill 运行时实例，依赖显式注入 |
| `fake_mqtt_client()` | `mqtt_fake.py` | function | — | 模拟消息总线，记录 events 历史 |
| `fake_safety_layer()` | `safety_fake.py` | function | — | 模拟安全层，validate/execute 可配置行为 |
| `fake_storage()` | `storage_fake.py` | function | — | 统一的持久化模拟 |
| `fake_clock()` | `clock_fake.py` | function | freezegun | 时间控制封装 |

**`skill_factory(profile=...)` 预设类型:**

```python
profile="normal"                # 标准合法 Skill
profile="missing_manifest"      # 缺少 SKILL.md
profile="missing_main"          # 缺少 main.py
profile="crash"                 # handle 执行抛异常
profile="timeout"               # handle 执行超时（v1.1）
profile="conflict"              # 与已有 Skill 域重叠
profile="incompatible_version"  # 版本不兼容（v1.1）
profile="unhealthy"             # 低健康度（供 health 测试用）
```

**扩展支持 overrides:**

```python
skill_factory(
    profile="conflict",
    overrides={"priority": 999, "domains": ["lighting"]}
)
```

### 2.4 Fixture 依赖关系

```
                    ┌──────────────────┐
                    │  fake_clock()     │
                    │  (freezegun封装)   │
                    └────────┬─────────┘
                             │
┌──────────────┐    ┌────────┴─────────┐    ┌──────────────┐
│ fake_skill() │    │  runtime()       │    │ fake_mqtt()  │
│              │───▶│  (skill + safety │    │ (events记录)  │
│ skill_factory│    │   + clock)       │    └──────────────┘
│ (profile)    │    └────────┬─────────┘
└──────────────┘             │
                             │
┌──────────────┐    ┌────────┴─────────┐
│ registry()   │    │ fake_safety()    │
│ (空实例)      │    │ (可配置行为)      │
└──────────────┘    └──────────────────┘

┌──────────────┐
│ fake_storage()│
│ (统一持久化)   │
└──────────────┘
```

**依赖方向规则:**
- registry → 独立，不依赖其他 fixture
- runtime → 依赖 skill + safety + clock（单向注入）
- 所有 fixture 默认 function scope

### 2.5 Helpers 与断言工具

```python
# tests/helpers/assertions.py

def assert_arbiter_resolution(arbiter, intents, expected):
    """验证一组意图的仲裁结果序列与预期一致"""
    ...

def assert_health_status(health_data, expected_level):
    """验证健康状态分类正确 (healthy/warning/critical/offline)"""
    ...
```

### 2.6 测试约定

1. **默认 function scope**: 所有有状态 fixture 必须使用 `scope="function"`，禁止未加评估就使用 `scope="module"` 或 `scope="session"`
2. **禁止 fixture 隐式创建**: fixture 不得在初始化时隐式创建它不负责的模块（如 registry fixture 不预注册 Skill）
3. **禁止循环依赖**: fixture 依赖图必须是有向无环图

---

## 3. 核心模块单元测试 (Phase 2)

### 3.1 arbiter.py — 三层冲突仲裁

**模块职责:** 接收 intent + priority，执行三层仲裁，返回 intent(放行) 或 None(拒绝)。

**仲裁规则矩阵:**

| 条件 | Layer 1 | Layer 2 | Layer 3 | 结果 |
|------|:-------:|:-------:|:-------:|:----:|
| `source="user"` | ✅ 放行 | — | — | ✅ |
| 无冲突历史 | — | ✅ 放行 | — | ✅ |
| 不同设备/域 | — | ✅ 放行 | — | ✅ |
| 更高 priority 覆盖 | — | ✅ 覆盖 | — | ✅ |
| 更低 priority 被拒 | — | ⛔ 拒绝 | — | ❌ |
| 同 priority, 切换 < 2 | — | — | ✅ 放行 | ✅ |
| 同 priority, 切换 ≥ 2 | — | — | ⛔ 拒绝 | ❌ |
| 超过 30s 窗口 | — | 视为新冲突 | 重置 | ✅/❌ |

**测试分组 (28 测试):**

| 分组 | 测试数 | 覆盖内容 |
|:----|:------:|---------|
| TestLayer1UserOverride | 3 | 用户无条件放行、覆盖高优先级、绕过防震荡 |
| TestLayer2Priority | 6 | 无冲突/不同设备/不同域 / 高覆盖 / 低被拒 / 极值 |
| TestLayer3AntiOscillation | 3 | 2 次切换阻止、多次阻止、同意图不算切换 |
| TestTimeWindow | 5 | 30s 记忆、31s 过期、29s 边界、30s 精确、多窗口 |
| TestEdgeCases | 6 | 空 device、缺失 device、空 domain、priority 异常类型、intent None |
| TestConcurrency | 1 | 10 线程并发调用，deque 不损坏 |
| TestArbiterHypothesis | 3 | 随机冲突组合、切换预算、user 不变性 |
| TestGetRecent | 1 | 按设备查询历史 |

**新增代码加固:** `resolve()` 对 `skill_priority` 做类型检查，非 int 抛 TypeError。

**覆盖率目标:** 100% 分支覆盖 (≥95% 语句覆盖, 12/12 路径)

### 3.2 runtime.py — Skill 运行时

**模块职责:** Skill 加载（动态 Python 模块导入）、执行（handle 函数调度）、信息查询。

**测试分层策略:**

| Layer | 测试方式 | 权重 | 覆盖 |
|:-----|:--------|:---:|------|
| A — Execute | mock handler / fake_skill | 40% | execute() 6 条路径 |
| B — Manifest | tmp_path 真实文件 | 20% | _load_manifest() 异常 |
| C — Module  | tmp_path 真实文件 | 30% | _load_module() 动态加载 |
| D — Info    | fake_skill | 10% | get_info() |

**测试分组 (21 测试):**

| 分组 | 测试数 | 覆盖内容 |
|:----|:------:|---------|
| TestExecute | 6 | 正常/禁用/无模块/无handler/异常/非awaitable返回值 |
| TestManifestLoading | 6 | 合法/MD缺失/YAML格式错误/必填字段缺失/UTF8/非UTF8编码 |
| TestModuleLoading | 6 | 合法main.py/缺失/import错误/语法错误/无handle/非async handle |
| TestGetInfo | 2 | 完整信息/部分manifest |
| TestReload | 1 | 文件变更后重新加载生效 |

**执行契约（新增代码加固）:**

```python
result = handler(intent, context)
if not inspect.isawaitable(result):
    return {"error": "handler_not_async", "message": "handle must return an awaitable"}
return await result
```

**覆盖率目标:** ≥90% 分支覆盖，execute() 100% 分支

### 3.3 registry.py — Skill 仓库

**模块职责:** Skill 安装、卸载、发现扫描、查询管理。

**测试分层策略:**

| Layer | 测试方式 | 覆盖 |
|:-----|:--------|------|
| A — 查询 | fake_skill 纯逻辑 | get()/list()/count() |
| B — 安装/卸载 | tmp_path 真实目录操作 | install()/uninstall() 完整周期 |
| C — 发现扫描 | tmp_path 真实目录结构 | discover() 各级目录 |
| D — 错误恢复 | tmp_path + mock | 部分失败、重复、权限 |

**测试分组 (26 测试):**

| 分组 | 测试数 | 覆盖内容 |
|:----|:------:|---------|
| TestRegistryQueries | 7 | get 存在/不存在、list_by_domain 匹配/不匹配、list_enabled/全禁用、count |
| TestRegistryInstall | 6 | 合法安装/路径不存在/缺main.py/覆盖安装/降级覆盖/pre_install_状态 |
| TestRegistryUninstall | 4 | 卸载已存在/不存在/磁盘清理/文件删除失败 |
| TestRegistryDiscover | 6 | 空目录/多合法/指定路径/路径不存在/部分失败/幂等性 |
| TestErrorRecovery | 3 | copytree 失败/rmtree 失败/discover 路径不存在 |

**关键契约:**
- `discover()` 必须幂等 — 第二次发现同路径不重复加载
- `install()` 同名 Skill 执行覆盖，不阻止降级
- `uninstall()` 文件删除失败时仍从内存移除

**覆盖率目标:** ≥90% 分支覆盖

### 3.4 覆盖率与风险映射

| 风险场景 | 覆盖模块 | 覆盖方式 |
|---------|:--------:|---------|
| 仲裁逻辑错误导致错 Skill 执行 | arbiter | L2 优先级矩阵全覆盖 |
| 同优先级冲突震荡 | arbiter | L3 防震荡 + Hypothesis 随机组合 |
| 用户指令被 Skill 冲突阻塞 | arbiter | L1 user bypass 测试 |
| 动态加载恶意/损坏代码 | runtime | Module Loading 6 异常路径 |
| 非 async handler 导致执行崩溃 | runtime | execute 契约检查 |
| 安装后 get() 找不到 | registry | install → get 完整链路 |
| 卸载后磁盘残留 | registry | uninstall + disk cleanup 校验 |
| discover() 重复加载/丢失 | registry | 幂等性 + 部分失败测试 |

---

## 4. 测试治理

### 4.1 测试命名规范

```python
# 格式: test_{module}_{scenario}_{expected}
# 示例:
test_arbiter_higher_priority_overrides
test_runtime_execute_disabled_skill
test_registry_install_valid_skill

# Class 分组:
TestLayer1UserOverride
TestLayer2Priority
TestRegistryInstall

# 禁止:
test1, test2, check_xxx, verify_xxx
```

### 4.2 Fixture 使用规范

1. **默认 function scope** — 有状态 fixture 禁止随意提升 scope
2. **禁止 fixture 隐式创建依赖** — registry fixture 不预注册 Skill，runtime fixture 不自动创建 SafetyLayer
3. **禁止 fixture 循环依赖** — fixture 依赖图必须保持有向无环
4. **测试内显式安装** — 测试自己通过 `registry.install(skill)` 控制状态，不依赖 fixture 预置

### 4.3 Mock 使用原则

| 测试对象 | Mock 策略 | 理由 |
|---------|:--------:|------|
| execute() handler | ✅ mock | 纯逻辑路径覆盖 |
| _load_manifest() | ❌ 不 mock, 用 tmp_path | YAML 解析 + 文件编码需要真实行为 |
| _load_module() | ❌ 不 mock, 用 tmp_path | importlib 动态加载无法被 mock 真实验证 |
| install() 文件操作 | ⚠️ 正常用 tmp_path, 异常用 mock | copytree/rmtree 失败用 mock 模拟 |
| time.time() | ⚠️ freezegun 统一封装 | 避免直接 mock 标准库 |

### 4.4 新模块测试准入要求

新增模块（如 `policy_engine.py`、`scheduler.py`）加入测试体系时需满足:

1. 至少 80% 语句覆盖率
2. 每个公共方法至少有一个正常路径 + 一个异常路径测试
3. 必须有边界条件测试（空输入、非法输入、极值）
4. 如果涉及文件系统，必须包含 tmp_path 测试（不依赖本地环境）

### 4.5 禁止测试内容

以下行为在测试中禁止出现：

- **测试私有实现细节** — 不测试以 `_` 开头的内部方法（如 `_record()`、`_load_manifest()` 由公共方法测试间接覆盖）
- **测试日志字符串** — 不断言 `logger.warning()` 的输出内容
- **测试第三方库行为** — 不验证 `yaml.safe_load` 或 `importlib` 的底层行为
- **Mock 被测对象自身** — 禁止 mock `Skill.execute()` 后再测试 `Skill.execute()`
- **为提高覆盖率写无价值测试** — 形如 `def test_x(): pass` 或只调用不断言

### 4.6 Review Checklist

Code Review 中检查测试时:

- [ ] 是否覆盖了正常路径 + 至少一条异常路径？
- [ ] 是否包含边界条件测试？
- [ ] fixture 是否使用了正确 scope？（有状态 → function）
- [ ] 是否有隐式 fixture 依赖？（registry 预注册了 Skill）
- [ ] 命名是否符合 `test_{module}_{scenario}_{expected}` 规范？
- [ ] 是否 mock 了不该 mock 的东西？（如 importlib、YAML 解析）
- [ ] 断言是否精确？（`>= 2` vs 具体值）

---

## 5. 覆盖率目标

### 5.1 模块级目标

| 模块 | 目标覆盖率 | 优先级 | 备注 |
|:----|:---------:|:------:|------|
| `arbiter.py` | 95%+ | P0 | 决策中枢，必须接近全覆盖 |
| `runtime.py` | 90%+ | P0 | execute() 要求 100% 分支 |
| `registry.py` | 90%+ | P0 | install/uninstall 全路径 |
| `health.py` | 85%+ | P1 | v1.1 |
| `quality.py` | 85%+ | P1 | v1.1 |
| `sandbox.py` | 80%+ | P1 | v1.1 |
| `conflict_predictor.py` | 80%+ | P1 | v1.1 |
| `version_contract.py` | 80%+ | P1 | v1.1 |
| `auto_repair.py` | 70%+ | P2 | v1.1 |
| `ecosystem.py` | 60%+ | P2 | v1.1 |
| `template_registry.py` | 60%+ | P2 | v1.1 |

### 5.2 项目级目标

| 阶段 | 目标 | 触发条件 |
|:----|:----:|---------|
| Phase 2 完成 | ≥ 60% | CI fail_under |
| Phase 2 + v1.1 核心 | ≥ 75% | 里程碑 |
| 最终目标 | ≥ 85% | 发布门禁 |

### 5.3 Coverage 演进策略

当前覆盖率 31%（3/11 模块已测）。随着 v1.1 逐步覆盖剩余 8 个模块，fail_under 阶梯递增：

```text
v1.0 (Phase 2, 3 模块):     fail_under = 30  ← 当前
v1.1 (剩余 8 模块 + v1.0):    fail_under = 60
v1.2 (集成测试加入):          fail_under = 80
```

每次提升前需确保新增模块的测试已达到或超过该模块的目标覆盖率。

每个版本递增 fail_under，防止团队长期停留在 60% 不再增长。每次提升前需确保当前基线稳定。

### 5.4 fail_under 策略

```toml
# Phase 2 完成后立即启用
[tool.coverage.report]
fail_under = 60
```

CI 流水线中，`coverage report --fail-under=60` 低于阈值则阻断。

---

## 6. CI/CD 集成

### 6.1 pytest 执行

```bash
# 单元测试
pytest tests/unit/ -v --tb=short

# 含覆盖率
pytest tests/ --cov=backend/app/skill -v --cov-report=term-missing

# 排除慢测试（默认不执行）
pytest tests/ -v -m "not slow"
```

### 6.2 Coverage 输出

```bash
coverage run -m pytest tests/unit/
coverage report --fail-under=60
coverage html  # 输出到 htmlcov/ 供审查
```

### 6.3 GitHub Actions / CI Gate

```yaml
# .github/workflows/test.yml (建议)
- name: Run unit tests with coverage
  run: |
    pytest tests/unit/ --cov=backend/app/skill \
      --cov-report=term-missing --cov-report=xml
- name: Enforce coverage threshold
  run: coverage report --fail-under=60
```

### 6.4 PR 阻断规则

| 检查项 | 阻断 | 警告 |
|:------|:----:|:----:|
| pytest 通过 | ✅ | — |
| fail_under ≥ 60% | ✅ | — |
| 核心模块覆盖率下降 > 5% | — | ⚠️ 人工审查 |
| 新增类型无测试 | — | ⚠️ 治理规范提醒 |

---

## 7. 后续规划 (v1.1)

以下内容计划在 v1.1 中完成，不在当前 v1.0 实现范围内。

### 7.1 health.py 测试

- 三层监测策略验证（被动/主动/集成）
- 加权评分算法正确性
- P99 延迟计算
- should_disable 阈值判定
- 边界：空记录、满 100 条翻转

### 7.2 quality.py 测试

- 日质量评分计算
- 趋势分析（上升/下降/平稳）
- 连续 3 天下降告警逻辑
- 历史持久化（flush/load）

### 7.3 sandbox.py 测试

- 接口签名兼容性（_extract_functions AST 解析）
- Schema 变化检测
- 缺失 tests 目录降级
- pytest 执行超时处理
- 临时目录清理

### 7.4 conflict_predictor.py 测试

- 域重叠检测
- 概率估算准确性
- 空域名/无 manifest 降级
- 边界概率 (0.3 阈值)

### 7.5 集成测试链路

| 链路 | 涉及模块 | 价值 |
|:----|:--------|:----:|
| 安装 → 加载 → 执行 | registry → runtime | 最核心 |
| 冲突 → 仲裁 | registry → arbiter | 决策正确性 |
| 执行失败 → 健康检测 → 自动修复 | runtime → health → auto_repair | 闭环 |
| 全链路回滚 | conflict_predictor → sandbox → registry → runtime → health | 最接近生产 |

### 7.6 E2E 测试

- REST API → 安装 Skill → 验证注册表 → 执行 → 验证结果
- 完整生命周期：草稿 → 沙箱 → 灰度 → 生产 → 回滚

---

## 8. 实施路线图

### Sprint 1 — 测试基础设施 + arbiter

```
Phase 1:
├── conftest.py + fixtures/ (7 fixtures)
├── helpers/assertions.py
├── pyproject.toml (pytest + coverage 配置)
└── requirements-dev.txt

Phase 2.1:
└── tests/unit/test_arbiter.py (28 测试)
```

可交付: `pytest tests/unit/test_arbiter.py -v --tb=short` 全部通过

### Sprint 2 — runtime 测试

```
Phase 2.2:
├── tests/unit/test_runtime.py (21 测试)
└── A+B 混合策略 (execute→mock, manifest/module→tmp_path)
```

### Sprint 3 — registry 测试

```
Phase 2.3:
└── tests/unit/test_registry.py (26 测试)
```

### Sprint 4 — CI + Coverage Gate

```
└── GitHub Actions workflow
    ├── pytest 运行
    ├── coverage report --fail-under=60
    └── PR 阻断规则
```

### Sprint 5+ — v1.1 (后续迭代)

```
├── health.py 测试
├── quality.py 测试
├── sandbox.py 测试
├── conflict_predictor.py 测试
├── version_contract.py 测试
├── auto_repair.py 测试
├── ecosystem.py 测试
├── template_registry.py 测试
├── 集成测试 (4 条全链路)
├── fail_under → 70
└── E2E 测试核心路径
