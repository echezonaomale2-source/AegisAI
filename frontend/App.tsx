import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { useFonts } from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { RootNavigator } from './src/navigation/RootNavigator';
import { paperTheme } from './src/theme/paperTheme';
import { colors } from './src/theme/colors';

export default function App() {
  const [fontsReady] = useFonts({
    SpaceGrotesk_500Medium: require('./assets/fonts/SpaceGrotesk_500Medium.ttf'),
    SpaceGrotesk_600SemiBold: require('./assets/fonts/SpaceGrotesk_600SemiBold.ttf'),
    SpaceGrotesk_700Bold: require('./assets/fonts/SpaceGrotesk_700Bold.ttf'),
    DMSans_400Regular: require('./assets/fonts/DMSans_400Regular.ttf'),
    DMSans_500Medium: require('./assets/fonts/DMSans_500Medium.ttf'),
    DMSans_700Bold: require('./assets/fonts/DMSans_700Bold.ttf'),
  });

  if (!fontsReady) {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.primary} size="large" />
        <StatusBar style="light" />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <PaperProvider theme={paperTheme}>
          <StatusBar style="light" />
          <RootNavigator />
        </PaperProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background,
  },
  boot: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
