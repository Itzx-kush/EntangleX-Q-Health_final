import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {DraftProvider} from './hooks/ExperimentDraft';
import App from './App';
import './styles.css';
import './styles/reference-product-composition.css';
import './styles/aether-visual-system.css';
import {AetherVisualLayer} from './components/AetherVisualLayer';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <DraftProvider>
        <AetherVisualLayer>
          <App />
        </AetherVisualLayer>
      </DraftProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
