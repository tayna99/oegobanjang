"use client";

import { useState } from "react";

import { MobileAgentProcessScreen } from "./MobileAgentProcessScreen";
import { MobileApprovalDoneScreen } from "./MobileApprovalDoneScreen";
import { MobileBriefingScreen } from "./MobileBriefingScreen";
import { MobileCaseDetailScreen } from "./MobileCaseDetailScreen";
import { MobileDraftScreen } from "./MobileDraftScreen";
import { MobileShell } from "./MobileShell";
import type { ApprovalActionResult, ExternalDeliveryJob, NextAction } from "../../types/dailyBriefing";
import type { MobileDemoStep } from "./demoTask";

type MobileApprovalDemoProps = {
  action?: NextAction | null;
  approvalResult?: ApprovalActionResult | null;
  deliveryJob?: ExternalDeliveryJob | null;
  embedded?: boolean;
  onApprove?: (action: NextAction) => Promise<ApprovalActionResult | null>;
  onCreateDeliveryJob?: (action: NextAction) => Promise<ExternalDeliveryJob | null>;
  onRequestRevision?: (action: NextAction, reason: string) => Promise<ApprovalActionResult | null>;
};

export function MobileApprovalDemo({
  action = null,
  approvalResult: externalApprovalResult = null,
  deliveryJob: externalDeliveryJob = null,
  embedded = false,
  onApprove,
  onCreateDeliveryJob,
  onRequestRevision,
}: MobileApprovalDemoProps) {
  const [step, setStep] = useState<MobileDemoStep>("briefing");
  const [draftBackTarget, setDraftBackTarget] = useState<MobileDemoStep>("process");
  const [busyAction, setBusyAction] = useState<"approve" | "revision" | null>(null);
  const [approvalResult, setApprovalResult] = useState<ApprovalActionResult | null>(externalApprovalResult);
  const [deliveryJob, setDeliveryJob] = useState<ExternalDeliveryJob | null>(externalDeliveryJob);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

  function go(nextStep: MobileDemoStep) {
    if (nextStep === "draft" && step !== "draft") {
      setDraftBackTarget(step);
    }
    setStep(nextStep);
  }

  async function approveSelectedAction() {
    if (!action || !onApprove) {
      setReviewMessage("데모 모드로 승인 완료 화면을 표시합니다.");
      go("done");
      return;
    }
    setBusyAction("approve");
    setReviewMessage(null);
    try {
      const result = await onApprove(action);
      if (!result) {
        setReviewMessage("승인 API 응답을 받지 못했습니다. PC 오류 영역을 확인해 주세요.");
        return;
      }
      setApprovalResult(result);
      if (onCreateDeliveryJob) {
        const job = await onCreateDeliveryJob(action);
        if (job) {
          setDeliveryJob(job);
        }
      }
      go("done");
    } finally {
      setBusyAction(null);
    }
  }

  async function requestSelectedRevision() {
    if (!action || !onRequestRevision) {
      setReviewMessage("수정 요청이 기록된 데모 상태입니다.");
      return;
    }
    setBusyAction("revision");
    try {
      const result = await onRequestRevision(
        action,
        "대표 모바일 화면에서 문구 수정을 요청했습니다.",
      );
      setReviewMessage(
        result
          ? `수정 요청이 기록되었습니다. Evidence ${result.evidence_event_id}`
          : "수정 요청 API 응답을 받지 못했습니다. PC 오류 영역을 확인해 주세요.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className={embedded ? "mobile-demo-stage embedded" : "mobile-demo-stage"}>
      <MobileShell>
        {step === "briefing" ? (
          <MobileBriefingScreen
            busyAction={busyAction}
            go={go}
            onApprove={approveSelectedAction}
            onRequestRevision={requestSelectedRevision}
            reviewMessage={reviewMessage}
          />
        ) : null}
        {step === "detail" ? <MobileCaseDetailScreen go={go} /> : null}
        {step === "process" ? <MobileAgentProcessScreen go={go} /> : null}
        {step === "draft" ? (
          <MobileDraftScreen
            backTo={draftBackTarget}
            busyAction={busyAction}
            go={go}
            onApprove={approveSelectedAction}
            onRequestRevision={requestSelectedRevision}
            reviewMessage={reviewMessage}
          />
        ) : null}
        {step === "done" ? (
          <MobileApprovalDoneScreen
            approvalResult={approvalResult}
            deliveryJob={deliveryJob}
            go={go}
          />
        ) : null}
      </MobileShell>
    </div>
  );
}

export default MobileApprovalDemo;
