import React from 'react';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { RootStackParamList } from './types';
import { MainTabs } from './MainTabs';
import { SplashScreen } from '../screens/SplashScreen';
import { AnalyzingScreen } from '../screens/AnalyzingScreen';
import { ResultsScreen } from '../screens/ResultsScreen';
import { TradeDetailsScreen } from '../screens/TradeDetailsScreen';
import { UploadOutcomeScreen } from '../screens/UploadOutcomeScreen';
import { MemoryScreen } from '../screens/MemoryScreen';
import { colors } from '../theme/colors';

const Stack = createNativeStackNavigator<RootStackParamList>();

const navTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.background,
    card: colors.background,
    text: colors.text,
    border: colors.surfaceBorder,
    primary: colors.primary,
  },
};

export function RootNavigator() {
  return (
    <NavigationContainer theme={navTheme}>
      <Stack.Navigator
        initialRouteName="Splash"
        screenOptions={{
          headerShown: false,
          animation: 'fade',
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="Splash" component={SplashScreen} />
        <Stack.Screen name="MainTabs" component={MainTabs} />
        <Stack.Screen name="Analyzing" component={AnalyzingScreen} />
        <Stack.Screen name="Results" component={ResultsScreen} />
        <Stack.Screen name="TradeDetails" component={TradeDetailsScreen} />
        <Stack.Screen name="UploadOutcome" component={UploadOutcomeScreen} />
        <Stack.Screen name="Memory" component={MemoryScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
