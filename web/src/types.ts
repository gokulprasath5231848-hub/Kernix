import { RiskClass } from './constants';

export interface Process {
  id: string;
  name: string;
  department: string;
  cases_per_month: number;
  steps: number;
  systems_touched: number;
  systems: string[];
  created_at: string;
}

export interface Score {
  id: string;
  process_id: string;
  frequency_volume: number;
  manual_time: number;
  rule_determinism: number;
  api_readiness: number;
  exception_frequency: number;
  privacy_risk: number;
  value_score: number;
  sensitive_outcome: number;
  fully_rule_based: number;
  risk_decision: RiskClass;
  reason: string;
  scored_at: string;
}

export interface ProcessListItem extends Process {
  score: Score;
  rank: number;
}

export interface EventItem {
  id: string;
  case_id: string;
  activity_raw: string;
  activity_normalised: string;
  event_time: string;
  actor_masked: string;
  system: string;
  confidence: number;
}

export interface BlueprintStep {
  name: string;
  description: string;
  system: string;
  requires_approval: boolean;
  approval_condition?: string;
}

export interface Blueprint {
  id: string;
  process_id: string;
  steps: BlueprintStep[];
  trigger: string;
  estimated_savings_hours: number;
  generated_at: string;
}

export interface ProcessDetail extends ProcessListItem {
  evidence_trail: EventItem[];
}

export interface WeightsConfig {
  id: string;
  weights: Record<string, number>;
  effective_from: string;
  set_by: string;
}

export interface AuditEntry {
  id: string;
  process_id: string;
  action: string;
  actor: string;
  detail: string;
  timestamp: string;
}
