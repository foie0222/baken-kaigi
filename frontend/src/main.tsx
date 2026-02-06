import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { configureAmplify } from './config/amplify';
import App from './App.tsx'

configureAmplify();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
