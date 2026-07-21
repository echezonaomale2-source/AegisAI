export const colors = {
  background: '#08080C',
  surface: '#101016',
  surfaceElevated: '#16161E',
  surfaceBorder: '#2A2A36',
  card: '#12121A',
  cardHover: '#1A1A24',

  // Primary CTA — electric violet (mockup Analyze / Submit)
  primary: '#7C5CFF',
  primaryMuted: '#6346E8',
  primaryDim: 'rgba(124, 92, 255, 0.16)',
  primaryGlow: 'rgba(124, 92, 255, 0.45)',

  // Secondary accent — blue edge of gradient
  secondary: '#4F7CFF',
  secondaryMuted: '#3A63E0',
  secondaryDim: 'rgba(79, 124, 255, 0.14)',

  // Bullish / success — neon green
  success: '#2EE59D',
  successDim: 'rgba(46, 229, 157, 0.14)',
  buy: '#2EE59D',

  // Bearish / danger
  danger: '#FF4D6A',
  dangerDim: 'rgba(255, 77, 106, 0.14)',
  sell: '#FF4D6A',

  warning: '#F5B942',
  warningDim: 'rgba(245, 185, 66, 0.14)',
  neutral: '#6B7280',
  noTrade: '#8B92A8',

  text: '#F4F5F7',
  textSecondary: '#A0A6B8',
  textMuted: '#6B7280',

  tipBg: 'rgba(46, 229, 157, 0.08)',
  tipBorder: 'rgba(46, 229, 157, 0.35)',

  tabBar: '#0C0C12',
  tabInactive: '#5C6378',

  overlay: 'rgba(0, 0, 0, 0.78)',
  white: '#FFFFFF',
  black: '#000000',
} as const;

export type AppColors = typeof colors;
