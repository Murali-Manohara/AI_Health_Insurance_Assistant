import { authApi } from './authApi';

const API_BASE = '/api/eligibility';
const DIRECT_BACKEND = 'http://127.0.0.1:8000/api/eligibility';

async function safeFetch(endpoint, options = {}) {
  const token = authApi.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

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

async function handleResponse(res) {
  const text = await res.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!res.ok) {
    const err = data.detail || data.message || `Request failed with status ${res.status}`;
    throw new Error(err);
  }

  return data;
}

export const eligibilityApi = {
  async assess(profile) {
    const res = await safeFetch('/assess', {
      method: 'POST',
      body: JSON.stringify(profile),
    });
    return handleResponse(res);
  },

  async getMyAssessment() {
    const res = await safeFetch('/me', {
      method: 'GET',
    });
    return handleResponse(res);
  },

  async selectPlan(selectedPlanId, assessmentId = null) {
    const res = await safeFetch('/select-plan', {
      method: 'POST',
      body: JSON.stringify({
        selected_plan_id: selectedPlanId,
        assessment_id: assessmentId,
      }),
    });
    return handleResponse(res);
  },

  async confirmPlan(selectedPlanId) {
    const res = await safeFetch('/confirm-plan', {
      method: 'POST',
      body: JSON.stringify({
        plan_id: selectedPlanId,
      }),
    });
    return handleResponse(res);
  },

  async contactAgent(contactData) {
    const res = await safeFetch('/agent-contact', {
      method: 'POST',
      body: JSON.stringify(contactData),
    });
    return handleResponse(res);
  },

  async getModelHealth() {
    const res = await safeFetch('/health', {
      method: 'GET',
    });
    return handleResponse(res);
  },

  async getPlanReviewDetails(planId) {
    const token = authApi.getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      const res = await fetch(`/api/plans/${planId}/review-details`, { method: 'GET', headers });
      return handleResponse(res);
    } catch {
      const directUrl = `http://127.0.0.1:8000/api/plans/${planId}/review-details`;
      const res = await fetch(directUrl, { method: 'GET', headers });
      return handleResponse(res);
    }
  },
};
