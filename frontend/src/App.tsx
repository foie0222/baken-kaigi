import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { RacesPage } from './pages/RacesPage';
import { RaceDetailPage } from './pages/RaceDetailPage';
import { CartPage } from './pages/CartPage';
import { ConsultationPage } from './pages/ConsultationPage';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import './styles/index.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<RacesPage />} />
          <Route path="races/:raceId" element={<RaceDetailPage />} />
          <Route path="cart" element={<CartPage />} />
          <Route path="consultation" element={<ConsultationPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
