export type StrategyAction =
  | "long_target"
  | "short_target"
  | "hold"
  | "unavailable";

export type ModelQuality = "strong" | "moderate" | "weak";

export interface PeerGroupMember {
  ticker: string;
  name: string;
}

export interface PeerGroup {
  id: string;
  name: string;
  sector: string;
  members: PeerGroupMember[];
}

export interface StrategyUniversesResponse {
  version: number;
  groups: PeerGroup[];
  limits: {
    minimum_tickers: number;
    maximum_tickers: number;
  };
  methodology_note: string;
}

export interface PeerWeight {
  ticker: string;
  weight: number;
}

export interface BasketSignal {
  target: string;
  peers: string[];
  as_of?: string;
  action: StrategyAction;
  zscore: number | null;
  formation_window?: number;
  observation_count?: number;
  hedge_beta: number | null;
  peer_weights: PeerWeight[];
  r_squared: number | null;
  adf_pvalue: number | null;
  ar1_coefficient?: number | null;
  half_life_days: number | null;
  model_quality: ModelQuality;
  cautions: string[];
  methodology_note?: string;
}

export interface StrategyDataQuality {
  observation_count: number;
  first_date: string;
  latest_date: string;
  warnings: string[];
}

export interface StrategyScanResponse {
  strategy_version: string;
  tickers: string[];
  as_of: string;
  candidates: BasketSignal[];
  data_quality: StrategyDataQuality;
  parameters: {
    formation_window: number;
    rebalance_sessions: number;
    entry_z: number;
    exit_z: number;
  };
}

export interface PerformanceMetrics {
  total_return: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  sharpe: number | null;
  max_drawdown: number | null;
}

export interface BacktestSummary extends PerformanceMetrics {
  final_equity: number | null;
  benchmark_return: number | null;
  trade_count: number;
  win_rate: number | null;
  average_holding_sessions: number | null;
  turnover: number | null;
  holdout: PerformanceMetrics;
}

export interface EquityPoint {
  date: string;
  equity: number | null;
  benchmark: number | null;
  drawdown: number | null;
  position: -1 | 0 | 1;
}

export interface ResidualPoint {
  date: string;
  residual_return: number | null;
  residual_state: number | null;
  equilibrium_mean: number | null;
  entry_upper: number | null;
  entry_lower: number | null;
}

export interface StrategyTrade {
  signal_date: string;
  entry_date: string;
  exit_date: string;
  direction: "long_target" | "short_target";
  entry_zscore: number | null;
  exit_zscore: number | null;
  exit_reason: string;
  holding_sessions: number;
  gross_pnl: number | null;
  net_pnl: number | null;
  transaction_cost: number;
  borrow_cost: number;
}

export interface SensitivityResult {
  formation_window: number;
  status: "available" | "unavailable";
  summary?: BacktestSummary;
  error?: string;
}

export interface StrategyBacktestResponse {
  strategy_version: string;
  target: string;
  peers: string[];
  as_of: string;
  formation_window: number;
  current_signal: BasketSignal;
  summary: BacktestSummary;
  costs: {
    transaction_cost: number | null;
    borrow_cost: number | null;
    total: number | null;
    transaction_cost_bps: number;
    annual_borrow_rate: number;
  };
  config: {
    initial_capital: number;
    gross_exposure: number;
    transaction_cost_bps: number;
    annual_borrow_rate: number;
    participation_rate: number;
    rebalance_sessions: number;
    entry_z: number;
    exit_z: number;
    stop_z: number;
    execution: string;
  };
  data_quality: StrategyDataQuality;
  methodology_note: string;
  equity_curve: EquityPoint[];
  residual_series: ResidualPoint[];
  trades: StrategyTrade[];
  sensitivity: SensitivityResult[];
  capacity_warnings: string[];
}
