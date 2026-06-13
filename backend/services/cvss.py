"""
CVSS 评分算法实现
CVSS 3.1 Base Score Calculator
"""
from typing import Dict, Any, Optional, Tuple
import math
import logging

logger = logging.getLogger(__name__)


class CVSSCalculator:
    """CVSS 3.1 评分计算器"""

    # 向量值映射
    METRICS = {
        "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},  # Attack Vector
        "AC": {"L": 0.77, "H": 0.44},  # Attack Complexity
        "PR": {"N": 0.85, "L": 0.62, "H": 0.27, "U": 0.27, "CL": 0.68, "CH": 0.50},  # Privileges Required (changed in 3.1)
        "UI": {"N": 0.85, "R": 0.62},  # User Interaction
        "S": {"U": 0.0, "C": 0.0},  # Scope (calculated)
        "C": {"H": 0.56, "L": 0.22, "N": 0.0},  # Confidentiality
        "I": {"H": 0.56, "L": 0.22, "N": 0.0},  # Integrity
        "A": {"H": 0.56, "L": 0.22, "N": 0.0},  # Availability
    }

    # 旧版本兼容 (3.0)
    METRICS_30 = {
        "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
        "AC": {"L": 0.77, "H": 0.44},
        "AU": {"N": 0.85, "S": 0.62},  # Authentication (3.0)
        "C": {"H": 0.56, "L": 0.22, "N": 0.0},
        "I": {"H": 0.56, "L": 0.22, "N": 0.0},
        "A": {"H": 0.56, "L": 0.22, "N": 0.0},
    }

    def __init__(self, version: str = "3.1"):
        self.version = version

    def parse_vector(self, vector: str) -> Dict[str, str]:
        """解析CVSS向量字符串"""
        result = {}
        metrics = vector.split("/")
        for metric in metrics:
            if ":" in metric:
                key, value = metric.split(":", 1)
                result[key] = value
        return result

    def build_vector(
        self,
        attack_vector: str = "N",
        attack_complexity: str = "L",
        privileges_required: str = "N",
        user_interaction: str = "N",
        scope: str = "U",
        confidentiality: str = "H",
        integrity: str = "H",
        availability: str = "H",
    ) -> str:
        """构建CVSS向量字符串"""
        if self.version == "3.1":
            return f"CVSS:3.1/AV:{attack_vector}/AC:{attack_complexity}/PR:{privileges_required}/UI:{user_interaction}/S:{scope}/C:{confidentiality}/I:{integrity}/A:{availability}"
        else:
            return f"CVSS:3.0/AV:{attack_vector}/AC:{attack_complexity}/AU:{privileges_required}/C:{confidentiality}/I:{integrity}/A:{availability}"

    def calculate_iss(self, c: float, i: float, a: float) -> float:
        """计算影响子分数 (ISS)"""
        iss = 1 - ((1 - c) * (1 - i) * (1 - a))
        return min(1, max(0, iss))

    def calculate_impact(
        self,
        iss: float,
        scope_unchanged: bool,
    ) -> float:
        """计算影响分数"""
        if self.version == "3.1":
            if scope_unchanged:
                impact = 6.42 * iss
            else:
                impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
        else:  # 3.0
            impact = 1 - (1 - c) * (1 - i) * (1 - a)
        
        return min(10, max(0, impact * 10))

    def calculate_exploitability(self, av: float, ac: float, pr: float, ui: float) -> float:
        """计算利用性分数"""
        if self.version == "3.1":
            return 8.22 * av * ac * pr * ui
        else:  # 3.0
            return 20 * av * ac * au

    def calculate_base_score(
        self,
        attack_vector: str = "N",
        attack_complexity: str = "L",
        privileges_required: str = "N",
        user_interaction: str = "N",
        scope: str = "U",
        confidentiality: str = "H",
        integrity: str = "H",
        availability: str = "H",
    ) -> Tuple[float, float, float, str]:
        """计算CVSS基础分数
        
        Returns: (base_score, impact_score, exploitability_score, severity)
        """
        try:
            # 获取度量值
            if self.version == "3.1":
                av = self.METRICS["AV"][attack_vector]
                ac = self.METRICS["AC"][attack_complexity]
                pr = self.METRICS["PR"].get(privileges_required, 0.62)
                ui = self.METRICS["UI"][user_interaction]
                c = self.METRICS["C"][confidentiality]
                i = self.METRICS["I"][integrity]
                a = self.METRICS["A"][availability]
            else:
                av = self.METRICS_30["AV"][attack_vector]
                ac = self.METRICS_30["AC"][attack_complexity]
                pr = self.METRICS_30["AU"].get(privileges_required, 0.62)  # AU in 3.0
                ui = 1.0  # No UI in 3.0
                c = self.METRICS_30["C"][confidentiality]
                i = self.METRICS_30["I"][integrity]
                a = self.METRICS_30["A"][availability]

            # 计算ISS
            iss = self.calculate_iss(c, i, a)

            # 计算影响
            scope_unchanged = scope == "U"
            impact = self.calculate_impact(iss, scope_unchanged)

            # 计算利用性
            exploitability = self.calculate_exploitability(av, ac, pr, ui)

            # 计算基础分数
            if impact <= 0:
                base_score = 0
            elif scope_unchanged:
                base_score = min(1.08 * (impact + exploitability), 10)
            else:
                base_score = min(1.08 * (impact + exploitability - 3.32), 10)

            base_score = math.ceil(base_score * 10) / 10

            # 确定严重性等级
            severity = self._get_severity(base_score)

            # 构建向量
            vector = self.build_vector(
                attack_vector, attack_complexity, privileges_required,
                user_interaction, scope, confidentiality, integrity, availability
            )

            return base_score, impact, exploitability, severity

        except Exception as e:
            logger.error(f"CVSS calculation error: {e}")
            return 0.0, 0.0, 0.0, "UNKNOWN"

    def _get_severity(self, score: float) -> str:
        """根据分数确定严重性"""
        if score >= 9.0:
            return "CRITICAL"
        elif score >= 7.0:
            return "HIGH"
        elif score >= 4.0:
            return "MEDIUM"
        elif score > 0:
            return "LOW"
        else:
            return "NONE"

    def calculate_from_crash(
        self,
        crash_type: str,
        crash_signal: Optional[str] = None,
        controllable_input: bool = True,
        requires_auth: bool = False,
        network_access: bool = True,
    ) -> Tuple[float, str, Dict[str, str]]:
        """从崩溃信息自动估算CVSS分数

        Args:
            crash_type: 崩溃类型 (sigsegv, sigabrt, timeout, etc.)
            crash_signal: 崩溃信号
            controllable_input: 输入是否可控
            requires_auth: 是否需要认证
            network_access: 是否需要网络访问
        """
        # Attack Vector
        av = "N" if network_access else "L"

        # Attack Complexity
        ac = "L"  # 默认低复杂度

        # Privileges Required
        if requires_auth:
            pr = "H" if not controllable_input else "L"
        else:
            pr = "N"
        
        # User Interaction
        ui = "N"  # 默认不需要用户交互
        
        # Scope - 默认unchanged
        s = "U"
        
        # 根据崩溃类型确定影响
        if crash_type in ["sigsegv", "sigbus", "sigill"]:
            # 内存相关崩溃 - 高影响
            c, i, a = "H", "H", "H"
        elif crash_type == "sigabrt":
            # 断言失败
            c, i, a = "M", "M", "M"
        elif crash_type == "timeout":
            # DoS可能性
            c, i, a = "L", "L", "H"
        else:
            c, i, a = "M", "M", "M"
        
        base_score, impact, exploitability, severity = self.calculate_base_score(
            attack_vector=av,
            attack_complexity=ac,
            privileges_required=pr,
            user_interaction=ui,
            scope=s,
            confidentiality=c,
            integrity=i,
            availability=a,
        )
        
        vector = self.build_vector(
            av, ac, pr, ui, s, c, i, a
        )
        
        return base_score, severity, {
            "vector": vector,
            "impact_score": f"{impact:.2f}",
            "exploitability_score": f"{exploitability:.2f}",
        }


# 全局实例
cvss_calculator = CVSSCalculator()
