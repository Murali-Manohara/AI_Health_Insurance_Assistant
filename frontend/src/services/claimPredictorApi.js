/**
 * Client service for the Employee-Only Insurance Claim Predictor API.
 */
export const claimPredictorApi = {
  async predict(data, token) {
    const headers = {
      'Content-Type': 'application/json'
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    let res;
    try {
      res = await fetch('/api/claim-predictor/predict', {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
      });
    } catch {
      res = await fetch('http://127.0.0.1:8000/api/claim-predictor/predict', {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
      });
    }

    const text = await res.text();
    let body = {};
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = { detail: text };
      }
    }

    if (!res.ok) {
      let errorMsg = `Prediction request failed (HTTP ${res.status})`;
      if (typeof body.detail === 'string') {
        errorMsg = body.detail;
      } else if (Array.isArray(body.detail)) {
        errorMsg = body.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
      } else if (body.detail && typeof body.detail === 'object') {
        errorMsg = JSON.stringify(body.detail);
      }
      const err = new Error(errorMsg);
      err.status = res.status;
      err.data = body;
      throw err;
    }

    return body;
  },

  async predictClaimPayout(data, token) {
    return this.predict(data, token);
  }
};

