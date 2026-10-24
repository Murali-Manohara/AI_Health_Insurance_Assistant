import React, { useState } from 'react';
import { authApi } from '../services/authApi';

export function LoginScreen({ onLoginSuccess, onSwitchToSignup }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError('Please provide both email and password.');
      return;
    }

    setLoading(true);
    try {
      const data = await authApi.login(email.trim(), password);
      if (onLoginSuccess) {
        onLoginSuccess(data.user, data.token);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemo = (demoEmail, demoPw) => {
    setEmail(demoEmail);
    setPassword(demoPw);
    setError(null);
  };

  return (
    <div className="auth-card-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand-badge">Secure Access</div>
          <h2 className="auth-title">Sign In to Insurance Assistant</h2>
          <p className="auth-subtitle">
            Access plan-scoped AI guidance, policy coverage terms, and verified benefits.
          </p>
        </div>

        {error && (
          <div className="auth-error-banner" role="alert">
            <span className="auth-error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="auth-field">
            <label className="auth-label" htmlFor="login-email">
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              className="auth-input"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              autoComplete="email"
              required
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="login-password">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              className="auth-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="current-password"
              required
            />
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-btn-spinner-content">
                <span className="auth-spinner"></span>
                <span>Authenticating...</span>
              </span>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Quick Demo Credentials Assistant */}
        <div className="auth-demo-chips">
          <span className="auth-demo-label">Quick Demo Access:</span>
          <button
            type="button"
            className="demo-chip-btn"
            onClick={() => handleFillDemo('customer@insurance.com', 'Customer@123')}
          >
            👤 Customer Demo
          </button>
          <button
            type="button"
            className="demo-chip-btn"
            onClick={() => handleFillDemo('employee@insurance.corp', 'Employee@123')}
          >
            🛡️ Corporate Employee Demo
          </button>
        </div>

        <div className="auth-footer">
          <span>Don't have an account? </span>
          <button
            type="button"
            className="auth-switch-link"
            onClick={onSwitchToSignup}
            disabled={loading}
          >
            Create an Account
          </button>
        </div>
      </div>
    </div>
  );
}
