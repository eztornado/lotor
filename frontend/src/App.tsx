import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom'
import { Container, Text } from '@mantine/core'
import Header from './components/layout/Header'
import HomePage from './pages/HomePage'
import GordoGeneratorPage from './pages/gordo/GordoGeneratorPage'
import PredictionPage from './pages/gordo/PredictionPage'
import StatisticsPage from './pages/gordo/StatisticsPage'
import HistoryPage from './pages/gordo/HistoryPage'
import WeeklyCombinationsPage from './pages/gordo/WeeklyCombinationsPage'
import BonolotoPage from './pages/bonoloto/BonolotoPage'
import BonolotoStatsPage from './pages/bonoloto/BonolotoStatsPage'
import BonolotoHistoryPage from './pages/bonoloto/BonolotoHistoryPage'
import { LEGACY_REDIRECTS } from './games'

function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Header />
        <Container size="xl" style={{ flex: 1, padding: '2rem' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />

            {/* El Gordo de la Primitiva */}
            <Route path="/gordo" element={<GordoGeneratorPage />} />
            <Route path="/gordo/prediction" element={<PredictionPage />} />
            <Route path="/gordo/statistics" element={<StatisticsPage />} />
            <Route path="/gordo/history" element={<HistoryPage />} />
            <Route path="/gordo/weekly-combinations" element={<WeeklyCombinationsPage />} />

            {/* Bonoloto */}
            <Route path="/bonoloto" element={<BonolotoPage />} />
            <Route path="/bonoloto/estadisticas" element={<BonolotoStatsPage />} />
            <Route path="/bonoloto/historial" element={<BonolotoHistoryPage />} />

            {/* Rutas heredadas */}
            {LEGACY_REDIRECTS.map((redirect) => (
              <Route
                key={redirect.from}
                path={redirect.from}
                element={<Navigate to={redirect.to} replace />}
              />
            ))}

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Container>
        <footer style={{ borderTop: '1px solid #373A40', padding: '1rem 2rem' }}>
          <Text size="xs" c="dimmed" ta="center">
            LoTor · Herramienta educativa. La lotería es un juego de azar; juega de forma responsable.
          </Text>
        </footer>
      </div>
    </Router>
  )
}

export default App
