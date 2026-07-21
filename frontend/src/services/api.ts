import type { AnalysisResult } from '../types/analysis';
import { getApiBaseUrl } from '../config/appConfig';

const DEFAULT_TIMEOUT_MS = 120_000;

async function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out — check that the backend is running.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export interface AnalyzeChartsPayload {
  pair?: string;
  timeframeHtf?: string;
  timeframeMtf?: string;
  timeframeLtf?: string;
  chart4hUri: string;
  chart1hUri: string;
  chart15mUri: string;
}

export interface MemoryStats {
  total_trades_stored: number;
  winning_trades: number;
  losing_trades: number;
  waiting_trades: number;
  estimated_win_rate: number | null;
  most_successful_pair: string | null;
  most_successful_timeframe_alignment: string | null;
  most_successful_feature_combination: {
    pattern: string;
    wins: number;
    trades?: number;
  } | null;
  most_common_losing_pattern: {
    pattern: string;
    losses: number;
    trades?: number;
  } | null;
  total_memories_stored: number;
  last_learning_update: string;
  top_patterns?: Array<{
    pattern: string;
    trades: number;
    wins: number;
    losses: number;
    win_rate: number | null;
    average_rr: number | null;
  }>;
  grade_distribution?: Record<string, number>;
  adaptive_weights?: Record<string, number>;
  feature_performance?: Array<{
    feature: string;
    wins: number;
    losses: number;
    total: number;
    win_rate: number | null;
  }>;
}

export async function healthCheck(): Promise<{ ok: boolean; version?: string; detail?: string }> {
  try {
    const base = await getApiBaseUrl();
    const response = await fetchWithTimeout(`${base}/api/health`, {}, 8_000);
    if (!response.ok) {
      return { ok: false, detail: `HTTP ${response.status}` };
    }
    const body = (await response.json()) as { version?: string; status?: string };
    return { ok: true, version: body.version };
  } catch (error) {
    return {
      ok: false,
      detail: error instanceof Error ? error.message : 'unreachable',
    };
  }
}

export async function analyzeCharts(payload: AnalyzeChartsPayload): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append('pair', payload.pair ?? 'EURUSD');
  formData.append('timeframe_htf', payload.timeframeHtf ?? '4H');
  formData.append('timeframe_mtf', payload.timeframeMtf ?? '1H');
  formData.append('timeframe_ltf', payload.timeframeLtf ?? '15M');
  formData.append('chart_4h', {
    uri: payload.chart4hUri,
    name: 'chart_4h.jpg',
    type: 'image/jpeg',
  } as unknown as Blob);
  formData.append('chart_1h', {
    uri: payload.chart1hUri,
    name: 'chart_1h.jpg',
    type: 'image/jpeg',
  } as unknown as Blob);
  formData.append('chart_15m', {
    uri: payload.chart15mUri,
    name: 'chart_15m.jpg',
    type: 'image/jpeg',
  } as unknown as Blob);

  const base = await getApiBaseUrl();
  const response = await fetchWithTimeout(`${base}/api/analyze`, {
    method: 'POST',
    body: formData,
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Analysis failed with status ${response.status}`);
  }

  return (await response.json()) as AnalysisResult;
}

export async function submitTradeOutcome(payload: {
  tradeId: string;
  outcome: 'TAKE_PROFIT' | 'STOP_LOSS' | 'BREAK_EVEN';
  resultChartUri: string;
  comments?: string;
  rrAchieved?: string;
}): Promise<{
  lesson: string;
  lessons?: string[];
  status: string;
  grade?: string;
  grade_label?: string;
  scorecard?: Record<string, number>;
  critique?: { strengths: string[]; weaknesses: string[]; improvements: string[] };
  review_summary?: string;
  pattern?: { pattern: string; trades: number; wins: number; losses: number; win_rate: number | null };
}> {
  const formData = new FormData();
  formData.append('outcome', payload.outcome);
  if (payload.comments) formData.append('comments', payload.comments);
  if (payload.rrAchieved) formData.append('rr_achieved', payload.rrAchieved);
  formData.append('result_chart', {
    uri: payload.resultChartUri,
    name: 'result.jpg',
    type: 'image/jpeg',
  } as unknown as Blob);

  const base = await getApiBaseUrl();
  const response = await fetchWithTimeout(
    `${base}/api/trades/${encodeURIComponent(payload.tradeId)}/outcome`,
    {
      method: 'POST',
      body: formData,
      headers: { Accept: 'application/json' },
    },
  );

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Outcome submit failed (${response.status})`);
  }

  return await response.json();
}

