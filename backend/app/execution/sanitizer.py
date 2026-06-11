"""敏感信息混合过滤——正则 + NER 双阶段脱敏

用法:
  sanitizer = Sanitizer()
  text = sanitizer.clean("帮我查一下身份证 110101199001011234")
  # → "帮我查一下身份证 [ID_CARD]"

按路径分离:
  - 快路径（设备指令）: 完全跳过 Sanitizer
  - 慢路径（LLM 解析）: 必经 Sanitizer 脱敏
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 第一层：正则过滤（确定性，O(n)，无模型依赖）
# ============================================================

class RegexSanitizer:
    """第一层：正则表达式脱敏——手机号/身份证/邮箱/车牌/地址"""

    PATTERNS: List[Tuple[str, str, str]] = [
        # (正则, 替换模板, 脱敏类型)
        # 注意：身份证检测必须在手机号之前，因为身份证含手机号片段
        (r"\d{17}[\dXx]", "[ID_CARD]", "身份证"),
        (r"\d{6}19\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]", "[ID_CARD]", "身份证(严格)"),
        (r"(?<!\d)1[3-9]\d{9}(?!\d)", "[PHONE]", "手机号"),
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]", "邮箱"),
        (r"(京|津|沪|渝|冀|豫|云|辽|黑|湘|皖|鲁|新|苏|浙|赣|鄂|桂|甘|晋|蒙|陕|吉|闽|贵|粤|川|青|藏|琼|宁)[A-Z][A-HJ-NP-Z0-9]{5,6}", "[PLATE]", "车牌"),
        (r"(广东省|广西省|湖南省|湖北省|河南省|河北省|山东省|山西省|江苏省|浙江省|安徽省|福建省|江西省|四川省|贵州省|云南省|陕西省|甘肃省|青海省|辽宁省|吉林省|黑龙江省)?[^\s，。,.]{,10}(市|县|区|镇|乡|街道|村)[^\s，。,.]{,20}(路|街|巷|大道)[^\s，。,.]{,30}(号|栋|单元|室|楼|层)", "[ADDRESS]", "地址"),
    ]

    # 编译所有正则
    COMPILED = [(re.compile(p), tpl, typ) for p, tpl, typ in PATTERNS]

    @classmethod
    def clean(cls, text: str) -> str:
        """执行正则脱敏，返回脱敏后文本"""
        result = text
        for pattern, replacement, _ in cls.COMPILED:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def detect(cls, text: str) -> List[dict]:
        """检测敏感信息（不替换，仅报告）"""
        findings = []
        for pattern, replacement, typ in cls.COMPILED:
            matches = pattern.findall(text)
            for m in matches:
                findings.append({
                    "type": typ,
                    "matched": m[:20] + "..." if len(str(m)) > 20 else m,
                    "position": text.find(str(m)),
                })
        return findings


# ============================================================
# 第二层：NER 语义脱敏（本地小模型识别人名/疾病）
# ============================================================

class NerSanitizer:
    """第二层：本地 NER 模型脱敏——识别人名/疾病/机构等语义敏感信息

    使用 bert-base-chinese 或轻量模型。
    如果模型未下载/未安装，自动跳过（仅正则层依然生效）。
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.available = False
        self._try_load()

    def _try_load(self):
        """尝试加载 NER 模型——如果不可用则跳过"""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            import torch

            # 使用轻量中文 NER 模型
            model_name = os.getenv("NER_MODEL", "ckiplab/bert-base-chinese-ner")

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)
            self.model.eval()
            self.available = True
            logger.info(f"NER 模型已加载: {model_name}")
        except ImportError:
            logger.info("NER 模型不可用 (pip install transformers torch)")
        except Exception as e:
            logger.warning(f"NER 模型加载失败: {e}")

    def clean(self, text: str) -> str:
        """执行 NER 脱敏——识别人名/疾病/机构"""
        if not self.available:
            return text

        try:
            import torch
            inputs = self.tokenizer(text, return_tensors="pt",
                                    truncation=True, max_length=128)
            with torch.no_grad():
                outputs = self.model(**inputs)

            predictions = outputs.logits.argmax(dim=-1)[0].tolist()
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

            # 识别敏感实体
            entities = []
            current_entity = []
            current_label = None

            for token, pred in zip(tokens, predictions):
                label = self.model.config.id2label[pred]
                if label.startswith("B-"):
                    if current_entity:
                        entities.append(("".join(current_entity), current_label))
                    current_entity = [token]
                    current_label = label[2:]
                elif label.startswith("I-") and current_label:
                    current_entity.append(token)
                else:
                    if current_entity:
                        entities.append(("".join(current_entity), current_label))
                        current_entity = []
                        current_label = None

            if current_entity:
                entities.append(("".join(current_entity), current_label))

            # 替换敏感实体
            SENSITIVE_TYPES = {"PER", "DISEASE", "ORG", "GPE"}
            for entity_text, label in entities:
                if label in SENSITIVE_TYPES:
                    replacement = {
                        "PER": "[NAME]",
                        "DISEASE": "[DISEASE]",
                        "ORG": "[ORG]",
                        "GPE": "[ADDRESS]",
                    }.get(label, f"[{label}]")
                    text = text.replace(entity_text, replacement)

            return text

        except Exception as e:
            logger.warning(f"NER 脱敏失败: {e}")
            return text


# ============================================================
# Sanitizer 主类
# ============================================================

class Sanitizer:
    """敏感信息过滤主类——正则 + NER 双阶段"""

    def __init__(self):
        self.regex = RegexSanitizer()
        self.ner = NerSanitizer()
        self.log_path = Path("data/sanitizer_log.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def clean(self, text: str, context: str = "") -> str:
        """双阶段脱敏

        1. 正则过滤（确定性，覆盖手机号/身份证/邮箱/车牌/地址）
        2. NER 过滤（语义识别，覆盖人名/疾病/机构）
        """
        if not text:
            return text

        original = text

        # 第一阶段：正则
        text = self.regex.clean(text)

        # 第二阶段：NER
        text = self.ner.clean(text)

        # 如果实际发生了脱敏，记录日志
        if text != original:
            self._log(original, text, context)

        return text

    def detect(self, text: str) -> List[dict]:
        """检测敏感信息（不修改文本）"""
        return self.regex.detect(text)

    def _log(self, original: str, cleaned: str, context: str = ""):
        """记录脱敏操作（仅记录脱敏类型和时间，不记录原文）"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "context": context,
                "has_phone": bool(re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", original)),
                "has_idcard": bool(re.search(r"\d{17}[\dXx]", original)),
                "has_email": bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", original)),
                "changed": original != cleaned,
            }
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ============================================================
# 全局单例
# ============================================================

sanitizer = Sanitizer()
