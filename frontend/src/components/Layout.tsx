import { NavLink } from 'react-router-dom';
import './Layout.css';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Law Firm ERP</h1>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            Dashboard
          </NavLink>
          <NavLink to="/matters" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            Matters
          </NavLink>
          <NavLink to="/tasks" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            Tasks
          </NavLink>
          <NavLink to="/case-brain" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            Case Brain
          </NavLink>
          <NavLink to="/review-queue" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            Review Queue
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
