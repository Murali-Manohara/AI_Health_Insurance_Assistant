import React from 'react';

/**
 * GlassFilter — SVG distortion and blur filter matching code.txt reference.
 * Provides the optical liquid glass refraction filter when needed.
 */
export function GlassFilter() {
  return (
    <svg className="liquid-glass-svg-defs" aria-hidden="true" style={{ position: 'absolute', width: 0, height: 0, overflow: 'hidden' }}>
      <defs>
        <filter
          id="container-glass"
          x="0%"
          y="0%"
          width="100%"
          height="100%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.05 0.05"
            numOctaves="1"
            seed="1"
            result="turbulence"
          />
          <feGaussianBlur in="turbulence" stdDeviation="2" result="blurredNoise" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="blurredNoise"
            scale="70"
            xChannelSelector="R"
            yChannelSelector="B"
            result="displaced"
          />
          <feGaussianBlur in="displaced" stdDeviation="4" result="finalBlur" />
          <feComposite in="finalBlur" in2="finalBlur" operator="over" />
        </filter>
      </defs>
    </svg>
  );
}

/**
 * LiquidButton — Apple-inspired Liquid Glass & Metal Button component.
 * Direct implementation of the reference in code.txt adapted for clean React + Vanilla CSS.
 * 
 * Variants:
 * - 'primary' (default): Solid #007AFF Apple blue with specular highlight, multi-layer depth shadow
 * - 'secondary': Translucent white glass with visible border, dark text, and subtle hover tint
 * - 'cool': Multi-layer liquid glass with specular inner reflection and spring physics
 * - 'icon': Circular or square icon hit-area button with centered icon and liquid hover glow
 * 
 * Sizes:
 * - 'sm': Compact 32px height
 * - 'default': Standard 38px height
 * - 'lg': Prominent 44px height
 * - 'icon': 38x38px circular/rounded hit target
 */
export const LiquidButton = React.forwardRef(function LiquidButton(
  {
    children,
    className = '',
    variant = 'primary',
    size = 'default',
    disabled = false,
    onClick,
    type = 'button',
    title,
    'aria-label': ariaLabel,
    style,
    ...props
  },
  ref
) {
  const [isPressed, setIsPressed] = React.useState(false);
  const [isHovered, setIsHovered] = React.useState(false);

  const variantClass = `liquid-btn-${variant}`;
  const sizeClass = `liquid-btn-size-${size}`;
  const pressedClass = isPressed ? 'is-pressed' : '';
  const hoveredClass = isHovered && !disabled ? 'is-hovered' : '';

  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      aria-label={ariaLabel}
      className={`liquid-btn ${variantClass} ${sizeClass} ${pressedClass} ${hoveredClass} ${className}`.trim()}
      style={style}
      onMouseDown={() => !disabled && setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onMouseLeave={() => {
        setIsPressed(false);
        setIsHovered(false);
      }}
      onMouseEnter={() => !disabled && setIsHovered(true)}
      onTouchStart={() => !disabled && setIsPressed(true)}
      onTouchEnd={() => setIsPressed(false)}
      onTouchCancel={() => setIsPressed(false)}
      {...props}
    >
      {/* Specular Top Shine Layer */}
      <span className="liquid-btn-specular-shine" aria-hidden="true" />

      {/* Button Content */}
      <span className="liquid-btn-content">
        {children}
      </span>
    </button>
  );
});

LiquidButton.displayName = 'LiquidButton';

export default LiquidButton;
