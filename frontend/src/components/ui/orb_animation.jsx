// Thinking Orbs — an animated thinking/agent orb.
//
// Six hand-tuned canvas animations, each a distinct state:
//   working · searching · solving · listening · composing · shaping
// Two tuned size presets ship: 64 (chat-avatar scale) and 20 (inline-text
// scale) — each carries its own dot count / dot size / speed tuning.
//
// Theme-aware: `theme="auto"` (default) resolves from a `data-theme` / `dark`
// class on any ancestor, else `prefers-color-scheme`, live-updating on change;
// `dark` / `light` pin the palette. SSR-safe — the canvas is client-only.
//
// Source & playground: https://orbs.jakubantalik.com
import React, { useState, useEffect, Component } from "react"
import { ThinkingOrb } from "thinking-orbs"

export { ThinkingOrb } from "thinking-orbs"

/**
 * Crash-safe Error Boundary for Canvas ThinkingOrb.
 * Ensures that if any canvas or preset resolution issue occurs,
 * the UI smoothly falls back to an elegant glowing pulse orb
 * without ever turning the screen white.
 */
class SafeThinkingOrbBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.warn("ThinkingOrb encountered render issue, using fallback orb:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="naked-thinking-fallback-orb"
          style={{
            width: 51,
            height: 51,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(0, 122, 255, 0.95) 0%, rgba(0, 122, 255, 0.45) 55%, transparent 75%)',
            boxShadow: '0 0 12px rgba(0, 122, 255, 0.45)',
            animation: 'thinkingPulse 1.6s ease-in-out infinite'
          }}
        />
      );
    }
    return this.props.children;
  }
}

/**
 * LiquidThinkingOrb — 12-second containerless thinking indicator (3 seconds per step).
 * Uses theme blue (#007AFF) composing orb with bold black status text.
 * Modes:
 *   - "rag":
 *       0s - 3s: "Understanding your query"
 *       3s - 6s: "Searching for relevant documents"
 *       6s - 9s: "Checking the evidence"
 *       9s - 12s: "Generating the answer"
 *   - "claim":
 *       0s - 3s: "Understanding your inputs"
 *       3s - 6s: "Preparing the prediction"
 *       6s - 9s: "Calculating the claim estimate"
 *       9s - 12s: "Preparing your results"
 */
export function LiquidThinkingOrb({ size = 51, color = "#007AFF", theme = "auto", mode = "rag" }) {
  const [phaseIndex, setPhaseIndex] = useState(0);

  // The thinking-orbs library only accepts preset sizes: 64, 32, or 20.
  // Using 64 gives the highest dot count and rendering fidelity,
  // which is styled to 51px by CSS/canvas dimensions.
  const validPresets = [64, 32, 20];
  const orbPresetSize = validPresets.includes(size) ? size : 64;

  useEffect(() => {
    setPhaseIndex(0);
    const t1 = setTimeout(() => setPhaseIndex(1), 3000);
    const t2 = setTimeout(() => setPhaseIndex(2), 6000);
    const t3 = setTimeout(() => setPhaseIndex(3), 9000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [mode]);

  const ragPhases = [
    { text: "Understanding your query" },
    { text: "Searching for relevant documents" },
    { text: "Checking the evidence" },
    { text: "Generating the answer" }
  ];

  const claimPhases = [
    { text: "Understanding your inputs" },
    { text: "Preparing the prediction" },
    { text: "Calculating the claim estimate" },
    { text: "Preparing your results" }
  ];

  const phases = mode === "claim" ? claimPhases : ragPhases;
  const current = phases[phaseIndex] || phases[0];

  return (
    <div className="naked-thinking-wrapper" role="status" aria-live="polite">
      <div className="naked-thinking-orb-canvas" style={{ width: 51, height: 51 }}>
        <SafeThinkingOrbBoundary>
          <ThinkingOrb
            state="composing"
            size={orbPresetSize}
            color={color}
            theme={theme}
            style={{ width: 51, height: 51 }}
          />
        </SafeThinkingOrbBoundary>
      </div>
      <div className="naked-thinking-text-group">
        <span className="naked-thinking-label">
          {current.text}
        </span>
        <span className="naked-thinking-dots">
          <span>.</span><span>.</span><span>.</span>
        </span>
      </div>
    </div>
  );
}

export default ThinkingOrb
