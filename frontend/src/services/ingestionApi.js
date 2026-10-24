import { authApi } from './authApi';

const API_BASE = 'http://127.0.0.1:8000/api';

function getAuthHeaders() {
  const token = authApi.getToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function fetchPlans() {
  const res = await fetch(`${API_BASE}/plans`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch plan registry');
  const data = await res.json();
  return data.plans;
}

export async function uploadAndIngest(file, planId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('plan_id', planId);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    const errorMsg = data.detail?.message || data.detail || 'Upload failed';
    const errors = data.detail?.errors || [errorMsg];
    const err = new Error(errorMsg);
    err.errors = errors;
    err.warnings = data.detail?.warnings || [];
    throw err;
  }
  return data;
}

export async function fetchJobStatus(jobId) {
  const res = await fetch(`${API_BASE}/ingestion/${jobId}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch job ${jobId}`);
  return res.json();
}

export async function fetchHistory() {
  const res = await fetch(`${API_BASE}/ingestion/history`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}
