import React, { useState, useEffect } from "react";
import { authApi } from "../services/authApi";

/**
 * ProfileDrawer — Slide-in Right Sidebar for User Profile & Account Settings.
 * Displays authoritative data retrieved from backend /auth/me persisted in SQLite.
 * Tailored for Customer, Employee, and Administrator roles per governance specification.
 */
export function ProfileDrawer({
  isOpen,
  onClose,
  currentUser,
  selectedPlan,
  assessment,
  onLogout,
}) {
  const [profileData, setProfileData] = useState(currentUser);

  // Refresh authoritative profile from backend whenever drawer opens
  useEffect(() => {
    if (isOpen) {
      let mounted = true;
      authApi.getCurrentUser().then((user) => {
        if (mounted && user) {
          setProfileData(user);
        }
      });
      return () => {
        mounted = false;
      };
    }
  }, [isOpen]);

  if (!isOpen || !profileData) return null;

  const userRole = profileData.role || "customer";
  const displayName = profileData.full_name || (userRole === "admin" ? "Administrator" : userRole === "employee" ? "Murali" : "Shivu");
  const initial = (displayName || profileData.email || "U")[0].toUpperCase();

  // Eligibility data: prioritize backend profile data, fallback to active assessment prop
  const eligibilityStatus = profileData.eligibility_status || (assessment?.status ? assessment.status : "NOT_STARTED");
  const eligibilityOutcome = profileData.eligibility_outcome || assessment?.outcome || null;
  const assessmentDate = profileData.assessment_completed_at || assessment?.completed_at || assessment?.created_at;

  const formattedAssessmentDate = assessmentDate
    ? new Date(assessmentDate).toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  // Plan & Confirmation data for customer
  const activePlanName = profileData.selected_plan_name || selectedPlan?.plan_name || null;
  const activePlanId = profileData.selected_plan_id || selectedPlan?.plan_id || null;
  const planStatus = profileData.plan_selection_status || (selectedPlan ? "ACTIVE" : "NONE");
  const isConfirmed = Boolean(profileData.is_confirmed || selectedPlan?.status === "CONFIRMED" || selectedPlan?.confirmed_at);
  const confirmationStatus = isConfirmed ? "CONFIRMED" : (selectedPlan ? "PENDING_CONFIRMATION" : "UNSELECTED");
  const confirmationDate = profileData.confirmed_at || selectedPlan?.confirmed_at;

  const formattedConfirmationDate = confirmationDate
    ? new Date(confirmationDate).toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

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
                {profileData.email || "user@example.com"}
              </p>
              <div className="profile-hero-tags">
                <span className={`user-role-tag ${userRole}`}>{userRole}</span>
                <span className="profile-status-tag">
                  <span className="profile-status-dot"></span>
                  {profileData.account_status || (profileData.is_approved ? "Active Session" : "Pending Verification")}
                </span>
              </div>
            </div>
          </div>

          {/* Section: Common Identity & Account Details */}
          <div className="profile-section">
            <h4 className="profile-section-heading">Identity & Account</h4>
            <div className="profile-detail-row">
              <span className="profile-detail-label">Full Name</span>
              <span className="profile-detail-value">{displayName}</span>
            </div>
            <div className="profile-detail-row">
              <span className="profile-detail-label">Email</span>
              <span className="profile-detail-value">{profileData.email}</span>
            </div>
            <div className="profile-detail-row">
              <span className="profile-detail-label">Assigned Role</span>
              <span className="profile-detail-value" style={{ textTransform: "capitalize", fontWeight: 700 }}>
                {userRole}
              </span>
            </div>
            <div className="profile-detail-row">
              <span className="profile-detail-label">Account Status</span>
              <span className="profile-detail-value">
                {profileData.is_approved ? (
                  <span style={{ color: "var(--success-text)", fontWeight: 600 }}>
                    Active & Verified
                  </span>
                ) : (
                  <span style={{ color: "#b45309", fontWeight: 600 }}>
                    Pending Verification
                  </span>
                )}
              </span>
            </div>
          </div>

          {/* Section: Eligibility Status (For Customer & Employee) */}
          {userRole !== "admin" && (
            <div className="profile-section">
              <h4 className="profile-section-heading">Eligibility Underwriting</h4>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Eligibility Status</span>
                <span className="profile-detail-value">
                  {eligibilityStatus === "COMPLETED" ? (
                    <span style={{ color: "var(--success-text)", fontWeight: 700 }}>
                      ✓ Completed
                    </span>
                  ) : (
                    <span style={{ color: "#1D1D1F", fontWeight: 700 }}>
                      Not Completed
                    </span>
                  )}
                </span>
              </div>

              {eligibilityOutcome && (
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Eligibility Result</span>
                  <span
                    className="profile-detail-value"
                    style={{
                      fontWeight: 700,
                      color: eligibilityOutcome === "ELIGIBLE" ? "var(--success-text)" : "#b45309",
                    }}
                  >
                    {eligibilityOutcome}
                  </span>
                </div>
              )}

              {formattedAssessmentDate && (
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Assessment Date</span>
                  <span className="profile-detail-value">{formattedAssessmentDate}</span>
                </div>
              )}
            </div>
          )}

          {/* Section: Plan & Confirmation (Customer and Employee) */}
          {userRole !== "admin" && (
            <div className="profile-section">
              <h4 className="profile-section-heading">Policy Selection & Confirmation</h4>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Selected Plan</span>
                <span className="profile-detail-value" style={{ fontWeight: 700, color: "var(--accent-text)" }}>
                  {activePlanName ? `${activePlanName} (${activePlanId})` : "No Plan Selected"}
                </span>
              </div>

              <div className="profile-detail-row">
                <span className="profile-detail-label">Selection Status</span>
                <span className="profile-detail-value" style={{ fontWeight: 600 }}>
                  {planStatus}
                </span>
              </div>

              <div className="profile-detail-row">
                <span className="profile-detail-label">Final Confirmation</span>
                <span className="profile-detail-value">
                  {isConfirmed ? (
                    <span style={{ color: "var(--success-text)", fontWeight: 700 }}>
                      ✓ Confirmed (Policy Locked)
                    </span>
                  ) : activePlanId ? (
                    <span style={{ color: "#0284c7", fontWeight: 600 }}>
                      Pending Review
                    </span>
                  ) : (
                    <span style={{ color: "#1D1D1F", fontWeight: 600 }}>Pending Selection</span>
                  )}
                </span>
              </div>

              {formattedConfirmationDate && (
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Confirmation Date</span>
                  <span className="profile-detail-value">{formattedConfirmationDate}</span>
                </div>
              )}
            </div>
          )}

          {/* Section: Employee-Specific Details */}
          {userRole === "employee" && (
            <div className="profile-section">
              <h4 className="profile-section-heading">Corporate Staff Authorization</h4>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Authorized Plan</span>
                <span className="profile-detail-value" style={{ fontWeight: 700, color: "var(--accent-text)" }}>
                  Executive Employee Insurance Plan (EMP-INS-001)
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Staff Verification</span>
                <span className="profile-detail-value" style={{ color: "var(--success-text)", fontWeight: 600 }}>
                  Authorized Corporate Employee
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Scope Access</span>
                <span className="profile-detail-value">Eligibility, Staff Chat & Document Search</span>
              </div>
            </div>
          )}

          {/* Section: Admin-Specific Details */}
          {userRole === "admin" && (
            <div className="profile-section">
              <h4 className="profile-section-heading">Administrator Governance</h4>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Admin Identity</span>
                <span className="profile-detail-value" style={{ fontWeight: 700 }}>
                  {displayName}
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Workspace Access</span>
                <span className="profile-detail-value" style={{ color: "var(--success-text)", fontWeight: 700 }}>
                  Full Access (Dashboard & Ingestion)
                </span>
              </div>
              <div className="profile-detail-row">
                <span className="profile-detail-label">Governance Mode</span>
                <span className="profile-detail-value">System Administrator</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer with Proper Liquid Glass Logout Button */}
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
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  );
}

export default ProfileDrawer;
