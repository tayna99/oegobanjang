import { DailyBriefingPanel } from "./DailyBriefingPanel";
import { PcFrame } from "../pc/PcShell";

export function DashboardShell() {
  return (
    <PcFrame showFab={false}>
      <DailyBriefingPanel />
    </PcFrame>
  );
}
