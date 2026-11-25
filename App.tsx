import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from './hooks/useAuth';
import { AppLayout } from './layouts/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { CommandCenterPage } from './pages/CommandCenterPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AiIntelligencePage } from './pages/AiIntelligencePage';
import { RiskObservatoryPage } from './pages/RiskObservatoryPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { ReportsStudioPage } from './pages/ReportsStudioPage';
import { ActionCenterPage } from './pages/ActionCenterPage';
import { KnowledgeHubPage } from './pages/KnowledgeHubPage';
import { CopilotPage } from './pages/CopilotPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient();

function AppRoutes() {
  const { user, loading, login, logout } = useAuth();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-navy-950 text-slate-400">Initializing EnterpriseIQ...</div>;
  }

  if (!user) {
    return <LoginPage onLogin={login} />;
  }

  return (
    <Routes>
      <Route element={<AppLayout user={user} onLogout={logout} />}>
        <Route path="/" element={<CommandCenterPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/ai-intelligence" element={<AiIntelligencePage />} />
        <Route path="/risks" element={<RiskObservatoryPage />} />
        <Route path="/departments" element={<DepartmentsPage />} />
        <Route path="/reports" element={<ReportsStudioPage />} />
        <Route path="/actions" element={<ActionCenterPage />} />
        <Route path="/knowledge" element={<KnowledgeHubPage />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="/settings" element={<SettingsPage user={user} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
