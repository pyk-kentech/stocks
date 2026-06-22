import os

import pytest

from stock_risk_mcp.kiwoom_mock_credential_boundary_engine import (
    run_kiwoom_mock_credential_boundary_evaluation,
)
from stock_risk_mcp.kiwoom_mock_credential_boundary_models import (
    KiwoomMockCredentialBoundaryConfig,
    KiwoomMockCredentialGapCategory,
)
from tests.test_kiwoom_mock_credential_boundary_models import (
    kiwoom_mock_credential_boundary_fixture_payload,
)


def _valid_config() -> KiwoomMockCredentialBoundaryConfig:
    return KiwoomMockCredentialBoundaryConfig.model_validate(kiwoom_mock_credential_boundary_fixture_payload())


def test_environment_policy_evaluation_success_path():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert result.safety_report.blocked is False
    assert "environment_policy=SYMBOLIC_ONLY" in result.safety_report.findings


def test_environment_policy_does_not_read_process_env(monkeypatch):
    monkeypatch.setenv("KIWOOM_MOCK_ONLY", "UNSAFE_RUNTIME_VALUE")
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert result.safety_report.blocked is False
    assert os.environ["KIWOOM_MOCK_ONLY"] == "UNSAFE_RUNTIME_VALUE"


def test_missing_environment_gap():
    config = _valid_config().model_copy(update={"environment": None})
    result = run_kiwoom_mock_credential_boundary_evaluation(config)
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MISSING_ENVIRONMENT in result.gap_report.gap_categories
    assert result.safety_report.blocked is True


def test_credential_ref_validation_success_path():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert "credential_ref_policy=SYMBOLIC_REFS_ONLY" in result.safety_report.findings


@pytest.mark.parametrize(
    ("field", "value", "category"),
    [
        ("reference_name", "appkey", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED),
        ("source_label", "secret_key_value", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED),
        ("source_label", "Bearer token", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED),
        ("source_label", "account_number=123456", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED),
        ("source_label", "authorization header", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED),
    ],
)
def test_credential_ref_unsafe_markers_rejected(field, value, category):
    config = _valid_config()
    ref = config.credential_refs[0].model_copy(update={field: value})
    config = config.model_copy(update={"credential_refs": [ref, *config.credential_refs[1:]]})
    result = run_kiwoom_mock_credential_boundary_evaluation(config)
    assert category in result.gap_report.gap_categories
    assert result.safety_report.blocked is True


def test_domain_policy_success_path():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert "domain_policy=MOCK_ONLY_BLOCKS_PRODUCTION" in result.safety_report.findings


def test_mock_domain_required_gap():
    config = _valid_config()
    policy = config.domain_policy.model_copy(update={"allowed_mock_rest_domain": "https://api.kiwoom.com"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"domain_policy": policy}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MOCK_DOMAIN_REQUIRED in result.gap_report.gap_categories


def test_production_domain_execution_rejected():
    config = _valid_config()
    policy = config.domain_policy.model_copy(update={"production_domain_execution_allowed": True})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"domain_policy": policy}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_PRODUCTION_DOMAIN_NOT_ALLOWED in result.gap_report.gap_categories


def test_live_prod_marker_rejected():
    config = _valid_config()
    policy = config.domain_policy.model_copy(update={"allowed_mock_websocket_domain": "prod_mode"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"domain_policy": policy}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED in result.gap_report.gap_categories


def test_opt_in_gate_disabled_by_default():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert "opt_in_gate=DISABLED_BY_DEFAULT" in result.safety_report.findings


def test_explicit_opt_in_required():
    config = _valid_config()
    gate = config.opt_in_gate.model_copy(update={"explicit_opt_in_present": True})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"opt_in_gate": gate}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_EXPLICIT_OPT_IN_REQUIRED in result.gap_report.gap_categories


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("KIWOOM_MOCK_DISABLED", "execution_mode_boundary=DRAFT_ONLY"),
        ("KIWOOM_MOCK_DRY_RUN", "execution_mode_boundary=DRY_RUN_BOUNDARY_ONLY"),
        ("KIWOOM_MOCK_OPT_IN_EXECUTION_FUTURE", "execution_mode_boundary=FUTURE_OPT_IN_MOCK_ONLY"),
    ],
)
def test_execution_mode_remains_non_executable(mode, expected):
    config = _valid_config().model_copy(update={"execution_mode": mode})
    result = run_kiwoom_mock_credential_boundary_evaluation(config)
    assert result.non_executable is True
    assert expected in result.safety_report.findings


