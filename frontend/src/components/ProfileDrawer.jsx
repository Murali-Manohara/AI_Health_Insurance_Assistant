import React from "react";

/**
 * ProfileDrawer — Slide-in Right Sidebar for User Profile & Account Settings.
 * Triggered by the user avatar/profile icon in the top right header.
 */
export function ProfileDrawer({
  isOpen,
  onClose,
  currentUser,
  selectedPlan,
  onLogout,
}) {
  if (!isOpen || !currentUser) return null;

  const userRole = currentUser.role || "customer";
  const displayName =
    currentUser.full_name ||
    (userRole === "employee"
      ? "Insurance Underwriter"
      : "Policy Holder Customer");
  const initial = (displayName || currentUser.email || "U")[0].toUpperCase();

  return (
    <>
      {/* Backdrop overlay for clicking outside */}
      <div
        className="profile-drawer-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Right-side Slide-in Profile Drawer */}
      <aside className="profile-drawer-panel" aria-label="User Profile Drawer">
        {/* Header */}
        <div className="profile-drawer-header">
          <div className="profile-drawer-title-row">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <span className="profile-drawer-title">Account Profile</span>
          </div>
          <button
            type="button"
            className="profile-drawer-close-btn"
            onClick={onClose}
            aria-label="Close profile drawer"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="profile-drawer-body">
          {/* User Hero Card */}
          <div className="profile-hero-card">
            <div className="profile-hero-avatar">{initial}</div>
            <div className="profile-hero-info">
              <h3 className="profile-hero-name">{displayName}</h3>
              <p className="profile-hero-email">
                {currentUser.email || "customer@example.com"}
              </p>
              <div className="profile-hero-tags">
                <span className={`user-role-tag ${userRole}`}>{userRole}</span>
                <span className="profile-status-tag">
                  <span className="profile-status-dot"></span>
                  Active Session
                </span>
              </div>
            </div>
          </div>

          {/* Account Details Section */}
          <div className="profile-section">
            <h4 className="profile-section-heading">Session & Security</h4>
            <div className="profile-detail-row">
              <span className="profile-detail-label">Access Level</span>
              <span className="profile-detail-value">
                {userRole === "employee"
                  ? "Internal Underwriting & Ingestion"
                  : "Standard Policy Holder"}
              </span>
            </div>
            <div className="profile-detail-row">
              <span className="profile-detail-label">Approval Status</span>
              <span className="profile-detail-value">
                {currentUser.is_approved ? (
                  <span
                    style={{ color: "var(--success-text)", fontWeight: 600 }}
                  >
                    Verified & Approved
                  </span>
                ) : (
                  <span style={{ color: "#b45309", fontWeight: 600 }}>
                    Standard Verification
                  </span>
                )}
              </span>
            </div>
            {selectedPlan && (
              <div className="profile-detail-row">
                <span className="profile-detail-label">Active Plan Scope</span>
                <span
                  className="profile-detail-value"
                  style={{ fontWeight: 600, color: "var(--accent-text)" }}
                >
                  {selectedPlan.plan_name} ({selectedPlan.plan_id})
                </span>
              </div>
            )}
          </div>

          {/* Permissions / Scope Note */}
          <div className="profile-notice-box">
            <div className="profile-notice-icon">🛡️</div>
            <div className="profile-notice-text">
              Your session is authenticated and plan-scoped. Grounded retrieval
              strictly adheres to your assigned role permissions.
            </div>
          </div>
        </div>

        {/* Footer with Logout Button */}
        <div className="profile-drawer-footer">
          <button
            type="button"
            className="profile-logout-btn"
            onClick={onLogout}
            title="Sign out of application"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            <span>Log Out</span>
          </button>
        </div>
      </aside>
    </>
  );
}

export default ProfileDrawer;
