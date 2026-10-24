import React, { useState } from 'react';
import { authApi } from '../services/authApi';

export function SignupScreen({ onSignupSuccess, onSwitchToLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('customer'); // 'customer' | 'employee'
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const validateForm = () => {
    if (!email.trim()) {
      return 'Please enter a valid email address.';
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      return 'Please enter a properly formatted email (e.g. user@example.com).';
    }
    if (!password) {
      return 'Please enter a password.';
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters long.';
    }
    if (password !== confirmPassword) {
      return 'Passwords do not match. Please re-enter.';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setNotice(null);

    const clientValidationErr = validateForm();
    if (clientValidationErr) {
      setError(clientValidationErr);
      return;
    }

    setLoading(true);
    try {
      const data = await authApi.signup(
        email.trim(),
        password,
        role,
        fullName.trim() || undefined
      );

      if (data.message && data.message.includes('pending')) {
        setNotice(data.message);
      }

      if (onSignupSuccess) {
        onSignupSuccess(data.user, data.token);
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Please check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-card-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand-badge">Create Account</div>
          <h2 className="auth-title">Register for Insurance Assistant</h2>
          <p className="auth-subtitle">
            Create an account to explore insurance policies and engage in grounded plan consultations.
          </p>
        </div>

        {error && (
          <div className="auth-error-banner" role="alert">
            <span className="auth-error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {notice && (
          <div className="auth-notice-banner" role="status">
            <span className="auth-notice-icon">ℹ️</span>
            <span>{notice}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="auth-field">
            <label className="auth-label" htmlFor="signup-name">
              Full Name (Optional)
            </label>
            <input
              id="signup-name"
              type="text"
              className="auth-input"
              placeholder="e.g. Alex Morgan"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={loading}
              autoComplete="name"
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="signup-email">
              Email Address
            </label>
            <input
              id="signup-email"
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
            <label className="auth-label">Account Role</label>
            <div className="auth-role-selector">
              <label className={`role-pill-label ${role === 'customer' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="account-role"
                  value="customer"
                  checked={role === 'customer'}
                  onChange={() => setRole('customer')}
                  disabled={loading}
                  style={{ display: 'none' }}
                />
                <span className="role-pill-title">Customer</span>
                <span className="role-pill-desc">Access Basic, Gold & Premium policies</span>
              </label>

              <label className={`role-pill-label ${role === 'employee' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="account-role"
                  value="employee"
                  checked={role === 'employee'}
                  onChange={() => setRole('employee')}
                  disabled={loading}
                  style={{ display: 'none' }}
                />
                <span className="role-pill-title">Corporate Employee</span>
                <span className="role-pill-desc">Requires corporate verification</span>
              </label>
            </div>

            {role === 'employee' && (
              <div className="role-security-note">
                🔒 <strong>Employee Protection Notice:</strong> Self-selecting Employee requires corporate domain verification (<code>@insurance.corp</code>) or administrative approval. Standard customer access is provisioned during verification.
              </div>
            )}
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="signup-password">
              Password
            </label>
            <input
              id="signup-password"
              type="password"
              className="auth-input"
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="new-password"
              required
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="signup-confirm-password">
              Confirm Password
            </label>
            <input
              id="signup-confirm-password"
              type="password"
              className="auth-input"
              placeholder="Re-enter password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              autoComplete="new-password"
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
                <span>Creating Account...</span>
              </span>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <span>Already have an account? </span>
          <button
            type="button"
            className="auth-switch-link"
            onClick={onSwitchToLogin}
            disabled={loading}
          >
            Sign In Instead
          </button>
        </div>
      </div>
    </div>
  );
}
