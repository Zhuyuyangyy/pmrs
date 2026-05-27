"""
LLM服务 - 协议理解和测试用例生成
基于LangChain + Qwen/CodeLlama
"""
from typing import List, Optional, Dict, Any
import json
import re
import logging
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import JsonOutputParser

from core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """大模型服务 - 协议理解 + 测试用例生成"""

    def __init__(self):
        self.llm = self._init_llm()
        self._init_prompts()

    def _init_llm(self):
        """初始化大模型"""
        if settings.LLM_PROVIDER == "dashscope":
            try:
                from langchain.chat_models import ChatDashScope
                return ChatDashScope(
                    model_name=settings.LLM_MODEL or "qwen-plus",
                    dashscope_api_key=settings.DASHSCOPE_API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
            except ImportError:
                logger.warning("DashScope not available, using OpenAI-compatible")
                
        return ChatOpenAI(
            model=settings.LLM_MODEL or "gpt-4",
            openai_api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    def _init_prompts(self):
        """初始化提示模板"""
        
        # 协议理解提示 - 双通道（协议规范+代码语义）
        self.protocol_understanding_template = PromptTemplate(
            input_variables=["protocol", "code_content", "pcap_summary", "specification"],
            template="""你是一个工业控制协议安全专家。请分析以下工业控制协议的规范和实现代码，识别协议状态机、关键函数、潜在漏洞点。

## 协议类型
{protocol}

## 协议规范/规格说明
{specification}

## 代码实现摘要
{code_content}

## PCAP抓包摘要
{pcap_summary}

请以JSON格式输出分析结果，包含以下字段：
{{
    "states": ["状态列表"],
    "transitions": [{{"from": "状态A", "to": "状态B", "trigger": "触发条件"}}],
    "critical_functions": ["关键函数列表"],
    "potential_vulnerabilities": ["潜在漏洞描述列表"],
    "semantic_summary": "协议语义总结（100字内）",
    "security_notes": ["安全注意事项"]
}}

只输出JSON，不要有其他文字。
"""
        )

        # 测试用例生成提示
        self.test_generation_template = PromptTemplate(
            input_variables=["protocol", "state_context", "target_function", "num_testcases", "edge_case_ratio"],
            template="""你是一个工业控制协议模糊测试专家。请生成针对{protocol}协议的测试用例。

## 协议当前状态
{state_context}

## 目标函数/特性
{target_function}

## 生成要求
1. 生成{num_testcases}个测试用例
2. 其中{edge_case_ratio}%为边界/异常测试用例
3. 每个测试用例需要：格式正确、语义有效、能触发潜在漏洞

## {protocol}协议基本格式
{protocol_format}

## 输出格式（JSON数组）
[
    {{
        "function_code": "功能码(如0x03读取保持寄存器)",
        "raw_hex": "十六进制数据(如00000000000601030000000A)",
        "semantic_description": "测试这个读取0x0A个寄存器的请求",
        "state_transition": "发送后进入等待响应状态",
        "edge_case": false,
        "expected_behavior": "正常响应或超时"
    }}
]

只输出JSON数组，不要有其他文字。
"""
        )

        # 漏洞分类提示
        self.vulnerability_classification_template = PromptTemplate(
            input_variables=["crash_info", "protocol", "backtrace"],
            template="""分析以下崩溃信息，对漏洞进行分类和CVSS评分。

## 协议类型
{protocol}

## 崩溃信息
{crash_info}

## 回溯信息
{backtrace}

## 输出格式（JSON）
{{
    "vulnerability_type": "漏洞类型(buffer_overflow/injection/dos等)",
    "severity": "CRITICAL/HIGH/MEDIUM/LOW/INFO",
    "cvss_base_score": 0.0-10.0,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/...",
    "title": "漏洞标题",
    "description": "漏洞描述",
    "remediation": "修复建议"
}}

只输出JSON，不要有其他文字。
"""
        )

        # PoC生成提示
        self.poc_generation_template = PromptTemplate(
            input_variables=["vulnerability", "protocol"],
            template="""为以下漏洞生成可用的PoC（概念验证代码）。

## 漏洞信息
{vulnerability}

## 协议类型
{protocol}

## 要求
1. 生成可实际执行的Python代码
2. 使用socket发送原始数据包
3. 代码需要包含详细的注释
4. 代码需要处理连接和错误

## 输出格式
```python
# PoC代码
import socket
...
```

只输出代码和简短说明，不要有其他文字。
"""
        )

    async def understand_protocol(
        self,
        protocol: str,
        code_content: Optional[str] = None,
        pcap_summary: Optional[str] = None,
        specification: Optional[str] = None,
    ) -> Dict[str, Any]:
        """协议理解 - 双通道联合分析"""
        try:
            chain = LLMChain(llm=self.llm, prompt=self.protocol_understanding_template)
            result = await chain.arun(
                protocol=protocol,
                code_content=code_content or "无可用代码",
                pcap_summary=pcap_summary or "无可用抓包",
                specification=specification or "无可用规范",
            )
            
            # 解析JSON结果
            json_str = self._extract_json(result)
            if json_str:
                return json.loads(json_str)
            return {"error": "Failed to parse protocol understanding result"}
        except Exception as e:
            logger.error(f"Protocol understanding failed: {e}")
            return {"error": str(e)}

    async def generate_testcases(
        self,
        protocol: str,
        state_context: Optional[str] = None,
        target_function: Optional[str] = None,
        num_testcases: int = 10,
        edge_case_ratio: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """LLM驱动测试用例生成"""
        protocol_formats = {
            "modbus_tcp": """
Modbus TCP 格式:
- 事务标识符(2字节) + 协议标识符(2字节) + 长度(2字节) + 单元标识符(1字节) + 功能码(1字节) + 数据
- 常用功能码: 0x03读取保持寄存器, 0x06写入单个寄存器, 0x10写入多个寄存器
- 示例: 00000000000601030000000A (读取保持寄存器0x00-0x09)
""",
            "iec61850": """
IEC 61850 格式:
- APDU结构，包含ASDU和ApplicationServiceDataUnit
- 建议使用MMS协议进行测试
- 关注Read/Write/Control服务
""",
            "dnp3": """
DNP3 格式:
- 数据链路层: 0x0564 + 长度 + 控制字节 + 目标地址 + 源地址 + CRC
- 传输层: Fragment序列
- 应用层: Function Code + Object Header + Data
"""
        }
        
        try:
            chain = LLMChain(llm=self.llm, prompt=self.test_generation_template)
            result = await chain.arun(
                protocol=protocol,
                state_context=state_context or "初始状态",
                target_function=target_function or "通用测试",
                num_testcases=num_testcases,
                edge_case_ratio=int(edge_case_ratio * 100),
                protocol_format=protocol_formats.get(protocol, ""),
            )
            
            json_str = self._extract_json(result)
            if json_str:
                testcases = json.loads(json_str)
                # 验证和清理测试用例
                return [tc for tc in testcases if isinstance(tc, dict) and "raw_hex" in tc]
            return []
        except Exception as e:
            logger.error(f"Test case generation failed: {e}")
            return []

    async def classify_vulnerability(
        self,
        crash_info: str,
        protocol: str,
        backtrace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """漏洞分类 + CVSS评分"""
        try:
            chain = LLMChain(llm=self.llm, prompt=self.vulnerability_classification_template)
            result = await chain.arun(
                crash_info=crash_info,
                protocol=protocol,
                backtrace=backtrace or "无可用回溯",
            )
            
            json_str = self._extract_json(result)
            if json_str:
                return json.loads(json_str)
            return {}
        except Exception as e:
            logger.error(f"Vulnerability classification failed: {e}")
            return {}

    async def generate_poc(
        self,
        vulnerability: Dict[str, Any],
        protocol: str,
    ) -> str:
        """生成PoC代码"""
        try:
            chain = LLMChain(llm=self.llm, prompt=self.poc_generation_template)
            result = await chain.arun(
                vulnerability=json.dumps(vulnerability),
                protocol=protocol,
            )
            return result
        except Exception as e:
            logger.error(f"PoC generation failed: {e}")
            return f"PoC generation failed: {e}"

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON"""
        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except:
            pass
        
        # 尝试提取 ```json ... ``` 块
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1).strip()
        
        # 尝试提取 { ... } 或 [ ... ]
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            return match.group(1).strip()
        
        return None


# 全局单例
llm_service = LLMService()
