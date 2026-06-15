from pathlib import Path

def test_technical_modules_have_no_forbidden_dependencies_or_cvd():
    root=Path(__file__).resolve().parents[1]/"src"/"stock_risk_mcp"
    names=("technical_evidence_models.py","technical_evidence_fixture.py","macd_features.py","rsi_features.py","ma_trend_features.py","hma_features.py","atr_features.py","volume_features.py","divergence_features.py","setup_evidence_scoring.py","technical_evidence_service.py")
    forbidden=("repository","sqlite","provider","realtime","broker","kiwoom","account_read","order_intent","strategydecision","credential","token_provider","urlopen","requests","httpx","cvd")
    for name in names:
        text=(root/name).read_text(encoding="utf-8").lower()
        assert all(item not in text for item in forbidden)
