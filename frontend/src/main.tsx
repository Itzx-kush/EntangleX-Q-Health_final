import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {Toaster} from 'sonner';
import {DraftProvider} from './hooks/useDraft';
import {VerifiedDemoProvider} from './hooks/useVerifiedDemo';
import {AuthProvider} from './auth/AuthProvider';
import {AuthGate} from './auth/AuthGate';
import {GuestMigrationProvider} from './auth/GuestMigrationProvider';
import './index.css';
import './styles/foundation.css';

const App = React.lazy(() => import('./App'));

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
                  <React.Suspense fallback={<main role="status" className="access-loading">Opening research workspace…</main>}><App/></React.Suspense>
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
