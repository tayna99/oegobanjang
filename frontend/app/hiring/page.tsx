import { Suspense } from "react";

import { PcRoutePage } from "@/features/pc/PcRoutePage";

export default function HiringPage() {
  return (
    <Suspense fallback={null}>
      <PcRoutePage />
    </Suspense>
  );
}
