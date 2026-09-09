import { useEffect, useMemo, useRef, useState } from 'react';
import { useRunAgent } from '../../hooks/useProcesses';
import { RiskClass } from '../../constants';
import { AgentRunResult, AgentStepType, AgentTraceStep } from '../../types';

/**
 * The visible face of the agentic layer.
 *
 * Click "Run Agent" and watch it plan, call tools, read results and either
 * finish autonomously, stop at the risk gate to ask a human, or refuse to start.
 * The trace is revealed one step at a time so the reasoning reads like a live
 * run rather than a dumped log.
 */

const STEP_ICON: Record<AgentStepType, string> = {
  plan: 'lightbulb',
  tool_call: 'bolt',
  observation: 'visibility',
  blocked: 'gpp_maybe',
  final: 'flag',
};

const STATUS_STYLE: Record<
  string,
  { icon: string; text: string; bg: string; border: string; label: string }
> = {
  COMPLETED: {
    icon: 'task_alt',
    text: 'text-emerald-400',
    bg: 'bg-emerald-950/30',
    border: 'border-emerald-500/30',
    label: 'Completed autonomously',
  },
  AWAITING_HUMAN_APPROVAL: {
    icon: 'front_hand',
    text: 'text-amber-300',
    bg: 'bg-amber-950/30',
    border: 'border-amber-500/30',
    label: 'Paused — awaiting human approval',
  },
  REFUSED: {
    icon: 'block',
    text: 'text-rose-400',
    bg: 'bg-rose-950/30',
    border: 'border-rose-500/30',
    label: 'Refused — too risky for any autonomous action',
  },
  FAILED: {
    icon: 'error',
    text: 'text-rose-400',
    bg: 'bg-rose-950/30',
    border: 'border-rose-500/30',
    label: 'Run failed',
  },
  MAX_STEPS_REACHED: {
    icon: 'timer_off',
    text: 'text-amber-300',
    bg: 'bg-amber-950/30',
    border: 'border-amber-500/30',
    label: 'Halted at step ceiling',
  },
};

function GateExplainer({ risk }: { risk: RiskClass }) {
  const copy: Record<RiskClass, string> = {
    [RiskClass.PRE_APPROVED]:
      'Pre-Approved: the agent may complete every step on its own, including writes.',
    [RiskClass.HUMAN_IN_THE_LOOP]:
      'Human-in-the-Loop: the agent does the safe prep, then stops before any write and asks a human.',
    [RiskClass.TOO_RISKY]:
      'Too Risky: the agent refuses to act. A human handles it end to end.',
  };
  return (
    <p className="text-xs text-on-surface-variant leading-relaxed">
      <span className="material-symbols-outlined text-[14px] align-middle mr-1 text-primary">
        shield
      </span>
      {copy[risk]}
    </p>
  );
}

function TraceRow({ step }: { step: AgentTraceStep }) {
  const blocked = step.blocked;
  return (
    <div
      className={`flex gap-3 px-4 py-3 rounded-lg border animate-[fadeIn_0.25s_ease-out] ${
        blocked
          ? 'bg-rose-950/20 border-rose-500/30'
          : step.type === 'final'
          ? 'bg-surface-container/60 border-outline-variant/40'
          : 'bg-surface-container-low border-outline-variant/20'
      }`}
    >
      <span
        className={`material-symbols-outlined text-[20px] mt-0.5 ${
          blocked ? 'text-rose-400' : step.type === 'plan' ? 'text-primary' : 'text-on-surface-variant'
        }`}
      >
        {blocked ? 'gpp_maybe' : STEP_ICON[step.type]}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono uppercase tracking-wide text-on-surface-variant/70">
            {blocked ? 'blocked by gate' : step.type.replace('_', ' ')}
          </span>
          {step.tool && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container-highest text-primary border border-outline-variant/30">
              {step.tool}()
            </span>
          )}
        </div>
        <p
          className={`text-sm mt-1 break-words ${
            blocked ? 'text-rose-200' : 'text-on-surface'
          }`}
        >
          {step.content}
        </p>
        {step.args && Object.keys(step.args).length > 0 && !step.tool?.startsWith('fetch') && (
          <pre className="text-[11px] font-mono text-on-surface-variant/80 mt-1 whitespace-pre-wrap break-words">
            {JSON.stringify(step.args)}
          </pre>
        )}
      </div>
    </div>
  );
}

