import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { CompositeNavigationProp, RouteProp } from '@react-navigation/native';
import type { AnalysisResult } from '../types/analysis';

export type MainTabParamList = {
  Scan: undefined;
  Analysis: undefined;
  History: undefined;
  Insights: undefined;
  Settings: undefined;
};

export type RootStackParamList = {
  Splash: undefined;
  MainTabs: { screen?: keyof MainTabParamList } | undefined;
  Analyzing: {
    chart4hUri: string;
    chart1hUri: string;
    chart15mUri: string;
    pair?: string;
    timeframeHtf?: string;
    timeframeMtf?: string;
    timeframeLtf?: string;
  };
  Results: {
    tradeId: string;
    analysis: AnalysisResult;
  };
  TradeDetails: {
    tradeId: string;
  };
  UploadOutcome: {
    tradeId: string;
  };
  Memory: undefined;
  /** @deprecated Use MainTabs — kept for deep-link compatibility during transition */
  Home: undefined;
  History: undefined;
};

export type RootNavigationProp = NativeStackNavigationProp<RootStackParamList>;

export type TabNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList>,
  NativeStackNavigationProp<RootStackParamList>
>;

export type AnalyzingRouteProp = RouteProp<RootStackParamList, 'Analyzing'>;
export type ResultsRouteProp = RouteProp<RootStackParamList, 'Results'>;
export type TradeDetailsRouteProp = RouteProp<RootStackParamList, 'TradeDetails'>;
export type UploadOutcomeRouteProp = RouteProp<RootStackParamList, 'UploadOutcome'>;
