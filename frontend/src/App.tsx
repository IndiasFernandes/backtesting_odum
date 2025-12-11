import { BrowserRouter, Routes, Route } from 'react-router-dom'

// Configure React Router future flags to suppress warnings
const routerConfig = {
  future: {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  },
}
import BacktestComparisonPage from './pages/BacktestComparisonPage'
import BacktestRunnerPage from './pages/BacktestRunnerPage'
import DefinitionsPage from './pages/DefinitionsPage'
import AlgorithmManagerPage from './pages/AlgorithmManagerPage'
import Layout from './components/Layout'

function App() {
  return (
    <BrowserRouter future={routerConfig.future}>
      <Layout>
        <Routes>
          <Route path="/" element={<BacktestComparisonPage />} />
          <Route path="/run" element={<BacktestRunnerPage />} />
          <Route path="/definitions" element={<DefinitionsPage />} />
          <Route path="/algorithms" element={<AlgorithmManagerPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App

