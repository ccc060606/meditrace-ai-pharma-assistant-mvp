"""Tests for sensitive info detection and masking."""
import pytest
from src.utils.sensitive import detect_sensitive_info, mask_sensitive_text


class TestDetectSensitiveInfo:
    def test_detect_phone_number(self):
        findings = detect_sensitive_info("联系电话：13812345678")
        assert len(findings) >= 1
        assert any(f["type"] == "手机号" for f in findings)

    def test_detect_email(self):
        findings = detect_sensitive_info("邮箱：test@example.com")
        assert any(f["type"] == "邮箱" for f in findings)

    def test_detect_id_card(self):
        findings = detect_sensitive_info("身份证：110101199001011234")
        assert any(f["type"] == "身份证号" for f in findings)

    def test_no_false_positive_on_normal_text(self):
        findings = detect_sensitive_info("科室：心内科，客户编号：C001，日期：2026-05-05")
        assert len(findings) == 0

    def test_detect_wechat(self):
        findings = detect_sensitive_info("微信号：test_user_123")
        assert any(f["type"] == "微信号" for f in findings)


class TestMaskSensitiveText:
    def test_mask_phone(self):
        masked = mask_sensitive_text("电话：13812345678")
        assert "****" in masked
        assert "13812345678" not in masked

    def test_mask_email(self):
        masked = mask_sensitive_text("邮箱：test@example.com")
        assert "t***@example.com" in masked
        assert "test@example.com" not in masked

    def test_normal_text_unchanged(self):
        original = "科室：心内科，客户编号：C001"
        masked = mask_sensitive_text(original)
        assert masked == original

    def test_mask_id_card(self):
        masked = mask_sensitive_text("身份证：110101199001011234")
        assert "****" in masked
        assert "110101199001011234" not in masked
