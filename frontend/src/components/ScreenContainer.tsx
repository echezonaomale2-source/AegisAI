import React from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';

interface ScreenContainerProps {
  children: React.ReactNode;
  style?: ViewStyle;
  edges?: Array<'top' | 'right' | 'bottom' | 'left'>;
}

export function ScreenContainer({
  children,
  style,
  edges = ['top', 'left', 'right', 'bottom'],
}: ScreenContainerProps) {
  return (
    <SafeAreaView style={styles.safe} edges={edges}>
      <View style={[styles.inner, style]}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  inner: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: 20,
  },
});
