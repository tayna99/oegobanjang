"use client";

import { useState } from "react";

import { MobileAgentProcessScreen } from "./MobileAgentProcessScreen";
import { MobileApprovalDoneScreen } from "./MobileApprovalDoneScreen";
import { MobileBriefingScreen } from "./MobileBriefingScreen";
import { MobileCaseDetailScreen } from "./MobileCaseDetailScreen";
import { MobileDraftScreen } from "./MobileDraftScreen";
import { MobileShell } from "./MobileShell";
import type { MobileDemoStep } from "./demoTask";

export function MobileApprovalDemo({ embedded = false }: { embedded?: boolean }) {
  const [step, setStep] = useState<MobileDemoStep>("briefing");
  const [draftBackTarget, setDraftBackTarget] = useState<MobileDemoStep>("process");

  function go(nextStep: MobileDemoStep) {
    if (nextStep === "draft" && step !== "draft") {
      setDraftBackTarget(step);
    }
    setStep(nextStep);
  }

  return (
    <div className={embedded ? "mobile-demo-stage embedded" : "mobile-demo-stage"}>
      <MobileShell>
        {step === "briefing" ? <MobileBriefingScreen go={go} /> : null}
        {step === "detail" ? <MobileCaseDetailScreen go={go} /> : null}
        {step === "process" ? <MobileAgentProcessScreen go={go} /> : null}
        {step === "draft" ? <MobileDraftScreen backTo={draftBackTarget} go={go} /> : null}
        {step === "done" ? <MobileApprovalDoneScreen go={go} /> : null}
      </MobileShell>
    </div>
  );
}

export default MobileApprovalDemo;
