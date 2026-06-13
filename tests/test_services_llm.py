"""
Tests for the LLM service module.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestLLMServiceJSONExtraction:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_json_direct(self):
        """Extract JSON when response is already valid JSON."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        result = service._extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_extract_json_from_code_block(self):
        """Extract JSON from markdown code block."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = service._extract_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_from_code_block_no_lang(self):
        """Extract JSON from code block without language specifier."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        text = '```\n{"key": "value"}\n```'
        result = service._extract_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_from_braces(self):
        """Extract JSON object from surrounding text."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        text = 'Here is the result: {"key": "value"} and more text'
        result = service._extract_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_array(self):
        """Extract JSON array from surrounding text."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        text = 'Results: [{"a": 1}, {"b": 2}] done'
        result = service._extract_json(text)
        assert result == '[{"a": 1}, {"b": 2}]'

    def test_extract_json_none_on_failure(self):
        """Return None when no JSON found."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        result = service._extract_json("No JSON here at all")
        assert result is None

    def test_extract_json_nested(self):
        """Extract nested JSON structures."""
        from services.llm_service import LLMService
        import json
        service = LLMService.__new__(LLMService)
        nested = {"outer": {"inner": [1, 2, 3]}}
        text = json.dumps(nested)
        result = service._extract_json(text)
        assert json.loads(result) == nested


class TestLLMPromptTemplates:
    """Tests for LLM prompt template initialization."""

    def test_protocol_understanding_template_exists(self):
        """Protocol understanding template is defined."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        service._init_prompts()
        assert hasattr(service, 'protocol_understanding_template')
        assert service.protocol_understanding_template is not None

    def test_test_generation_template_exists(self):
        """Test generation template is defined."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        service._init_prompts()
        assert hasattr(service, 'test_generation_template')
        assert service.test_generation_template is not None

    def test_vulnerability_classification_template_exists(self):
        """Vulnerability classification template is defined."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        service._init_prompts()
        assert hasattr(service, 'vulnerability_classification_template')

    def test_poc_generation_template_exists(self):
        """PoC generation template is defined."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        service._init_prompts()
        assert hasattr(service, 'poc_generation_template')


class TestLLMProtocolFormats:
    """Tests for protocol format definitions in LLM service."""

    def test_modbus_format_defined(self):
        """Modbus TCP format is defined in test generation."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        # Access the formats from generate_testcases method source
        import inspect
        source = inspect.getsource(service.generate_testcases)
        assert "modbus_tcp" in source

    def test_iec61850_format_defined(self):
        """IEC 61850 format is defined."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        import inspect
        source = inspect.getsource(service.generate_testcases)
        assert "iec61850" in source

    def test_dnp3_format_defined(self):
        """DNP3 format is defined."""
        from services.llm_service import LLMService
        service = LLMService.__new__(LLMService)
        import inspect
        source = inspect.getsource(service.generate_testcases)
        assert "dnp3" in source
