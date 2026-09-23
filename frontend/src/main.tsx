import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {Toaster} from 'sonner';
import {DraftProvider} from './hooks/useDraft';
import App from './App';
import './index.css';

const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:3000,retry:1}}});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <DraftProvider>
          <App/>
          <Toaster position="bottom-right" richColors/>
        </DraftProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
