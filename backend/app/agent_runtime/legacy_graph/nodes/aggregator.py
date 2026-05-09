"""Aggregator: 여러 agent 결과와 RAG/tool 근거를 하나의 case output으로 합칩니다."""
from __future__ import annotations

from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event, log_event
from app.agent_runtime.schemas import EventType, ForeignHiringState, ToolStatus


def aggregator_node(state: ForeignHiringState) -> ForeignHiringState:
  agent_names = _dedupe(
      str(result.get("agent"))
      for result in state.agent_results
      if result.get("agent")
  )
  summaries = [
      {
          "agent": str(result.get("agent", "")),
          "summary": str(result.get("summary", "")),
          "status": str(result.get("status", "completed")),
      }
      for result in state.agent_results
      if result.get("summary")
  ]

  key_findings = _collect_key_findings(state.agent_results)

  risk_flags = _dedupe(
      [
          *state.risk_flags,
          *[
              str(flag)
              for result in state.agent_results
              for flag in result.get("risk_flags", [])
          ],
          *[
              str(flag)
              for tool_result in state.tool_results
              for flag in tool_result.risk_flags
          ],
      ]
  )
  approval_required = bool(
      state.plan.requires_approval
      or any(bool(result.get("approval_required")) for result in state.agent_results)
      or any(
          tool_result.approval_required or tool_result.status == ToolStatus.NEEDS_APPROVAL
          for tool_result in state.tool_results
      )
  )
  citation_ids = _dedupe(
      [
          *[
              str(context.get("source_id"))
              for context in state.rag_contexts
              if context.get("source_id")
          ],
          *[
              citation.source_id
              for tool_result in state.tool_results
              for citation in tool_result.citations
          ],
      ]
  )

  risk_level = _risk_level(risk_flags=risk_flags, approval_required=approval_required)
  risk_reasons = _collect_risk_reasons(risk_flags, risk_level, approval_required)
  approval_reasons = _collect_approval_reasons(state.agent_results, state.tool_results)

  handoff_ready, handoff_blockers = _handoff_status(agent_names, key_findings, approval_required)

  state.aggregated_output = {
      "request_id": state.request_id,
      "agent_count": len(agent_names),
      "agents": agent_names,
      "summaries": summaries,
      "key_findings": key_findings,
      "risk_flags": risk_flags,
      "risk_level": risk_level,
      "risk_reasons": risk_reasons,
      "approval_required": approval_required,
      "approval_reasons": approval_reasons,
      "citation_ids": citation_ids,
      "handoff_ready": handoff_ready,
      "handoff_blockers": handoff_blockers,
      "tool_count": len(state.tool_results),
      "rag_context_count": len(state.rag_contexts),
  }

  state.key_findings = key_findings

  if risk_flags:
      event_summary = f"Aggregator risk 분류: {risk_level}, {len(risk_flags)}건"
      if risk_reasons:
          event_summary += f" ({risk_reasons[0]})"
      event = make_event(
          event_type=EventType.RISK_FLAGGED,
          request_id=state.request_id,
          summary=event_summary,
          step_name="aggregator",
          citation_ids=citation_ids,
          risk_level=risk_level,
      )
  else:
      event = make_event(
          event_type=EventType.TOOL_EXECUTED,
          request_id=state.request_id,
          summary=f"Aggregator 실행. agent {len(agent_names)}개 결과 통합",
          step_name="aggregator",
          citation_ids=citation_ids,
          risk_level=risk_level,
      )
  return log_event(state, event)


def _risk_level(*, risk_flags: list[str], approval_required: bool) -> str:
  joined = " ".join(risk_flags)

  # HIGH 조건
  high_keywords = ("D-30", "D-7", "D-14", "만료 임박", "기한 초과", "제출 기한 초과", "HIGH")
  high_external = ("자동 발송", "정부 제출", "전문가 전달", "외부 export")
  high_guardrail = ("guardrail", "차단", "BLOCKED", "금지됨")

  if any(keyword in joined for keyword in high_keywords):
      return "HIGH"
  if approval_required and any(keyword in joined for keyword in high_external):
      return "HIGH"
  if any(keyword in joined for keyword in high_guardrail):
      return "HIGH"

  # MEDIUM 조건
  medium_keywords = ("누락", "검수", "상태 후보", "공식 근거 부족")
  if risk_flags or approval_required:
      if any(keyword in joined for keyword in medium_keywords) or approval_required:
          return "MEDIUM"

  return "LOW"


def _collect_key_findings(agent_results: list[dict]) -> list[dict]:
  findings = []
  for result in agent_results:
      if "key_findings" in result and result["key_findings"]:
          for finding in result["key_findings"]:
              if isinstance(finding, dict):
                  findings.append(finding)
  return findings


def _collect_approval_reasons(agent_results: list[dict], tool_results: list) -> list[str]:
  reasons = []
  allowed_reasons = {
      "worker_message_draft",
      "worker_message_send",
      "expert_handoff_package_draft",
      "expert_handoff_transfer",
      "external_export",
      "government_submission",
      "case_completion",
      "status_update_apply",
      "translation_review",
      "legal_or_visa_judgment_blocked",
  }

  for result in agent_results:
      if "approval_reasons" in result:
          for reason in result.get("approval_reasons", []):
              if reason in allowed_reasons and reason not in reasons:
                  reasons.append(reason)

  for tool_result in tool_results:
      if hasattr(tool_result, "approval_required") and tool_result.approval_required:
          if "tool_execution_approval" not in reasons:
              reasons.append("tool_execution_approval")

  return reasons


def _collect_risk_reasons(risk_flags: list[str], risk_level: str, approval_required: bool) -> list[str]:
  reasons = []

  if risk_level == "HIGH":
      if any("D-" in flag for flag in risk_flags):
          reasons.append("체류만료 또는 기한이 30일 이내입니다.")
      if any("누락" in flag for flag in risk_flags):
          reasons.append("필수 서류가 누락되었습니다.")
      if any("차단" in flag or "guardrail" in flag for flag in risk_flags):
          reasons.append("안전 규칙 위반으로 차단되었습니다.")
      if approval_required:
          reasons.append("외부 실행 전 담당자 승인이 필요합니다.")

  elif risk_level == "MEDIUM":
      if any("누락" in flag for flag in risk_flags):
          reasons.append("필수 서류 누락 또는 상태 불일치가 있습니다.")
      if approval_required:
          reasons.append("운영 검토가 필요합니다.")
      if any("검수" in flag for flag in risk_flags):
          reasons.append("번역 또는 근로자 답변 검토가 필요합니다.")

  if not reasons:
      reasons.append("정보 조회 완료.")

  return reasons


def _handoff_status(agent_names: list[str], key_findings: list[dict], approval_required: bool) -> tuple[bool, list[str]]:
  blockers = []

  for finding in key_findings:
      finding_type = finding.get("type", "").lower()
      if finding_type == "missing_info":
          blockers.append(finding.get("message", "미분류된 누락 정보"))

  handoff_ready = bool(agent_names and not blockers and approval_required)

  return handoff_ready, blockers


def _dedupe(values) -> list[str]:
  deduped: list[str] = []
  seen: set[str] = set()
  for value in values:
      text = str(value)
      if not text or text in seen:
          continue
      seen.add(text)
      deduped.append(text)
  return deduped
