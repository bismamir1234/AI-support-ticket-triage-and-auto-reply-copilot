const API_BASE = '/api/v1/tickets';

function extractErrorMessage(errorBody, fallback) {
  if (!errorBody) return fallback;
  if (typeof errorBody.detail === 'string') {
    return errorBody.detail;
  }
  if (Array.isArray(errorBody.detail) && errorBody.detail.length > 0) {
    return errorBody.detail
      .map((item) => {
        const msg = item?.msg || 'Validation error';
        return msg.replace(/^Value error,\s*/i, '');
      })
      .join(' ');
  }
  if (typeof errorBody.message === 'string') {
    return errorBody.message;
  }
  return fallback;
}

async function handleApiResponse(res, fallbackMessage) {
  if (res.ok) {
    return res.json();
  }
  const errorBody = await res.json().catch(() => null);
  const message = extractErrorMessage(errorBody, `${fallbackMessage} (${res.status} ${res.statusText})`);
  const err = new Error(message);
  err.status = res.status;
  err.code = errorBody?.error_code || null;
  throw err;
}

async function safeFetch(url, options = {}, fallbackMessage = 'Request failed') {
  try {
    const res = await fetch(url, options);
    return await handleApiResponse(res, fallbackMessage);
  } catch (err) {
    if (err instanceof TypeError) {
      const netErr = new Error('Network connection error: Unable to reach the backend API server.');
      netErr.code = 'NETWORK_CONNECTION_ERROR';
      throw netErr;
    }
    throw err;
  }
}

export async function fetchAiStatus() {
  return safeFetch(`${API_BASE}/ai-status`, {}, 'Failed to check AI service status');
}

export async function fetchTickets(filterParams = {}) {
  const query = new URLSearchParams();
  if (filterParams.category) query.append('category', filterParams.category);
  if (filterParams.priority) query.append('priority', filterParams.priority);
  if (filterParams.ticket_status) query.append('ticket_status', filterParams.ticket_status);
  if (filterParams.approval_status) query.append('approval_status', filterParams.approval_status);

  const url = `${API_BASE}${query.toString() ? `?${query.toString()}` : ''}`;
  return safeFetch(url, {}, 'Failed to fetch tickets');
}

export async function fetchTicketStats() {
  return safeFetch(`${API_BASE}/stats`, {}, 'Failed to fetch dashboard stats');
}

export async function fetchTicketById(ticketId) {
  return safeFetch(`${API_BASE}/${ticketId}`, {}, `Failed to fetch ticket ${ticketId}`);
}

export async function processNewTicket(ticketData) {
  return safeFetch(
    `${API_BASE}/process`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ticketData),
    },
    'Failed to process ticket'
  );
}

export async function updateTicket(ticketId, updates) {
  return safeFetch(
    `${API_BASE}/${ticketId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    },
    `Failed to update ticket ${ticketId}`
  );
}

export async function regenerateReply(ticketId) {
  return safeFetch(
    `${API_BASE}/${ticketId}/regenerate`,
    { method: 'POST' },
    'Failed to regenerate reply'
  );
}

export async function seedSampleTickets() {
  return safeFetch(
    `${API_BASE}/seed-samples`,
    { method: 'POST' },
    'Failed to seed samples'
  );
}

export async function approveTicket(ticketId, editedResponse = null) {
  const payload =
    editedResponse !== null && editedResponse !== undefined
      ? { edited_response: editedResponse }
      : {};
  return safeFetch(
    `${API_BASE}/${ticketId}/approve`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    `Failed to approve ticket ${ticketId}`
  );
}

export async function rejectTicket(ticketId) {
  return safeFetch(
    `${API_BASE}/${ticketId}/reject`,
    { method: 'POST' },
    `Failed to reject ticket ${ticketId}`
  );
}

export async function resolveTicket(ticketId) {
  return safeFetch(
    `${API_BASE}/${ticketId}/resolve`,
    { method: 'POST' },
    `Failed to resolve ticket ${ticketId}`
  );
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

export async function downloadBatchLogCsv(filterParams = {}) {
  const query = new URLSearchParams();
  if (filterParams.category) query.append('category', filterParams.category);
  if (filterParams.priority) query.append('priority', filterParams.priority);
  if (filterParams.ticket_status) query.append('ticket_status', filterParams.ticket_status);
  if (filterParams.approval_status) query.append('approval_status', filterParams.approval_status);

  const url = `${API_BASE}/export/batch-csv${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to download Batch Log CSV: ${res.statusText}`);
  }
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `batch_tickets_log_${new Date().toISOString().slice(0, 10)}.csv`;
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
