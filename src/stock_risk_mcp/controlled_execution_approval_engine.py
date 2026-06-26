from __future__ import annotations

from datetime import timedelta

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionApprovalPacket,
    ControlledExecutionManualApproval,
    ControlledExecutionOrderDraft,
    ControlledExecutionPipelineInput,
)


def _simple_hash(*parts: object) -> str:
    text = "|".join(str(part) for part in parts)
    return f"HASH-{abs(hash(text)) % 10_000_000:07d}"


def build_controlled_execution_approval_packet(
    pipeline_input: ControlledExecutionPipelineInput,
    order_draft: ControlledExecutionOrderDraft,
    *,
    kill_switch_summary: dict[str, object],
    duplicate_summary: dict[str, object],
    risk_summary: dict[str, object],
    reconciliation_summary: dict[str, object],
    adapter_summary: dict[str, object],
) -> ControlledExecutionApprovalPacket:
    packet_hash = _simple_hash(order_draft.draft_hash, pipeline_input.pipeline_id, "PACKET")
    return ControlledExecutionApprovalPacket(
        packet_id=f"{pipeline_input.pipeline_id}-APPROVAL-PACKET",
        order_draft_hash=order_draft.draft_hash,
        packet_hash=packet_hash,
        expiry_at=pipeline_input.requested_at + timedelta(minutes=30),
        single_use_approval_ref=f"approval-ref-{pipeline_input.pipeline_id.lower()}",
        risk_summary=risk_summary,
        reconciliation_summary=reconciliation_summary,
        kill_switch_summary=kill_switch_summary,
        duplicate_guard_summary=duplicate_summary,
        adapter_summary=adapter_summary,
        preview_summary={
            "instrument_id": order_draft.instrument_id,
            "side": order_draft.side.value,
            "quantity": order_draft.quantity,
            "blocked_live_submit": True,
        },
    )


def validate_controlled_execution_manual_approval(
    pipeline_input: ControlledExecutionPipelineInput,
    order_draft: ControlledExecutionOrderDraft,
    approval_packet: ControlledExecutionApprovalPacket,
) -> ControlledExecutionManualApproval:
    fixture = pipeline_input.manual_approval_fixture or {}
    approval_ref = str(fixture.get("approval_ref", f"fake-approval-{pipeline_input.pipeline_id.lower()}"))
    approval_ref_hash = _simple_hash(approval_ref)
    already_used = bool(fixture.get("already_used", False)) or pipeline_input.approval_reuse_detected
    draft_match = str(fixture.get("order_draft_hash", order_draft.draft_hash)).upper() == order_draft.draft_hash
    packet_match = str(fixture.get("packet_hash", approval_packet.packet_hash)).upper() == approval_packet.packet_hash
    expiry_at = fixture.get("expiry_at", approval_packet.expiry_at)
    valid = draft_match and packet_match and not already_used and approval_packet.expiry_at >= pipeline_input.requested_at
    reason_codes: list[str] = []
    if not draft_match:
        reason_codes.append("DRAFT_HASH_MISMATCH")
    if not packet_match:
        reason_codes.append("PACKET_HASH_MISMATCH")
    if already_used:
        reason_codes.append("APPROVAL_REUSE_DETECTED")
    if approval_packet.expiry_at < pipeline_input.requested_at:
        reason_codes.append("APPROVAL_EXPIRED")
    return ControlledExecutionManualApproval(
        approval_id=f"{pipeline_input.pipeline_id}-MANUAL-APPROVAL",
        approval_ref=approval_ref,
        approval_ref_hash=approval_ref_hash,
        order_draft_hash=order_draft.draft_hash,
        packet_hash=approval_packet.packet_hash,
        approved_at=pipeline_input.requested_at,
        expiry_at=expiry_at,
        single_use=True,
        already_used=already_used,
        valid=valid,
        reason_codes=reason_codes or ["APPROVAL_VALID"],
    )
