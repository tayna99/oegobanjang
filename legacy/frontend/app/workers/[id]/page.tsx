import { PcShell } from "../../../features/pc/PcShell";
import { WorkerDetailPage } from "../../../features/pc/WorkerDetailPage";

export default async function WorkerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <PcShell activeViewOverride="workers">
      <WorkerDetailPage workerId={id} />
    </PcShell>
  );
}
