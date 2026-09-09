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

// ---------------------------------------------------------------------------
// Automation Blueprints catalog
// ---------------------------------------------------------------------------

export interface BlueprintCatalogItem {
  process_id: string;
  process_name: string;
  department: string | null;
  risk_decision: RiskClass;
  value_score: number;
  blueprint_id: string | null;
  generated_at: string | null;
  estimated_savings_hours: number | null;
  status: 'Blocked' | 'Not Generated' | 'Draft' | 'Awaiting Approval';
}

// ---------------------------------------------------------------------------
// Agentic execution
// ---------------------------------------------------------------------------

export type AgentStepType =
  | 'plan'
  | 'tool_call'
  | 'observation'
  | 'blocked'
  | 'final';

export type AgentRunStatus =
  | 'COMPLETED'
  | 'AWAITING_HUMAN_APPROVAL'
  | 'REFUSED'
  | 'FAILED'
  | 'MAX_STEPS_REACHED';

export interface AgentTraceStep {
  seq: number;
  type: AgentStepType;
  tool: string | null;
  args: Record<string, unknown> | null;
  content: string;
  blocked: boolean;
}

export interface AgentRunResult {
  process_id: string;
  process_name: string;
  risk_decision: RiskClass;
  engine: string;
  status: AgentRunStatus;
  summary: string;
  trace: AgentTraceStep[];
}

// ---------------------------------------------------------------------------
// Process Intelligence (process mining)
// ---------------------------------------------------------------------------

export interface FlowNode {
  activity: string;
  count: number;
  avg_minutes: number;
  systems: string[];
}

export interface FlowEdge {
  source: string;
  target: string;
  count: number;
}

export interface FlowVariant {
  sequence: string[];
  case_count: number;
  pct: number;
}

export interface ProcessIntelligence {
  process_id: string;
  name: string;
  case_count: number;
  nodes: FlowNode[];
  edges: FlowEdge[];
  variants: FlowVariant[];
  rework_rate: number;
}
