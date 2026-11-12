import React from 'react';
import {
  Inbox,
  AlertCircle,
  Clock,
  CheckCircle2,
  Flame,
} from 'lucide-react';

export default function StatsCards({ stats }) {
  const cards = [
    {
      label: 'Total Tickets',
      value: stats?.total_tickets ?? 0,
      icon: Inbox,
      bg: '#eff6ff',
      color: '#2563eb',
    },
    {
      label: 'Open Tickets',
      value: stats?.open_tickets ?? 0,
      icon: AlertCircle,
      bg: '#f0f9ff',
      color: '#0284c7',
    },
    {
      label: 'Pending Tickets',
      value: stats?.pending_tickets ?? 0,
      icon: Clock,
      bg: '#fffbeb',
      color: '#d97706',
    },
    {
      label: 'Resolved Tickets',
      value: stats?.resolved_tickets ?? 0,
      icon: CheckCircle2,
      bg: '#ecfdf5',
      color: '#059669',
    },
    {
      label: 'P1 Urgent (High/Crit)',
      value: stats?.high_priority_tickets ?? 0,
      icon: Flame,
      bg: '#fef2f2',
      color: '#dc2626',
    },
  ];

  return (
    <div className="stats-container">
      {cards.map((card, i) => {
        const IconComponent = card.icon;
        return (
          <div key={i} className="stat-card">
            <div className="stat-label-wrap">
              <span className="stat-label">{card.label}</span>
              <div
                className="stat-icon"
                style={{ backgroundColor: card.bg, color: card.color }}
              >
                <IconComponent size={16} />
              </div>
            </div>
            <div className="stat-value">{card.value}</div>
          </div>
        );
      })}
    </div>
  );
}

