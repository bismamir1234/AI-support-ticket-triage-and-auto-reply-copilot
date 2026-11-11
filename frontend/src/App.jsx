import React, { useState, useEffect, useMemo } from 'react';
import {
  Download,
  FileJson,
  Sparkles,
  PlusCircle,
  Search,
  CheckCircle,
  CheckCircle2,
  RotateCcw,
  Send,
  Save,
  AlertTriangle,
  AlertCircle,
  Clock,
  ShieldCheck,
  User,
  Mail,
  X,
  Undo,
  ExternalLink,
  Bot,
  Flame,
  Check,
  BarChart3,
  Tag,
  Sun,
  Moon,
} from 'lucide-react';

import Sidebar from './components/Sidebar';
import StatsCards from './components/StatsCards';
import {
  CategoryBadge,
  PriorityBadge,
  SentimentBadge,
  StatusBadge,
  ApprovalBadge,
} from './components/Badges';

import {
  fetchTickets,
  fetchTicketStats,
  fetchTicketById,
  processNewTicket,
  updateTicket,
  approveTicket,
  resolveTicket,
  regenerateReply,
  seedSampleTickets,
  downloadExportCsv,
  downloadExportJson,
} from './api';

export default function App() {
  // Theme State (Dark Mode)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (isDarkMode) {
      document.body.classList.add('dark-mode');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.remove('dark-mode');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode((prev) => !prev);
  };

  // Navigation & Filtering
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPriority, setSelectedPriority] = useState('all');

  // Core Data
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Draft Editing State
  const [draftText, setDraftText] = useState('');
  const [initialDraftText, setInitialDraftText] = useState('');
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isResolving, setIsResolving] = useState(false);

  // Modals & Notifications
  const [showNewTicketModal, setShowNewTicketModal] = useState(false);
  const [mockNoticeModal, setMockNoticeModal] = useState(null);
  const [toasts, setToasts] = useState([]);

  // New Ticket Form State
  const [newTicketForm, setNewTicketForm] = useState({
    ticket_id: '',
    customer_name: '',
    customer_email: '',
    subject: '',
    message: '',
  });
  const [isSubmittingTicket, setIsSubmittingTicket] = useState(false);

  // Toast Helper
  const addToast = (type, message, details = '') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, type, message, details }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5500);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Initial Load & Refresh
  const loadData = async (preserveSelectedId = null) => {
    try {
      setIsLoading(true);
      const [ticketsData, statsData] = await Promise.all([
        fetchTickets(),
        fetchTicketStats(),
      ]);

      setTickets(ticketsData);
      setStats(statsData);

      const targetId = preserveSelectedId || selectedTicketId;
      if (targetId && ticketsData.some((t) => t.ticket_id === targetId)) {
        setSelectedTicketId(targetId);
      } else if (ticketsData.length > 0 && !preserveSelectedId) {
        setSelectedTicketId(ticketsData[0].ticket_id);
      }
    } catch (err) {
      console.error('Error loading tickets:', err);
      addToast('error', 'Failed to load tickets', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Sync draft text whenever selected ticket changes
  const selectedTicket = useMemo(() => {
    return tickets.find((t) => t.ticket_id === selectedTicketId) || null;
  }, [tickets, selectedTicketId]);

  useEffect(() => {
    if (selectedTicket) {
      const activeText =
        selectedTicket.edited_response || selectedTicket.generated_response || '';
      setDraftText(activeText);
      setInitialDraftText(activeText);
    } else {
      setDraftText('');
      setInitialDraftText('');
    }
  }, [selectedTicketId, selectedTicket?.updated_at]);

  const hasUnsavedChanges = useMemo(() => {
    return draftText.trim() !== initialDraftText.trim();
  }, [draftText, initialDraftText]);

  // Tab & Filter Logic
  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      // 1. Sidebar tab filter
      if (activeTab === 'open' && t.ticket_status !== 'open') return false;
      if (
        activeTab === 'pending' &&
        t.ticket_status !== 'pending' &&
        t.approval_status !== 'pending'
      )
        return false;
      if (
        activeTab === 'resolved' &&
        t.ticket_status !== 'resolved' &&
        t.ticket_status !== 'closed'
      )
        return false;

      // 2. Dropdown category filter
      if (selectedCategory !== 'all' && t.category !== selectedCategory)
        return false;

      // 3. Dropdown priority filter
      if (selectedPriority !== 'all' && t.priority !== selectedPriority)
        return false;

      // 4. Search query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesId = t.ticket_id.toLowerCase().includes(query);
        const matchesName = t.customer_name.toLowerCase().includes(query);
        const matchesEmail = t.customer_email.toLowerCase().includes(query);
        const matchesSubject = t.subject.toLowerCase().includes(query);
        return matchesId || matchesName || matchesEmail || matchesSubject;
      }

      return true;
    });
  }, [tickets, activeTab, selectedCategory, selectedPriority, searchQuery]);

  // =================================================================
  // ACTION HANDLERS
  // =================================================================

  // TASK 1: Save Draft Response
  const handleSaveDraft = async () => {
    if (!selectedTicket) return;
    try {
      setIsSavingDraft(true);
      const updated = await updateTicket(selectedTicket.ticket_id, {
        edited_response: draftText,
      });

      // Update state
      setTickets((prev) =>
        prev.map((t) => (t.ticket_id === updated.ticket_id ? updated : t))
      );
      setInitialDraftText(draftText);
      addToast('success', 'Draft Saved', 'Response changes preserved in SQLite.');
    } catch (err) {
      addToast('error', 'Failed to save draft', err.message);
    } finally {
      setIsSavingDraft(false);
    }
  };

  // TASK 1: Regenerate Draft
  const handleRegenerateDraft = async () => {
    if (!selectedTicket) return;
    try {
      setIsRegenerating(true);
      const regenerated = await regenerateReply(selectedTicket.ticket_id);

      setTickets((prev) =>
        prev.map((t) => (t.ticket_id === regenerated.ticket_id ? regenerated : t))
      );
      const newText =
        regenerated.edited_response || regenerated.generated_response || '';
      setDraftText(newText);
      setInitialDraftText(newText);
      addToast(
        'info',
        'Draft Regenerated',
        'AI regenerated policy-grounded reply and saved to SQLite.'
      );
    } catch (err) {
      addToast('error', 'Regeneration failed', err.message);
    } finally {
      setIsRegenerating(false);
    }
  };

  // TASK 2: Mock Approval & Send
  const handleApproveAndSend = async () => {
    if (!selectedTicket) return;
    try {
      setIsApproving(true);
      const result = await approveTicket(selectedTicket.ticket_id, draftText);
      const updatedTicket = result.ticket;

      // Update tickets list and stats
      setTickets((prev) =>
        prev.map((t) =>
          t.ticket_id === updatedTicket.ticket_id ? updatedTicket : t
        )
      );
      setInitialDraftText(draftText);

      // Refresh dashboard stats
      const newStats = await fetchTicketStats();
      setStats(newStats);

      // Open clear Mock Notice Dialog & Toast
      setMockNoticeModal({
        recipient: updatedTicket.customer_email,
        customerName: updatedTicket.customer_name,
        ticketId: updatedTicket.ticket_id,
        content: result.mock_send?.sent_content || draftText,
      });

      addToast(
        'success',
        'Mock Send Complete',
        'DEMO ONLY: No real email was sent to customer.'
      );
    } catch (err) {
      addToast('error', 'Approval failed', err.message);
    } finally {
      setIsApproving(false);
    }
  };

  // TASK 3: Mark Resolved
  const handleMarkResolved = async () => {
    if (!selectedTicket) return;
    try {
      setIsResolving(true);
      const result = await resolveTicket(selectedTicket.ticket_id);
      const resolvedTicket = result.ticket;

      setTickets((prev) =>
        prev.map((t) =>
          t.ticket_id === resolvedTicket.ticket_id ? resolvedTicket : t
        )
      );

      // Refresh dashboard stats
      const newStats = await fetchTicketStats();
      setStats(newStats);

      addToast(
        'success',
        'Ticket Resolved',
        `Ticket ${selectedTicket.ticket_id} status updated to Resolved in SQLite.`
      );
    } catch (err) {
      addToast('error', 'Failed to resolve ticket', err.message);
    } finally {
      setIsResolving(false);
    }
  };

  // TASK 4: CSV Export
  const handleExportCsv = async () => {
    try {
      await downloadExportCsv();
      addToast(
        'success',
        'CSV Export Downloaded',
        'File contains latest SQLite data: Ticket ID, Customer, Category, Priority, Sentiment, Missing entities, Status, and Final response.'
      );
    } catch (err) {
      addToast('error', 'Export CSV Failed', err.message);
    }
  };

  // TASK 5: JSON Export
  const handleExportJson = async () => {
    try {
      await downloadExportJson();
      addToast(
        'success',
        'JSON Export Downloaded',
        'Complete ticket analysis and response details exported.'
      );
    } catch (err) {
      addToast('error', 'Export JSON Failed', err.message);
    }
  };

  // Seed Realistic Demo Tickets
  const handleSeedSamples = async () => {
    try {
      setIsLoading(true);
      await seedSampleTickets();
      await loadData();
      addToast(
        'success',
        'Demo Tickets Seeded',
        'Sample tickets loaded with full policy matching & triage analysis.'
      );
    } catch (err) {
      addToast('error', 'Seeding failed', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle New Ticket Ingestion
  const handleCreateTicketSubmit = async (e) => {
    e.preventDefault();
    if (!newTicketForm.ticket_id || !newTicketForm.customer_email) {
      addToast('error', 'Missing Fields', 'Ticket ID and Email are required.');
      return;
    }

    try {
      setIsSubmittingTicket(true);
      const result = await processNewTicket(newTicketForm);
      await loadData(result.ticket.ticket_id);
      setShowNewTicketModal(false);
      setNewTicketForm({
        ticket_id: '',
        customer_name: '',
        customer_email: '',
        subject: '',
        message: '',
      });
      addToast(
        'success',
        'Ticket Processed',
        `Ticket ${result.ticket.ticket_id} ingested, analyzed, and persisted.`
      );
    } catch (err) {
      addToast('error', 'Failed to create ticket', err.message);
    } finally {
      setIsSubmittingTicket(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        stats={stats}
        isDarkMode={isDarkMode}
        toggleTheme={toggleTheme}
        onOpenNewTicketModal={() => {
          setNewTicketForm({
            ticket_id: `TCK-${Math.floor(1000 + Math.random() * 9000)}`,
            customer_name: '',
            customer_email: '',
            subject: '',
            message: '',
          });
          setShowNewTicketModal(true);
        }}
      />

      {/* Main Content Area */}
      <div className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-title-wrap">
            <h1>AI Support Ticket Triage & Auto-Reply Copilot</h1>
            <p>
              Groq LLM triage, policy-grounded draft responses, mock approval &
              data exports
            </p>
          </div>

          <div className="header-actions">
            <button
              className="btn btn-secondary"
              onClick={handleSeedSamples}
              title="Seed realistic sample tickets"
            >
              <Sparkles size={15} style={{ color: '#2563eb' }} />
              <span>Seed Samples</span>
            </button>

            <button
              className="btn btn-secondary"
              onClick={handleExportCsv}
              title="Download CSV export with latest SQLite data"
            >
              <Download size={15} />
              <span>Export CSV</span>
            </button>

            <button
              className="btn btn-secondary"
              onClick={handleExportJson}
              title="Download complete JSON ticket analysis"
            >
              <FileJson size={15} />
              <span>Export JSON</span>
            </button>

            <button
              className="btn btn-primary"
              onClick={() => {
                setNewTicketForm({
                  ticket_id: `TCK-${Math.floor(1000 + Math.random() * 9000)}`,
                  customer_name: '',
                  customer_email: '',
                  subject: '',
                  message: '',
                });
                setShowNewTicketModal(true);
              }}
            >
              <PlusCircle size={15} />
              <span>New Ticket</span>
            </button>

            {/* Dark Mode Toggle */}
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle theme mode"
            >
              {isDarkMode ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </header>

        {/* Dashboard Statistics Bar */}
        <StatsCards stats={stats} />

        {/* Reports View OR Workspace Inbox */}
        {activeTab === 'reports' ? (
          <div className="reports-panel">
            {/* Export Header Card */}
            <div className="export-section-card">
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
                  Support Operations Data Export
                </h3>
                <p style={{ fontSize: '13px', color: '#475569', marginTop: '4px' }}>
                  Export all tickets with live SQLite data, classification
                  metrics, missing entities, and final responses.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-primary" onClick={handleExportCsv}>
                  <Download size={16} />
                  <span>Download CSV</span>
                </button>
                <button className="btn btn-secondary" onClick={handleExportJson}>
                  <FileJson size={16} />
                  <span>Download JSON</span>
                </button>
              </div>
            </div>

            <div className="reports-grid">
              {/* Category Breakdown */}
              <div className="report-card">
                <div className="report-card-title">
                  <Tag size={18} style={{ color: '#2563eb' }} />
                  <span>Category Distribution</span>
                </div>
                <div>
                  {stats?.category_breakdown &&
                    Object.entries(stats.category_breakdown).map(
                      ([cat, count]) => {
                        const pct = stats.total_tickets
                          ? Math.round((count / stats.total_tickets) * 100)
                          : 0;
                        return (
                          <div key={cat} className="progress-row">
                            <div className="progress-label-row">
                              <span style={{ textTransform: 'capitalize' }}>
                                {cat.replace('_', ' ')}
                              </span>
                              <span style={{ fontWeight: 600 }}>
                                {count} ({pct}%)
                              </span>
                            </div>
                            <div className="progress-track">
                              <div
                                className="progress-fill"
                                style={{
                                  width: `${pct}%`,
                                  backgroundColor: '#3b82f6',
                                }}
                              />
                            </div>
                          </div>
                        );
                      }
                    )}
                </div>
              </div>

              {/* Sentiment Breakdown */}
              <div className="report-card">
                <div className="report-card-title">
                  <Flame size={18} style={{ color: '#ea580c' }} />
                  <span>Customer Sentiment Distribution</span>
                </div>
                <div>
                  {stats?.sentiment_breakdown &&
                    Object.entries(stats.sentiment_breakdown).map(
                      ([sent, count]) => {
                        const pct = stats.total_tickets
                          ? Math.round((count / stats.total_tickets) * 100)
                          : 0;
                        const barColor =
                          sent === 'Frustrated' || sent === 'Highly Urgent'
                            ? '#ef4444'
                            : sent === 'Positive'
                            ? '#10b981'
                            : '#64748b';
                        return (
                          <div key={sent} className="progress-row">
                            <div className="progress-label-row">
                              <span>{sent}</span>
                              <span style={{ fontWeight: 600 }}>
                                {count} ({pct}%)
                              </span>
                            </div>
                            <div className="progress-track">
                              <div
                                className="progress-fill"
                                style={{
                                  width: `${pct}%`,
                                  backgroundColor: barColor,
                                }}
                              />
                            </div>
                          </div>
                        );
                      }
                    )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Split Grid: Inbox + Detail */
          <div className="workspace-grid">
            {/* Left Column: Inbox List */}
            <div className="inbox-panel">
              <div className="inbox-toolbar">
                {/* Search */}
                <div className="search-input-wrap">
                  <Search size={15} className="search-icon" />
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search ID, customer, subject..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      style={{
                        position: 'absolute',
                        right: '10px',
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#94a3b8',
                      }}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>

                {/* Filters */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px',
                  }}
                >
                  <select
                    className="form-input"
                    style={{ fontSize: '12px', padding: '6px 10px' }}
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                  >
                    <option value="all">All Categories</option>
                    <option value="order_issue">Order Issue</option>
                    <option value="refund">Refund</option>
                    <option value="technical_issue">Technical Issue</option>
                    <option value="general_inquiry">General Inquiry</option>
                  </select>

                  <select
                    className="form-input"
                    style={{ fontSize: '12px', padding: '6px 10px' }}
                    value={selectedPriority}
                    onChange={(e) => setSelectedPriority(e.target.value)}
                  >
                    <option value="all">All Priorities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              {/* Tickets List */}
              <div className="inbox-list">
                {isLoading ? (
                  <div className="loading-spinner">
                    <Clock className="animate-spin" size={20} />
                    <span>Loading tickets...</span>
                  </div>
                ) : filteredTickets.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">
                      <AlertCircle size={24} />
                    </div>
                    <h4 style={{ fontSize: '14px', fontWeight: 600 }}>
                      No tickets found
                    </h4>
                    <p style={{ fontSize: '12px' }}>
                      Try adjusting your search or filters, or seed demo samples.
                    </p>
                  </div>
                ) : (
                  filteredTickets.map((ticket) => {
                    const isSelected = ticket.ticket_id === selectedTicketId;
                    return (
                      <div
                        key={ticket.ticket_id}
                        className={`ticket-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => setSelectedTicketId(ticket.ticket_id)}
                      >
                        <div className="ticket-item-top">
                          <span className="ticket-id">{ticket.ticket_id}</span>
                          <span
                            style={{
                              fontSize: '11px',
                              color: '#94a3b8',
                              fontWeight: 500,
                            }}
                          >
                            {new Date(ticket.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>

                        <div className="ticket-customer">
                          {ticket.customer_name}
                        </div>

                        <div className="ticket-subject">{ticket.subject}</div>

                        <div className="ticket-badges-row">
                          <CategoryBadge category={ticket.category} />
                          <PriorityBadge priority={ticket.priority} />
                          <SentimentBadge sentiment={ticket.sentiment} />
                          <StatusBadge status={ticket.ticket_status} />
                          {ticket.approval_status === 'approved' && (
                            <ApprovalBadge approvalStatus="approved" />
                          )}
                          {ticket.edited_response && (
                            <span
                              className="badge"
                              style={{
                                background: '#fef3c7',
                                color: '#b45309',
                                border: '1px solid #fde68a',
                                fontSize: '10px',
                              }}
                            >
                              Edited
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Column: Ticket Detail Workspace */}
            <div className="detail-panel">
              {!selectedTicket ? (
                <div
                  className="empty-state"
                  style={{ height: '100%', justifyContent: 'center' }}
                >
                  <div className="empty-state-icon">
                    <Bot size={28} />
                  </div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600 }}>
                    Select a ticket to inspect
                  </h3>
                  <p style={{ fontSize: '13px' }}>
                    Choose a support ticket from the inbox list to review AI
                    triage, edit responses, and manage approval.
                  </p>
                </div>
              ) : (
                <>
                  {/* Ticket Header & Resolution Actions */}
                  <div className="detail-card">
                    <div className="detail-card-header">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                        }}
                      >
                        <span
                          style={{
                            fontSize: '18px',
                            fontWeight: 700,
                            color: '#1e293b',
                            fontFamily: 'monospace',
                          }}
                        >
                          {selectedTicket.ticket_id}
                        </span>
                        <StatusBadge status={selectedTicket.ticket_status} />
                        <ApprovalBadge
                          approvalStatus={selectedTicket.approval_status}
                        />
                        <PriorityBadge priority={selectedTicket.priority} />
                      </div>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        {/* TASK 3: Mark Resolved Button */}
                        <button
                          className="btn btn-success"
                          onClick={handleMarkResolved}
                          disabled={
                            isResolving ||
                            selectedTicket.ticket_status === 'resolved'
                          }
                          title="Mark ticket as resolved and update dashboard stats"
                        >
                          <CheckCircle2 size={15} />
                          <span>
                            {selectedTicket.ticket_status === 'resolved'
                              ? 'Resolved'
                              : isResolving
                              ? 'Resolving...'
                              : 'Mark Resolved'}
                          </span>
                        </button>
                      </div>
                    </div>

                    {/* Customer Meta */}
                    <div className="customer-info-grid">
                      <div className="customer-info-item">
                        <span className="info-label">Customer Name</span>
                        <span className="info-val">
                          {selectedTicket.customer_name}
                        </span>
                      </div>
                      <div className="customer-info-item">
                        <span className="info-label">Customer Email</span>
                        <span className="info-val">
                          {selectedTicket.customer_email}
                        </span>
                      </div>
                      <div className="customer-info-item">
                        <span className="info-label">Submitted At</span>
                        <span className="info-val" style={{ fontSize: '12px' }}>
                          {new Date(selectedTicket.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="customer-info-item">
                        <span className="info-label">Last Saved</span>
                        <span className="info-val" style={{ fontSize: '12px' }}>
                          {new Date(selectedTicket.updated_at).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {/* Original Message Box */}
                    <div>
                      <div
                        style={{
                          fontSize: '12px',
                          fontWeight: 700,
                          color: '#475569',
                          marginBottom: '6px',
                        }}
                      >
                        SUBJECT: {selectedTicket.subject}
                      </div>
                      <div className="message-box">
                        {selectedTicket.original_message}
                      </div>
                    </div>
                  </div>

                  {/* AI Triage & Entity Extraction Card */}
                  <div className="detail-card">
                    <div className="detail-card-header">
                      <div className="detail-card-title">
                        <Sparkles size={16} style={{ color: '#2563eb' }} />
                        <span>AI Triage & Extracted Entities</span>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <CategoryBadge category={selectedTicket.category} />
                        <SentimentBadge sentiment={selectedTicket.sentiment} />
                      </div>
                    </div>

                    {/* Extracted Entities Chips */}
                    <div>
                      <span
                        className="info-label"
                        style={{ display: 'block', marginBottom: '8px' }}
                      >
                        Identified Entities
                      </span>
                      <div className="entity-chips-container">
                        {selectedTicket.extracted_entities &&
                        Object.keys(selectedTicket.extracted_entities).some(
                          (k) => selectedTicket.extracted_entities[k]
                        ) ? (
                          Object.entries(selectedTicket.extracted_entities)
                            .filter(([_, val]) => val)
                            .map(([key, val]) => (
                              <div key={key} className="entity-chip">
                                <span className="entity-chip-key">
                                  {key.replace('_', ' ')}:
                                </span>
                                <span className="entity-chip-val">{val}</span>
                              </div>
                            ))
                        ) : (
                          <span
                            style={{
                              fontSize: '12px',
                              color: '#94a3b8',
                              fontStyle: 'italic',
                            }}
                          >
                            No specific order ID or error code identified in message.
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Missing Entities Warning Banner */}
                    {selectedTicket.missing_entities &&
                      selectedTicket.missing_entities.length > 0 && (
                        <div className="alert-banner-warning">
                          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
                          <div>
                            <h4>Missing Information Detected</h4>
                            <p>
                              Customer must provide:{' '}
                              <strong>
                                {selectedTicket.missing_entities.join(', ')}
                              </strong>
                              . Draft response has been policy-grounded to politely
                              request this information.
                            </p>
                          </div>
                        </div>
                      )}
                  </div>

                  {/* Response Copilot & Human-In-The-Loop Card */}
                  <div className="detail-card">
                    <div className="detail-card-header">
                      <div className="detail-card-title">
                        <Bot size={18} style={{ color: '#2563eb' }} />
                        <span>Policy-Grounded Response Draft</span>
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                        }}
                      >
                        {hasUnsavedChanges ? (
                          <span className="unsaved-badge">
                            <Clock size={12} />
                            Unsaved Changes
                          </span>
                        ) : selectedTicket.edited_response ? (
                          <span className="saved-badge">
                            <Check size={12} />
                            Agent Edited (Saved)
                          </span>
                        ) : (
                          <span
                            className="badge"
                            style={{ background: '#f1f5f9', color: '#475569' }}
                          >
                            AI Generated Draft
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Mock Dispatched Notice if Approved */}
                    {selectedTicket.approval_status === 'approved' && (
                      <div className="mock-alert-banner">
                        <span className="mock-alert-badge">Approved</span>
                        <span>
                          <strong>Mock Sent:</strong> This response was recorded
                          and approved for {selectedTicket.customer_email}. No
                          real email was sent (Demonstration Project).
                        </span>
                      </div>
                    )}

                    {/* TASK 1: Editable Response Textarea */}
                    <textarea
                      className="response-textarea"
                      value={draftText}
                      onChange={(e) => setDraftText(e.target.value)}
                      placeholder="AI draft reply will appear here. Support agents can edit freely..."
                    />

                    {/* Action Bar */}
                    <div className="response-panel-footer">
                      <div style={{ display: 'flex', gap: '8px' }}>
                        {/* TASK 1: Regenerate Draft */}
                        <button
                          className="btn btn-secondary"
                          onClick={handleRegenerateDraft}
                          disabled={isRegenerating}
                          title="Re-run AI policy triage to regenerate the draft reply"
                        >
                          <RotateCcw
                            size={14}
                            className={isRegenerating ? 'animate-spin' : ''}
                          />
                          <span>
                            {isRegenerating ? 'Regenerating...' : 'Regenerate Draft'}
                          </span>
                        </button>

                        {/* Undo Edits button */}
                        {hasUnsavedChanges && (
                          <button
                            className="btn btn-secondary"
                            onClick={() => setDraftText(initialDraftText)}
                            title="Discard current unsaved edits"
                          >
                            <Undo size={14} />
                            <span>Discard</span>
                          </button>
                        )}
                      </div>

                      <div className="response-actions-right">
                        {/* TASK 1: Save Edited Response */}
                        <button
                          className="btn btn-secondary"
                          onClick={handleSaveDraft}
                          disabled={isSavingDraft || !hasUnsavedChanges}
                          title="Save edited response to SQLite database"
                        >
                          <Save size={14} />
                          <span>
                            {isSavingDraft ? 'Saving...' : 'Save Draft'}
                          </span>
                        </button>

                        {/* TASK 2: Approve & Send (Mock) */}
                        <button
                          className="btn btn-primary"
                          onClick={handleApproveAndSend}
                          disabled={isApproving}
                          title="Save response and record mock email approval (No real email is sent)"
                        >
                          <Send size={14} />
                          <span>
                            {isApproving ? 'Approving...' : 'Approve & Send'}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* TASK 2: Mock Sending Modal Notification */}
      {mockNoticeModal && (
        <div
          className="modal-overlay"
          onClick={() => setMockNoticeModal(null)}
        >
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ width: '600px' }}
          >
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={20} style={{ color: '#16a34a' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>
                  Response Approved & Mock Dispatched
                </h3>
              </div>
              <button
                onClick={() => setMockNoticeModal(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#64748b',
                }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div
                className="mock-alert-banner"
                style={{
                  backgroundColor: '#fef2f2',
                  borderColor: '#fca5a5',
                  color: '#991b1b',
                }}
              >
                <AlertCircle size={20} style={{ flexShrink: 0 }} />
                <div>
                  <strong>DEMONSTRATION PROJECT NOTICE:</strong>
                  <div style={{ marginTop: '2px', fontSize: '12px' }}>
                    No real email was transmitted. The response has been
                    approved and permanently stored in your SQLite database.
                  </div>
                </div>
              </div>

              <div className="customer-info-grid">
                <div className="customer-info-item">
                  <span className="info-label">Ticket ID</span>
                  <span className="info-val">{mockNoticeModal.ticketId}</span>
                </div>
                <div className="customer-info-item">
                  <span className="info-label">Customer Recipient</span>
                  <span className="info-val">{mockNoticeModal.recipient}</span>
                </div>
              </div>

              <div>
                <span
                  className="info-label"
                  style={{ display: 'block', marginBottom: '6px' }}
                >
                  Dispatched Response Content
                </span>
                <div
                  className="message-box"
                  style={{
                    maxHeight: '180px',
                    overflowY: 'auto',
                    fontSize: '13px',
                  }}
                >
                  {mockNoticeModal.content}
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn btn-primary"
                onClick={() => setMockNoticeModal(null)}
              >
                <span>Understood</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Ticket Ingestion Modal */}
      {showNewTicketModal && (
        <div
          className="modal-overlay"
          onClick={() => setShowNewTicketModal(false)}
        >
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <PlusCircle size={18} style={{ color: '#2563eb' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>
                  Ingest New Customer Ticket
                </h3>
              </div>
              <button
                onClick={() => setShowNewTicketModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#64748b',
                }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateTicketSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Ticket ID</label>
                  <input
                    type="text"
                    className="form-input"
                    value={newTicketForm.ticket_id}
                    onChange={(e) =>
                      setNewTicketForm({
                        ...newTicketForm,
                        ticket_id: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '12px',
                  }}
                >
                  <div className="form-group">
                    <label className="form-label">Customer Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Sarah Connor"
                      value={newTicketForm.customer_name}
                      onChange={(e) =>
                        setNewTicketForm({
                          ...newTicketForm,
                          customer_name: e.target.value,
                        })
                      }
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Customer Email</label>
                    <input
                      type="email"
                      className="form-input"
                      placeholder="e.g. sarah@example.com"
                      value={newTicketForm.customer_email}
                      onChange={(e) =>
                        setNewTicketForm({
                          ...newTicketForm,
                          customer_email: e.target.value,
                        })
                      }
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Subject</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Return request for defective item"
                    value={newTicketForm.subject}
                    onChange={(e) =>
                      setNewTicketForm({
                        ...newTicketForm,
                        subject: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Customer Message</label>
                  <textarea
                    className="form-textarea"
                    rows={4}
                    placeholder="Paste the customer email or chat inquiry here..."
                    value={newTicketForm.message}
                    onChange={(e) =>
                      setNewTicketForm({
                        ...newTicketForm,
                        message: e.target.value,
                      })
                    }
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowNewTicketModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmittingTicket}
                >
                  <Sparkles size={14} />
                  <span>
                    {isSubmittingTicket
                      ? 'Analyzing with AI...'
                      : 'Run AI Triage & Persist'}
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toast Notification Container */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast ${
              toast.type === 'error'
                ? 'toast-error'
                : toast.type === 'success'
                ? 'toast-success'
                : ''
            }`}
            onClick={() => removeToast(toast.id)}
            style={{ cursor: 'pointer' }}
          >
            {toast.type === 'error' ? (
              <AlertCircle size={16} />
            ) : toast.type === 'success' ? (
              <CheckCircle size={16} />
            ) : (
              <Sparkles size={16} />
            )}
            <div>
              <div style={{ fontWeight: 600 }}>{toast.message}</div>
              {toast.details && (
                <div style={{ fontSize: '11px', opacity: 0.85, marginTop: '2px' }}>
                  {toast.details}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
