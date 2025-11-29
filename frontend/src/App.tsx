import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import './App.css';
import './index.css';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import WalletList from './pages/WalletList';
import WalletDetail from './pages/WalletDetail';
import Leaderboards from './pages/Leaderboards';
import LeaderboardDetail from './pages/LeaderboardDetail';
import Operations from './pages/Operations';
import Settings from './pages/Settings';
import AdminPanel from './pages/Admin';
import Login from './pages/Login';
import WalletImport from './pages/WalletImport';

function ProtectedLayout() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="content-area">
        <Header />
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/wallets" element={<WalletList />} />
          <Route path="/wallets/:address" element={<WalletDetail />} />
          <Route path="/wallets/import" element={<WalletImport />} />
          <Route path="/leaderboards" element={<Leaderboards />} />
          <Route path="/leaderboards/:id" element={<LeaderboardDetail />} />
          <Route path="/operations" element={<Operations />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
      <div id="toast-root" className="toast-container" />
    </>
  );
}

export default App;
