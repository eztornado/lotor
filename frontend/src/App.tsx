import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Container } from '@mantine/core'
import Header from './components/Header'
import HomePage from './components/HomePage'
import PredictionPage from './components/PredictionPage'
import StatisticsPage from './components/StatisticsPage'
import HistoryPage from './components/HistoryPage'
import WeeklyCombinationsPage from './components/WeeklyCombinationsPage'

function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Header />
        <Container size="xl" style={{ flex: 1, padding: '2rem' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/prediction" element={<PredictionPage />} />
            <Route path="/statistics" element={<StatisticsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/weekly-combinations" element={<WeeklyCombinationsPage />} />
          </Routes>
        </Container>
      </div>
    </Router>
  )
}

export default App
