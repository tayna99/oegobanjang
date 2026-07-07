import { useState } from 'react';
import { AppShell } from './components/AppShell';
import { TabKey } from './data';
import { TodayTasksView } from './views/TodayTasks';
import { HiringPreparationView } from './views/HiringPreparation';
import { WorkersView } from './views/Workers';
import { ContactView } from './views/Contact';
import { CasesView } from './views/Cases';
import { AdminReviewView } from './views/AdminReview';
import { JudgmentLogView } from './views/JudgmentLog';

export default function App() {
  const [active, setActive] = useState<TabKey>('today');
  return (
    <AppShell active={active} onTabChange={setActive}>
      {active === 'today' && <TodayTasksView />}
      {active === 'hiring' && <HiringPreparationView />}
      {active === 'workers' && <WorkersView />}
      {active === 'contact' && <ContactView />}
      {active === 'cases' && <CasesView />}
      {active === 'admin' && <AdminReviewView />}
      {active === 'judgment' && <JudgmentLogView />}
    </AppShell>
  );
}
