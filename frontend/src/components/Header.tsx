import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();
  const pageTitle = location.pathname.startsWith('/wallets')
    ? '钱包管理'
    : '仪表盘';

  return (
    <header className="app-header">
      <div>
        <h1>{pageTitle}</h1>
        <p className="subtitle">Hyperliquid 钱包表现洞察</p>
      </div>
      <div className="header-actions">
        <Link to="/wallets" className="btn secondary">
          钱包列表
        </Link>
        <Link to="/dashboard" className="btn primary">
          仪表盘
        </Link>
        <button
          className="btn secondary"
          onClick={() => {
            localStorage.removeItem('authToken');
            window.location.href = '/login';
          }}
        >
          退出
        </button>
      </div>
    </header>
  );
}
