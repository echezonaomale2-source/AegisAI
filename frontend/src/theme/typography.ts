export const fonts = {
  display: 'SpaceGrotesk_700Bold',
  displayMedium: 'SpaceGrotesk_600SemiBold',
  displayRegular: 'SpaceGrotesk_500Medium',
  body: 'DMSans_400Regular',
  bodyMedium: 'DMSans_500Medium',
  bodyBold: 'DMSans_700Bold',
} as const;

export const typography = {
  hero: {
    fontFamily: fonts.display,
    fontSize: 34,
    letterSpacing: -0.5,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 24,
    letterSpacing: -0.3,
  },
  subtitle: {
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 20,
  },
  section: {
    fontFamily: fonts.displayMedium,
    fontSize: 16,
    letterSpacing: 0.2,
  },
  label: {
    fontFamily: fonts.bodyMedium,
    fontSize: 12,
    letterSpacing: 0.4,
  },
  body: {
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 20,
  },
  button: {
    fontFamily: fonts.bodyBold,
    fontSize: 15,
    letterSpacing: 0.8,
  },
} as const;
