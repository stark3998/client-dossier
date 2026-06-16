// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ClientDashboard } from '@/components/ClientDashboard';
import { ClientWorkspace } from '@/components/ClientWorkspace';
import { ProjectTracker } from '@/components/insights/ProjectTracker';
import { RiskRegister } from '@/components/insights/RiskRegister';
import { InteractionTimeline } from '@/components/insights/InteractionTimeline';
import { AnalysisResults } from '@/components/insights/AnalysisResults';
import { CommunicationView } from '@/components/communication/CommunicationView';
import { ProfilePage } from '@/components/profile/ProfilePage';
import { ClientSettings } from '@/components/settings/ClientSettings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ClientDashboard />} />
        <Route path="/clients/:clientName" element={<ClientWorkspace />} />
        <Route path="/clients/:clientName/engagements" element={<ProjectTracker />} />
        <Route path="/clients/:clientName/risks" element={<RiskRegister />} />
        <Route path="/clients/:clientName/timeline" element={<InteractionTimeline />} />
        <Route path="/clients/:clientName/analysis" element={<AnalysisResults />} />
        <Route path="/clients/:clientName/communications" element={<CommunicationView />} />
        <Route path="/clients/:clientName/settings" element={<ClientSettings />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
