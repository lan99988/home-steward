---
name: device-control
version: 1.0.0
description: 基础设备开关控制能力
domains:
  - domain: light
    operations: [turn_on, turn_off, set_brightness]
  - domain: climate
    operations: [turn_on, turn_off, set_temperature, set_mode]
  - domain: curtain
    operations: [turn_on, turn_off, set_position]
priority: 50
conflict_resolution: yield_on_user
compatible_with:
  api_version: "1.0.0"
  memory_format: "v1"
  system: ">=0.1.0"
---

# 设备控制 Skill

基础的设备开关和控制能力。覆盖灯、空调、窗帘等常见设备的开关和参数调节。
