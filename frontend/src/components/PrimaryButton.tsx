import React from 'react';
import { StyleSheet } from 'react-native';
import { Button } from 'react-native-paper';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

interface PrimaryButtonProps {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  mode?: 'contained' | 'outlined' | 'text';
  color?: string;
}

export function PrimaryButton({
  label,
  onPress,
  disabled = false,
  loading = false,
  mode = 'contained',
  color = colors.primary,
}: PrimaryButtonProps) {
  return (
    <Button
      mode={mode}
      onPress={onPress}
      disabled={disabled || loading}
      loading={loading}
      buttonColor={mode === 'contained' ? color : undefined}
      textColor={mode === 'contained' ? colors.white : color}
      style={[styles.button, mode === 'outlined' && { borderColor: color }]}
      contentStyle={styles.content}
      labelStyle={styles.label}
    >
      {label}
    </Button>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  content: {
    minHeight: 52,
  },
  label: {
    fontFamily: fonts.bodyBold,
    fontSize: 14,
    letterSpacing: 0.6,
  },
});