def test_token_boundary_policy_generation():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert "token_boundary=POLICY_ONLY" in result.safety_report.findings
    assert "token_storage_policy=NOT_CREATED" in result.safety_report.findings


def test_token_issue_rejected():
    config = _valid_config()
    boundary = config.token_boundary.model_copy(update={"token_issue_attempted": True})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"token_boundary": boundary}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED in result.gap_report.gap_categories


def test_token_revoke_rejected():
    config = _valid_config()
    boundary = config.token_boundary.model_copy(update={"token_revoke_attempted": True})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"token_boundary": boundary}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED in result.gap_report.gap_categories


def test_api_mockapi_network_websocket_markers_rejected():
    config = _valid_config()
    ref = config.credential_refs[0].model_copy(update={"source_label": "mockapi_call websocket network api_call"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"credential_refs": [ref, *config.credential_refs[1:]]}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MOCKAPI_CALL_NOT_ALLOWED in result.gap_report.gap_categories
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_WEBSOCKET_NOT_ALLOWED in result.gap_report.gap_categories
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_NETWORK_CALL_NOT_ALLOWED in result.gap_report.gap_categories
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_API_CALL_NOT_ALLOWED in result.gap_report.gap_categories


def test_real_order_live_trading_markers_rejected():
    config = _valid_config()
    ref = config.credential_refs[0].model_copy(update={"source_label": "real_order live_trading"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"credential_refs": [ref, *config.credential_refs[1:]]}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_REAL_ORDER_NOT_ALLOWED in result.gap_report.gap_categories
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_TRADING_NOT_ALLOWED in result.gap_report.gap_categories


def test_account_mutation_marker_rejected():
    config = _valid_config()
    ref = config.credential_refs[0].model_copy(update={"source_label": "account_mutation"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"credential_refs": [ref, *config.credential_refs[1:]]}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ACCOUNT_MUTATION_NOT_ALLOWED in result.gap_report.gap_categories


def test_safety_report_generation():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert result.safety_report.safety_report_id == "KIWOOM-CREDENTIAL-SAFETY-REPORT-1"
    assert result.safety_report.blocked is False


def test_gap_report_generation():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert result.gap_report.gap_status == "NO_GAPS"
    assert result.gap_report.blocking_gap_count == 0


def test_audit_record_generation():
    result = run_kiwoom_mock_credential_boundary_evaluation(_valid_config())
    assert len(result.audit_records) == 1
    assert result.audit_records[0].audit_record_id.endswith("AUDIT-EVALUATED")


def test_cloud_llm_local_llm_runtime_markers_rejected():
    config = _valid_config()
    ref = config.credential_refs[0].model_copy(update={"source_label": "gemini ollama"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"credential_refs": [ref, *config.credential_refs[1:]]}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED in result.gap_report.gap_categories
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED in result.gap_report.gap_categories


def test_parquet_rejected():
    config = _valid_config()
    ref = config.credential_refs[0].model_copy(update={"source_label": "parquet export"})
    result = run_kiwoom_mock_credential_boundary_evaluation(config.model_copy(update={"credential_refs": [ref, *config.credential_refs[1:]]}))
    assert KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_PARQUET_NOT_ALLOWED in result.gap_report.gap_categories
