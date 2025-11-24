import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import './App.css';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import WalletList from './pages/WalletList';
import WalletDetail from './pages/WalletDetail';
import Leaderboards from './pages/Leaderboards';
import Operations from './pages/Operations';
import Settings from './pages/Settings';
import AdminPanel from './pages/Admin';
import Login from './pages/Login';
import WalletImport from './pages/WalletImport';

function App() {
  const location = useLocation();
  const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;

  if (location.pathname === '/login') {
    return <Login />;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="content-area">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/wallets" element={<WalletList />} />
            <Route path="/wallets/:address" element={<WalletDetail />} />
            <Route path="/wallets/import" element={<WalletImport />} />
            <Route path="/leaderboards" element={<Leaderboards />} />
            <Route path="/operations" element={<Operations />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
