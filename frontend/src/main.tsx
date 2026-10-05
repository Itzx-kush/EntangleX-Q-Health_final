import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {Toaster} from 'sonner';
import {DraftProvider} from './hooks/useDraft';
import {VerifiedDemoProvider} from './hooks/useVerifiedDemo';
import App from './App';
import {AuthProvider} from './auth/AuthProvider';
import {AuthGate} from './auth/AuthGate';
import {GuestMigrationProvider} from './auth/GuestMigrationProvider';
import './index.css';
import './tokens.css';
import './styles/reference-theme.css';
import './styles/logo-system.css';
import './styles/public-experience.css';
import './styles/outer-reactbits.css';
import './sidebar-layout-fix.css';
import './responsive-adaptation.css';
import './styles/tremor.css';
import './styles/tremor-v2.css';
import './styles/product-polish.css';
import './styles/account-workspace.css';
import './styles/research-history.css';
import './styles/guest-migration.css';
import './styles/workspace-premium.css';
import './styles/quantum-lab.css';
import './styles/layer3-final-polish.css';
import './styles/dark-theme-consistency.css';

const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:3000,retry:1}}});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <GuestMigrationProvider>
            <AuthGate>
              <DraftProvider>
                <VerifiedDemoProvider>
                  <App/>
                  <Toaster position="bottom-right" richColors/>
                </VerifiedDemoProvider>
              </DraftProvider>
            </AuthGate>
          </GuestMigrationProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
