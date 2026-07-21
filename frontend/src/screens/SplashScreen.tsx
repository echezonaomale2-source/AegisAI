import React, { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../navigation/types';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';
import { getDatabase } from '../storage/database';

type Props = NativeStackScreenProps<RootStackParamList, 'Splash'>;

export function SplashScreen({ navigation }: Props) {
  const opacity = useSharedValue(0);
  const scale = useSharedValue(0.92);
  const lineWidth = useSharedValue(0);

  useEffect(() => {
    const bootstrap = async () => {
      await getDatabase();
      opacity.value = withTiming(1, { duration: 700, easing: Easing.out(Easing.cubic) });
      scale.value = withTiming(1, { duration: 700, easing: Easing.out(Easing.cubic) });
      lineWidth.value = withDelay(
        250,
        withTiming(140, { duration: 600, easing: Easing.out(Easing.cubic) }),
      );

      setTimeout(() => {
        navigation.replace('MainTabs');
      }, 1800);
    };

    void bootstrap();
  }, [lineWidth, navigation, opacity, scale]);

  const brandStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ scale: scale.value }],
  }));

  const lineStyle = useAnimatedStyle(() => ({
    width: lineWidth.value,
    opacity: opacity.value,
  }));

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#12081F', colors.background, '#061018']}
        style={StyleSheet.absoluteFill}
      />
      <Animated.View style={[styles.brandWrap, brandStyle]}>
        <Text style={styles.brand}>AegisAI</Text>
        <Animated.View style={[styles.line, lineStyle]} />
        <Text style={styles.tagline}>Personal Smart Money Assistant</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandWrap: {
    alignItems: 'center',
  },
  brand: {
    color: colors.white,
    fontFamily: fonts.display,
    fontSize: 44,
    letterSpacing: 1.4,
  },
  line: {
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.primary,
    marginVertical: 16,
  },
  tagline: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 14,
    letterSpacing: 0.4,
  },
});