export async function fetchMemoryStats(): Promise<MemoryStats> {
  const base = await getApiBaseUrl();
  const response = await fetchWithTimeout(`${base}/api/memory/stats`, {}, 30_000);
  if (!response.ok) {
    throw new Error(`Memory stats failed (${response.status})`);
  }
  return (await response.json()) as MemoryStats;
}

export interface ResearchDashboard {
  total_analyses: number;
  trades_awaiting_results: number;
  completed_reviews: number;
  current_confidence_calibration: {
    global_gap: number;
    sample_count: number;
    adjustment_factor: number;
    notes: string[];
    bins?: Array<{
      bin_label: string;
      predictions: number;
      successes: number;
      realized_rate: number | null;
      calibration_gap: number | null;
    }>;
  } | null;
  most_reliable_feature_combination: {
    pattern_id: string;
    feature_combination: string[];
    occurrences: number;
    wins: number;
    losses: number;
    reliability_score: number | null;
  } | null;
  least_reliable_feature_combination: {
    pattern_id: string;
    feature_combination: string[];
    occurrences: number;
    wins: number;
    losses: number;
    reliability_score: number | null;
  } | null;
  most_common_reason_for_losing_trades: string | null;
  most_common_reason_for_no_trade: string | null;
  recent_lessons: string[];
  decision_quality_distribution: Record<string, number>;
  top_patterns?: Array<{
    pattern_id: string;
    feature_combination: string[];
    occurrences: number;
    wins: number;
    losses: number;
    reliability_score: number | null;
  }>;
  memory_snapshot?: {
    total_trades_stored?: number;
    winning_trades?: number;
    losing_trades?: number;
    waiting_trades?: number;
    estimated_win_rate?: number | null;
    most_successful_pair?: string | null;
    last_learning_update?: string;
  };
  learning_snapshot?: {
    adaptive_weights?: Record<string, number>;
    feature_reliability?: Array<{
      feature: string;
      wins: number;
      losses: number;
      total: number;
      win_rate: number | null;
    }>;
  };
  notes: string[];
}

export interface EvaluationDashboard {
  total_analyses: number;
  completed_reviews: number;
  current_calibration_quality: string;
  most_reliable_feature: string | null;
  least_reliable_feature: string | null;
  common_no_trade_reasons: string[];
  recent_lessons: string[];
  overall_system_health: {
    overall_grade: string;
    overall_score: number;
    modules: Array<{ module: string; grade: string; score: number; notes: string[] }>;
  } | null;
  latest_report_id: string | null;
  decision_path_log_count: number;
}

export async function fetchResearchDashboard(): Promise<ResearchDashboard> {
  const base = await getApiBaseUrl();
  const response = await fetchWithTimeout(`${base}/api/research/dashboard`, {}, 30_000);
  if (!response.ok) {
    throw new Error(`Research dashboard failed (${response.status})`);
  }
  return (await response.json()) as ResearchDashboard;
}

export async function fetchEvaluationDashboard(): Promise<EvaluationDashboard> {
  const base = await getApiBaseUrl();
  const response = await fetchWithTimeout(`${base}/api/evaluation/dashboard`, {}, 30_000);
  if (!response.ok) {
    throw new Error(`Evaluation dashboard failed (${response.status})`);
  }
  return (await response.json()) as EvaluationDashboard;
}

export { getApiBaseUrl };
