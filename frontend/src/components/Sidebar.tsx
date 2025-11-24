import { NavLink } from 'react-router-dom';

const links = [
  { path: '/dashboard', label: '仪表盘' },
  { path: '/wallets', label: '钱包列表' },
  { path: '/wallets/import', label: '钱包导入' },
  { path: '/leaderboards', label: '榜单' },
  { path: '/operations', label: '运营监控' },
  { path: '/settings', label: '偏好设置' },
  { path: '/admin', label: '后台配置' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">Wallet Analytics</div>
      <nav>
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
