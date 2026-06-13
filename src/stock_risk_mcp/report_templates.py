DISCLAIMER_EN = "This report is for paper trading and research support only. It is not financial advice."
DISCLAIMER_KO = "이 보고서는 모의 투자와 리서치 지원용이며 투자 조언이 아닙니다."


def labels(language: str) -> dict[str, str]:
    if language == "ko":
        return {
            "key_metrics": "핵심 지표", "main_findings": "주요 분석",
            "risks": "위험 및 경고", "next_actions": "다음 확인 사항", "disclaimer": "면책",
        }
    return {
        "key_metrics": "Key Metrics", "main_findings": "Main Findings",
        "risks": "Risks / Warnings", "next_actions": "Next Actions", "disclaimer": "Disclaimer",
    }


def disclaimer(language: str) -> str:
    return DISCLAIMER_KO if language == "ko" else DISCLAIMER_EN


def suggested_questions(language: str) -> list[str]:
    if language == "ko":
        return ["이 결과의 주요 근거를 설명해 주세요.", "모의 투자 전 확인할 위험을 정리해 주세요."]
    return ["Explain the main evidence behind this result.", "List the top risks before paper trading."]


def localized_report_text(title: str, source_id: str, language: str) -> tuple[str, str, str]:
    if language != "ko":
        return title, f"Deterministic research summary for {source_id}.", "Stored evidence metrics."
    titles = {
        "Pipeline Summary Report": "파이프라인 요약 보고서",
        "Candidate Scan Report": "후보 스캔 보고서",
        "Basket Plan Report": "바스켓 계획 보고서",
        "Policy Evaluation Report": "정책 평가 보고서",
    }
    return titles[title], f"{source_id}에 대한 결정론적 리서치 요약입니다.", "저장된 근거 지표입니다."