export default function AgentConsole({
  processId,
  riskClass,
}: {
  processId: string;
  riskClass: RiskClass;
}) {
  const runAgent = useRunAgent();
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [revealed, setRevealed] = useState(0);
  const timer = useRef<number | null>(null);

  // Reveal trace steps one at a time for a live-run feel.
  useEffect(() => {
    if (!result) return;
    setRevealed(0);
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(() => {
      setRevealed((n) => {
        if (n >= result.trace.length) {
          if (timer.current) window.clearInterval(timer.current);
          return n;
        }
        return n + 1;
      });
    }, 450);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [result]);

  const actionsTaken = useMemo(
    () =>
      result
        ? result.trace.filter(
            (s) => s.type === 'tool_call' && s.tool === 'apply_update' && !s.blocked
          ).length
        : 0,
    [result]
  );

  const done = result && revealed >= result.trace.length;
  const status = result ? STATUS_STYLE[result.status] : null;

  const handleRun = () => {
    setResult(null);
    runAgent.mutate(
      { processId, engine: 'auto' },
      { onSuccess: (data) => setResult(data) }
    );
  };

  return (
    <div className="mt-space-2xl">
      <style>{`@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}`}</style>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold flex items-center space-x-2">
            <span className="material-symbols-outlined text-primary">smart_toy</span>
            <span>Agent Console</span>
          </h3>
          <p className="text-xs text-on-surface-variant mt-1">
            Autonomous execution, fenced by the risk gate.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={runAgent.isPending}
          className="px-5 py-2.5 rounded-lg bg-primary text-on-primary text-sm font-bold hover:bg-primary/90 transition-all flex items-center justify-center space-x-2 shadow-[0_0_15px_rgba(236,194,70,0.3)] disabled:opacity-70"
        >
          <span
            className={`material-symbols-outlined text-[18px] ${
              runAgent.isPending ? 'animate-spin' : ''
            }`}
          >
            {runAgent.isPending ? 'sync' : 'play_arrow'}
          </span>
          <span>{runAgent.isPending ? 'Agent running…' : 'Run Agent'}</span>
        </button>
      </div>

      <div className="bg-surface-container-low/50 rounded-2xl p-5 md:p-6 border border-outline-variant/30">
        <GateExplainer risk={riskClass} />

        {runAgent.isError && (
          <p className="text-sm text-error mt-4">
            Agent run failed: {(runAgent.error as Error)?.message || 'unknown error'}
          </p>
        )}

        {!result && !runAgent.isPending && (
          <p className="text-sm text-on-surface-variant/70 mt-6 text-center py-8">
            Press <span className="font-semibold text-on-surface">Run Agent</span> to watch it
            plan, call tools, and respect the gate in real time.
          </p>
        )}

        {result && (
          <div className="mt-5 space-y-2">
            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="text-[10px] font-mono uppercase px-2 py-1 rounded bg-surface-container-highest text-on-surface-variant border border-outline-variant/30">
                engine: {result.engine}
              </span>
              <span className="text-[10px] font-mono uppercase px-2 py-1 rounded bg-surface-container-highest text-on-surface-variant border border-outline-variant/30">
                consequential actions: {actionsTaken}
              </span>
            </div>

            {result.trace.slice(0, revealed).map((step) => (
              <TraceRow key={step.seq} step={step} />
            ))}

            {!done && (
              <div className="flex items-center gap-2 px-4 py-3 text-on-surface-variant text-sm">
                <span className="material-symbols-outlined text-[18px] animate-spin">
                  progress_activity
                </span>
                <span>thinking…</span>
              </div>
            )}

            {done && status && (
              <div
                className={`mt-3 flex items-start gap-3 px-4 py-3 rounded-lg border ${status.bg} ${status.border}`}
              >
                <span className={`material-symbols-outlined ${status.text}`}>
                  {status.icon}
                </span>
                <div>
                  <p className={`text-sm font-semibold ${status.text}`}>{status.label}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">{result.summary}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
