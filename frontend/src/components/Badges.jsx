import React from 'react';
import {
  Package,
  RotateCcw,
  Wrench,
  HelpCircle,
  AlertTriangle,
  Smile,
  Meh,
  Frown,
  Flame,
  CheckCircle2,
  ShieldAlert,
} from 'lucide-react';

export function mapPriorityToUrgency(priority) {
  const prio = (priority || 'medium').toLowerCase().trim();
  if (prio === 'critical' || prio === 'p1') {
    return { tier: 'P1', originalLabel: 'Critical / P1', cssClass: 'badge-priority-p1' };
  }
  if (prio === 'high') {
    return { tier: 'P1', originalLabel: 'High', cssClass: 'badge-priority-p1' };
  }
  if (prio === 'medium' || prio === 'p2') {
    return { tier: 'P2', originalLabel: 'Medium / P2', cssClass: 'badge-priority-p2' };
  }
  if (prio === 'low' || prio === 'p3') {
    return { tier: 'P3', originalLabel: 'Low / P3', cssClass: 'badge-priority-p3' };
  }
  return { tier: 'P4', originalLabel: 'Info / P4', cssClass: 'badge-priority-p4' };
}

export function CategoryBadge({ category }) {
  const cat = (category || 'general_inquiry').toLowerCase();

  if (cat.includes('order')) {
    return (
      <span className="badge badge-cat-order">
        <Package size={12} />
        Order Issue
      </span>
    );
  }
  if (cat.includes('refund')) {
    return (
      <span className="badge badge-cat-refund">
        <RotateCcw size={12} />
        Refund
      </span>
    );
  }
  if (cat.includes('tech')) {
    return (
      <span className="badge badge-cat-tech">
        <Wrench size={12} />
        Technical Issue
      </span>
    );
  }
  return (
    <span className="badge badge-cat-general">
      <HelpCircle size={12} />
      General Inquiry
    </span>
  );
}

export function PriorityBadge({ priority, showOriginal = false }) {
  const { tier, originalLabel, cssClass } = mapPriorityToUrgency(priority);

  return (
    <span
      className={`badge ${cssClass}`}
      title={`Urgency: ${tier} | Original Priority: ${originalLabel}`}
    >
      {tier === 'P1' ? (
        <Flame size={12} />
      ) : tier === 'P2' ? (
        <AlertTriangle size={12} />
      ) : null}
      <span>{showOriginal ? `${tier} · ${originalLabel}` : tier}</span>
    </span>
  );
}

export function SecurityBadge({ detected }) {
  if (!detected) return null;
  return (
    <span
      className="badge badge-security-guarded"
      title="Prompt injection attempt detected and isolated as untrusted input"
    >
      <ShieldAlert size={12} />
      Injection Blocked
    </span>
  );
}

export function SentimentBadge({ sentiment }) {
  const s = (sentiment || 'Neutral').toLowerCase();

  if (s.includes('urgent')) {
    return (
      <span className="badge badge-sent-urgent">
        <Flame size={12} />
        Highly Urgent
      </span>
    );
  }
  if (s.includes('angry')) {
    return (
      <span className="badge badge-sent-frustrated">
        <Frown size={12} />
        Angry
      </span>
    );
  }
  if (s.includes('frustrat')) {
    return (
      <span className="badge badge-sent-frustrated">
        <Frown size={12} />
        Frustrated
      </span>
    );
  }
  if (s.includes('pos')) {
    return (
      <span className="badge badge-sent-positive">
        <Smile size={12} />
        Positive
      </span>
    );
  }
  return (
    <span className="badge badge-sent-neutral">
      <Meh size={12} />
      Neutral
    </span>
  );
}

export function StatusBadge({ status }) {
  const st = (status || 'open').toLowerCase();

  if (st === 'resolved' || st === 'closed') {
    return <span className="badge badge-status-resolved">Resolved</span>;
  }
  if (st === 'in_progress') {
    return <span className="badge badge-status-inprogress">In Progress</span>;
  }
  if (st === 'pending') {
    return <span className="badge badge-status-pending">Pending</span>;
  }
  return <span className="badge badge-status-open">Open</span>;
}

export function ApprovalBadge({ approvalStatus }) {
  const st = (approvalStatus || 'pending').toLowerCase();
  if (st === 'approved') {
    return (
      <span className="badge badge-status-resolved" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
        <CheckCircle2 size={12} />
        Approved
      </span>
    );
  }
  if (st === 'rejected') {
    return (
      <span className="badge badge-priority-p1" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
        <AlertTriangle size={12} />
        Rejected
      </span>
    );
  }
  return (
    <span className="badge badge-status-pending" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
      Pending Approval
    </span>
  );
}
