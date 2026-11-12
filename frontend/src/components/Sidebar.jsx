import React from 'react';
import {
  LayoutDashboard,
  Inbox,
  Clock,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  Bot,
  PlusCircle,
  Sparkles,
  Sun,
  Moon,
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  stats,
  aiStatus,
  onOpenNewTicketModal,
  isDarkMode,
  toggleTheme,
}) {
  const navItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      count: stats?.total_tickets ?? 0,
    },
    {
      id: 'all',
      label: 'All Tickets',
      icon: Inbox,
      count: stats?.total_tickets ?? 0,
    },
    {
      id: 'open',
      label: 'Open Tickets',
      icon: AlertCircle,
      count: stats?.open_tickets ?? 0,
    },
    {
      id: 'pending',
      label: 'Pending Tickets',
      icon: Clock,
      count: stats?.pending_tickets ?? 0,
    },
    {
      id: 'resolved',
      label: 'Resolved Tickets',
      icon: CheckCircle2,
      count: stats?.resolved_tickets ?? 0,
    },
    {
      id: 'reports',
      label: 'Reports',
      icon: BarChart3,
      count: null,
    },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">
          <Bot size={22} />
        </div>
        <div>
          <h2 className="app-title">Copilot Support</h2>
          <span className="app-subtitle">AI Triage & Triage</span>
        </div>
      </div>

      <div style={{ padding: '16px 14px 4px' }}>
        <button
          className="btn btn-primary"
          style={{ width: '100%', justifyContent: 'center' }}
          onClick={onOpenNewTicketModal}
        >
          <PlusCircle size={16} />
          <span>New Ticket</span>
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const IconComponent = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <div className="nav-item-left">
                <IconComponent size={18} />
                <span>{item.label}</span>
              </div>
              {item.count !== null && (
                <span className="nav-count">{item.count}</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {aiStatus?.status === 'online' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', fontWeight: 600 }}>
            <Sparkles size={14} />
            <span>Groq AI Online</span>
          </div>
        ) : aiStatus?.status === 'missing_key' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#dc2626', fontWeight: 600 }}>
            <AlertCircle size={14} />
            <span>API Key Missing</span>
          </div>
        ) : aiStatus?.status === 'auth_error' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#dc2626', fontWeight: 600 }}>
            <AlertCircle size={14} />
            <span>Invalid API Key</span>
          </div>
        ) : aiStatus?.status === 'rate_limited' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#d97706', fontWeight: 600 }}>
            <Clock size={14} />
            <span>AI Rate Limited</span>
          </div>
        ) : aiStatus?.status ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#dc2626', fontWeight: 600 }}>
            <AlertCircle size={14} />
            <span>AI Service Error</span>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontWeight: 600 }}>
            <Clock size={14} />
            <span>Checking AI...</span>
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
          <span>{isDarkMode ? '🌙 Dark Mode' : '☀️ Light Mode'}</span>
          <button
            onClick={toggleTheme}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              padding: '2px',
            }}
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {isDarkMode ? <Sun size={15} style={{ color: '#fbbf24' }} /> : <Moon size={15} />}
          </button>
        </div>
      </div>
    </aside>
  );
}

