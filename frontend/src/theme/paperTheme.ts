import { MD3DarkTheme } from 'react-native-paper';
import { colors } from './colors';

export const paperTheme = {
  ...MD3DarkTheme,
  dark: true,
  roundness: 14,
  colors: {
    ...MD3DarkTheme.colors,
    primary: colors.primary,
    secondary: colors.secondary,
    background: colors.background,
    surface: colors.surface,
    surfaceVariant: colors.surfaceElevated,
    onPrimary: colors.white,
    onSecondary: colors.white,
    onBackground: colors.text,
    onSurface: colors.text,
    onSurfaceVariant: colors.textSecondary,
    outline: colors.surfaceBorder,
    error: colors.danger,
    elevation: {
      level0: colors.background,
      level1: colors.surface,
      level2: colors.surfaceElevated,
      level3: colors.card,
      level4: colors.card,
      level5: colors.card,
    },
  },
};
