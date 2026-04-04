export interface Game {
  game_id: string;
  home_team: string;
  home_team_id: number;
  away_team: string;
  away_team_id: number;
  home_abbr: string;
  away_abbr: string;
}

export interface Prediction {
  player_name: string;
  team: string;
  opponent: string;
  stat_type: "Points" | "Rebounds" | "Assists";
  predicted: number;
  line: number | null;
  edge: number | null;
  direction: "OVER" | "UNDER" | null;
  confidence: number | null;
  bettable?: boolean;
  odds_type?: string;
  bookmaker: string | null;
  key_factors: string[];
  last_5_games: number[];
  avg_last_5: number;
  season_avg: number;
}

export interface ParlayPick {
  player_name: string;
  team: string;
  opponent: string;
  stat_type: string;
  stat_abbr: string;
  direction: string;
  line: number;
  predicted: number;
  edge: number;
  confidence: number;
}

export interface Parlay {
  strategy: string;
  size: number;
  picks: ParlayPick[];
  all_hit_probability: number;
  power_payout: string;
  flex_payouts: Record<string, string>;
  expected_value: number;
  power_ev: number;
  flex_ev: number;
  recommended_play: "Power" | "Flex";
}

export interface PredictionsResponse {
  games: Game[];
  points: Prediction[];
  rebounds: Prediction[];
  assists: Prediction[];
  parlays: Parlay[];
  predictions_count?: number;
  message?: string;
  error?: string;
}

export interface RecordOverall {
  total: number;
  wins: number;
  losses: number;
  win_pct: number;
  pending: number;
  days_tracked: number;
}

export interface StatRecord {
  stat_type: string;
  total: number;
  wins: number;
  win_pct: number;
}

export interface DayRecord {
  date: string;
  total: number;
  wins: number;
  win_pct: number;
}

export interface ConfidenceTier {
  tier: string;
  total: number;
  wins: number;
  win_pct: number;
}

export interface RecordResponse {
  overall: RecordOverall;
  by_stat: StatRecord[];
  by_confidence: ConfidenceTier[];
  recent_days: DayRecord[];
  pending_dates: string[];
}

export interface HistoryEntry {
  id: number;
  date: string;
  player_name: string;
  team: string;
  opponent: string;
  stat_type: string;
  predicted: number;
  line: number;
  direction: string;
  edge: number;
  confidence: number;
  actual: number | null;
  correct: number | null;
}

export type TabType = "points" | "rebounds" | "assists" | "parlays" | "record";
