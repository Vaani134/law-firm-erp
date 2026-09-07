import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { ReviewQueue } from './pages/ReviewQueue';
import { Matters } from './pages/Matters';
import { MatterCreate } from './pages/MatterCreate';
import { MatterDetail } from './pages/MatterDetail';
import { EmailDetail } from './pages/EmailDetail';
import { CaseBrain } from './pages/CaseBrain';

export function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/review-queue" element={<ReviewQueue />} />
          <Route path="/matters" element={<Matters />} />
          <Route path="/matters/new" element={<MatterCreate />} />
          <Route path="/matters/:matterKey" element={<MatterDetail />} />
          <Route path="/email/:emailId" element={<EmailDetail />} />
          <Route path="/case-brain" element={<CaseBrain />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
