const API_BASE = '/api/v1/tickets';

export async function fetchTickets(filterParams = {}) {
  const query = new URLSearchParams();
  if (filterParams.category) query.append('category', filterParams.category);
  if (filterParams.priority) query.append('priority', filterParams.priority);
  if (filterParams.ticket_status) query.append('ticket_status', filterParams.ticket_status);
  if (filterParams.approval_status) query.append('approval_status', filterParams.approval_status);

  const url = `${API_BASE}${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch tickets: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTicketStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) {
    throw new Error(`Failed to fetch dashboard stats: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTicketById(ticketId) {
  const res = await fetch(`${API_BASE}/${ticketId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ticket ${ticketId}: ${res.statusText}`);
  }
  return res.json();
}

export async function processNewTicket(ticketData) {
  const res = await fetch(`${API_BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ticketData),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to process ticket: ${res.statusText}`);
  }
  return res.json();
}

export async function updateTicket(ticketId, updates) {
  const res = await fetch(`${API_BASE}/${ticketId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    throw new Error(`Failed to update ticket ${ticketId}: ${res.statusText}`);
  }
  return res.json();
}

export async function regenerateReply(ticketId) {
  const res = await fetch(`${API_BASE}/${ticketId}/regenerate`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to regenerate reply: ${res.statusText}`);
  }
  return res.json();
}

export async function seedSampleTickets() {
  const res = await fetch(`${API_BASE}/seed-samples`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to seed samples: ${res.statusText}`);
  }
  return res.json();
}

export async function approveTicket(ticketId, editedResponse = null) {
  const payload = editedResponse !== null && editedResponse !== undefined ? { edited_response: editedResponse } : {};
  const res = await fetch(`${API_BASE}/${ticketId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to approve ticket ${ticketId}: ${res.statusText}`);
  }
  return res.json();
}

export async function resolveTicket(ticketId) {
  const res = await fetch(`${API_BASE}/${ticketId}/resolve`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to resolve ticket ${ticketId}: ${res.statusText}`);
  }
  return res.json();
}

export async function downloadExportCsv(filterParams = {}) {
  const query = new URLSearchParams();
  if (filterParams.category) query.append('category', filterParams.category);
  if (filterParams.priority) query.append('priority', filterParams.priority);
  if (filterParams.ticket_status) query.append('ticket_status', filterParams.ticket_status);
  if (filterParams.approval_status) query.append('approval_status', filterParams.approval_status);

  const url = `${API_BASE}/export/csv${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to download CSV: ${res.statusText}`);
  }
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `tickets_export_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export async function downloadExportJson(filterParams = {}) {
  const query = new URLSearchParams();
  if (filterParams.category) query.append('category', filterParams.category);
  if (filterParams.priority) query.append('priority', filterParams.priority);
  if (filterParams.ticket_status) query.append('ticket_status', filterParams.ticket_status);
  if (filterParams.approval_status) query.append('approval_status', filterParams.approval_status);

  const url = `${API_BASE}/export/json${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to download JSON: ${res.statusText}`);
  }
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `tickets_export_${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

