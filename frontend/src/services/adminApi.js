import { authApi } from './authApi';

const API_BASE = '/api/admin';
const DIRECT_BACKEND = 'http://127.0.0.1:8000/api/admin';

function getHeaders() {
  const token = authApi.getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

async function safeFetch(endpoint, options = {}) {
  const headers = {
    ...getHeaders(),
    ...(options.headers || {})
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    return res;
  } catch (err) {
    try {
      const directUrl = `${DIRECT_BACKEND}${endpoint}`;
      return await fetch(directUrl, { ...options, headers });
    } catch {
      throw err;
    }
  }
}

async function handleResponse(res, fallbackError) {
  if (!res.ok) {
    let msg = fallbackError;
    try {
      const data = await res.json();
      msg = data.detail || data.message || fallbackError;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export const adminApi = {
  async fetchOverview(rangePreset = '7d', startDate = null, endDate = null) {
    const params = new URLSearchParams({ range: rangePreset });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const res = await safeFetch(`/overview?${params.toString()}`);
    return handleResponse(res, 'Failed to fetch executive overview');
  },

  async fetchUsers(limit = 50, offset = 0, search = '', role = '', rangePreset = '', startDate = null, endDate = null) {
    const params = new URLSearchParams({ limit, offset });
    if (search) params.append('search', search);
    if (role) params.append('role', role);
    if (rangePreset) params.append('range', rangePreset);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const res = await safeFetch(`/users?${params.toString()}`);
    return handleResponse(res, 'Failed to fetch user list');
  },

  async updateUserStatus(userId, isApproved) {
    const res = await safeFetch(`/users/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_approved: isApproved })
    });
    return handleResponse(res, 'Failed to update user status');
  },

  async fetchDocuments(limit = 50, offset = 0, planId = '', status = '', rangePreset = '', startDate = null, endDate = null) {
    const params = new URLSearchParams({ limit, offset });
    if (planId) params.append('plan_id', planId);
    if (status) params.append('status', status);
    if (rangePreset) params.append('range', rangePreset);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const res = await safeFetch(`/documents?${params.toString()}`);
    return handleResponse(res, 'Failed to fetch document inventory');
  },

  async deleteDocument(documentId) {
    const res = await safeFetch(`/documents/${documentId}`, {
      method: 'DELETE'
    });
    return handleResponse(res, 'Failed to delete document');
  },

  async reindexDocument(documentId) {
    const res = await safeFetch(`/documents/${documentId}/reindex`, {
      method: 'POST'
    });
    return handleResponse(res, 'Failed to request document reindexing');
  },

  async fetchConversations(rangePreset = '7d', startDate = null, endDate = null) {
    const params = new URLSearchParams({ range: rangePreset });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const res = await safeFetch(`/conversations?${params.toString()}`);
    return handleResponse(res, 'Failed to fetch conversation analytics');
  },

  async fetchRagMetrics(rangePreset = '7d') {
    const res = await safeFetch(`/rag-metrics?range=${rangePreset}`);
    return handleResponse(res, 'Failed to fetch RAG metrics');
  },

  async fetchAuditLogs(limit = 50, offset = 0, action = '', outcome = '') {
    const params = new URLSearchParams({ limit, offset });
    if (action) params.append('action', action);
    if (outcome) params.append('outcome', outcome);

    const res = await safeFetch(`/audit-logs?${params.toString()}`);
    return handleResponse(res, 'Failed to fetch audit logs');
  },

  async fetchSystemHealth() {
    const res = await safeFetch(`/system-health`);
    return handleResponse(res, 'Failed to fetch system health status');
  }
};
