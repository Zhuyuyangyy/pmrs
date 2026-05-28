"""
Unit tests for the CVSS 3.1 calculator.

Run:
    cd D:/ZYY Project/pmrs
    python -m pytest tests/test_cvss.py -v
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.cvss import CVSSCalculator


class TestCVSSCalculator:
    """Tests for the CVSS 3.1 base score calculator."""

    @pytest.fixture
    def calc(self):
        return CVSSCalculator(version="3.1")

    def test_critical_score(self, calc):
        """Network/Low/None/None/Unchanged/H/H/H should yield CRITICAL."""
        score, impact, exploit, severity = calc.calculate_base_score(
            attack_vector="N",
            attack_complexity="L",
            privileges_required="N",
            user_interaction="N",
            scope="U",
            confidentiality="H",
            integrity="H",
            availability="H",
        )
        assert score >= 9.0
        assert severity == "CRITICAL"

    def test_high_score(self, calc):
        """Adjacent/Low/Low/None/Unchanged/H/H/H should yield HIGH."""
        score, impact, exploit, severity = calc.calculate_base_score(
            attack_vector="A",
            attack_complexity="L",
            privileges_required="L",
            user_interaction="N",
            scope="U",
            confidentiality="H",
            integrity="H",
            availability="H",
        )
        assert 7.0 <= score < 9.0
        assert severity == "HIGH"

    def test_medium_score(self, calc):
        """Network/High/High/Required/Unchanged/L/L/L should yield MEDIUM or lower."""
        score, impact, exploit, severity = calc.calculate_base_score(
            attack_vector="N",
            attack_complexity="H",
            privileges_required="H",
            user_interaction="R",
            scope="U",
            confidentiality="L",
            integrity="L",
            availability="L",
        )
        assert score < 7.0
        assert severity in ("MEDIUM", "LOW")

    def test_none_score(self, calc):
        """All None impact should yield NONE."""
        score, impact, exploit, severity = calc.calculate_base_score(
            attack_vector="N",
            attack_complexity="L",
            privileges_required="N",
            user_interaction="N",
            scope="U",
            confidentiality="N",
            integrity="N",
            availability="N",
        )
        assert score == 0.0
        assert severity == "NONE"

    def test_scope_changed(self, calc):
        """Scope changed increases the score."""
        score_unchanged, _, _, _ = calc.calculate_base_score(
            attack_vector="N", attack_complexity="L",
            privileges_required="N", user_interaction="N",
            scope="U", confidentiality="H", integrity="H", availability="H",
        )
        score_changed, _, _, _ = calc.calculate_base_score(
            attack_vector="N", attack_complexity="L",
            privileges_required="N", user_interaction="N",
            scope="C", confidentiality="H", integrity="H", availability="H",
        )
        # Scope changed should generally increase the score
        assert score_changed >= score_unchanged

    def test_score_range(self, calc):
        """All scores should be between 0.0 and 10.0."""
        import itertools
        av_values = ["N", "A", "L", "P"]
        ac_values = ["L", "H"]
        pr_values = ["N", "L", "H"]
        ui_values = ["N", "R"]
        s_values = ["U", "C"]
        cia_values = ["H", "L", "N"]

        for av, ac, pr, ui, s in itertools.product(
            av_values, ac_values, pr_values, ui_values, s_values
        ):
            for c in cia_values:
                score, _, _, _ = calc.calculate_base_score(
                    attack_vector=av, attack_complexity=ac,
                    privileges_required=pr, user_interaction=ui,
                    scope=s, confidentiality=c, integrity=c, availability=c,
                )
                assert 0.0 <= score <= 10.0, (
                    f"Score {score} out of range for AV={av} AC={ac} PR={pr} "
                    f"UI={ui} S={s} C={c} I={c} A={c}"
                )


class TestCVSSVectorParsing:
    """Tests for CVSS vector string parsing and building."""

    def test_parse_vector(self):
        calc = CVSSCalculator()
        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        result = calc.parse_vector(vector)
        assert result["AV"] == "N"
        assert result["AC"] == "L"
        assert result["PR"] == "N"
        assert result["C"] == "H"

    def test_build_vector_31(self):
        calc = CVSSCalculator(version="3.1")
        vector = calc.build_vector(
            attack_vector="N", attack_complexity="L",
            privileges_required="N", user_interaction="N",
            scope="U", confidentiality="H", integrity="H", availability="H",
        )
        assert vector.startswith("CVSS:3.1/")
        assert "AV:N" in vector
        assert "AC:L" in vector

    def test_build_vector_30(self):
        calc = CVSSCalculator(version="3.0")
        vector = calc.build_vector(
            attack_vector="N", attack_complexity="L",
            privileges_required="N", user_interaction="N",
            scope="U", confidentiality="H", integrity="H", availability="H",
        )
        assert vector.startswith("CVSS:3.0/")


class TestCVSSSeverityLevels:
    """Tests for severity level classification."""

    def test_severity_boundaries(self):
        calc = CVSSCalculator()
        assert calc._get_severity(9.0) == "CRITICAL"
        assert calc._get_severity(9.5) == "CRITICAL"
        assert calc._get_severity(10.0) == "CRITICAL"
        assert calc._get_severity(7.0) == "HIGH"
        assert calc._get_severity(8.9) == "HIGH"
        assert calc._get_severity(4.0) == "MEDIUM"
        assert calc._get_severity(6.9) == "MEDIUM"
        assert calc._get_severity(0.1) == "LOW"
        assert calc._get_severity(3.9) == "LOW"
        assert calc._get_severity(0.0) == "NONE"


class TestCVSSFromCrash:
    """Tests for automatic CVSS estimation from crash info."""

    def test_sigsegv_crash(self):
        calc = CVSSCalculator()
        score, severity, details = calc.calculate_from_crash(
            crash_type="sigsegv",
            has_可控=True,
            requires_auth=False,
            network_access=True,
        )
        assert score > 0
        assert severity in ("CRITICAL", "HIGH", "MEDIUM")
        assert "vector" in details

    def test_timeout_crash(self):
        calc = CVSSCalculator()
        score, severity, details = calc.calculate_from_crash(
            crash_type="timeout",
            network_access=True,
        )
        assert score > 0
        assert "vector" in details


class TestCVSSISS:
    """Tests for Impact Sub-Score calculation."""

    def test_iss_full_impact(self):
        calc = CVSSCalculator()
        iss = calc.calculate_iss(c=1.0, i=1.0, a=1.0)
        assert iss == 1.0

    def test_iss_no_impact(self):
        calc = CVSSCalculator()
        iss = calc.calculate_iss(c=0.0, i=0.0, a=0.0)
        assert iss == 0.0

    def test_iss_partial_impact(self):
        calc = CVSSCalculator()
        iss = calc.calculate_iss(c=0.5, i=0.5, a=0.5)
        assert 0.0 < iss < 1.0

    def test_iss_clamped(self):
        """ISS should be clamped to [0, 1]."""
        calc = CVSSCalculator()
        iss = calc.calculate_iss(c=1.0, i=1.0, a=1.0)
        assert 0.0 <= iss <= 1.0
