import React from 'react';
import { StyleSheet, View } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import type { MainTabParamList } from './types';
import { HomeScreen } from '../screens/HomeScreen';
import { AnalysisHubScreen } from '../screens/AnalysisHubScreen';
import { HistoryScreen } from '../screens/HistoryScreen';
import { ResearchScreen } from '../screens/ResearchScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

const Tab = createBottomTabNavigator<MainTabParamList>();

type IconName = keyof typeof Ionicons.glyphMap;

function tabIcon(name: IconName, focusedName: IconName) {
  return ({ focused, color, size }: { focused: boolean; color: string; size: number }) => (
    <View style={focused ? styles.iconActive : undefined}>
      <Ionicons name={focused ? focusedName : name} size={size} color={color} />
    </View>
  );
}

export function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarLabelStyle: styles.tabLabel,
        tabBarHideOnKeyboard: true,
      }}
    >
      <Tab.Screen
        name="Scan"
        component={HomeScreen}
        options={{
          title: 'Scan',
          tabBarIcon: tabIcon('scan-outline', 'scan'),
        }}
      />
      <Tab.Screen
        name="Analysis"
        component={AnalysisHubScreen}
        options={{
          title: 'Analysis',
          tabBarIcon: tabIcon('analytics-outline', 'analytics'),
        }}
      />
      <Tab.Screen
        name="History"
        component={HistoryScreen}
        options={{
          title: 'History',
          tabBarIcon: tabIcon('time-outline', 'time'),
        }}
      />
      <Tab.Screen
        name="Insights"
        component={ResearchScreen}
        options={{
          title: 'Insights',
          tabBarIcon: tabIcon('bulb-outline', 'bulb'),
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: 'Settings',
          tabBarIcon: tabIcon('settings-outline', 'settings'),
        }}
      />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.tabBar,
    borderTopColor: colors.surfaceBorder,
    borderTopWidth: 1,
    height: 64,
    paddingBottom: 8,
    paddingTop: 6,
  },
  tabLabel: {
    fontFamily: fonts.bodyMedium,
    fontSize: 11,
  },
  iconActive: {
    shadowColor: colors.primary,
    shadowOpacity: 0.55,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 0 },
  },
});
