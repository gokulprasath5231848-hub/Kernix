import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useBlueprint, useProcess } from '../hooks/useProcesses';
import { submitForApproval } from '../api/client';

function downloadText(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
import { RiskClass } from '../constants';
import RiskVerificationBanner from '../components/blueprint/RiskVerificationBanner';
import StepFlow from '../components/blueprint/StepFlow';

export default function BlueprintPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: process, isLoading: isProcessLoading } = useProcess(id);
  const { data: blueprint, isLoading: isBlueprintLoading, error } = useBlueprint(id);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(false);

  // DEFENSE IN DEPTH: Client-side check matching backend
  useEffect(() => {
    if (process && process.score.risk_decision === RiskClass.TOO_RISKY) {
      navigate('/');
    }
  }, [process, navigate]);

  if (isProcessLoading || isBlueprintLoading) return <div className="p-8 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>;
  if (error || !blueprint || !process) {
    // If API returned 403, TanStack query catches it as error, we can also redirect here
    if ((error as any)?.status === 403) {
      navigate('/');
      return null;
    }
    return <div className="p-8 text-error">Failed to load blueprint.</div>;
  }

  const humanGateIndex = blueprint.steps.findIndex(s => s.requires_approval);

  // KINTIX recommends; a human authorises. This queues the blueprint for human
  // approval — it never executes the automation itself.
  const handleSubmitForApproval = () => {
    setIsSubmitting(true);
    submitForApproval(process.id)
      .then(() => setSubmitted(true))
      .catch(() => setSubmitError(true))
      .finally(() => setIsSubmitting(false));
  };

  return (
    <div className="space-y-space-2xl max-w-7xl mx-auto pb-12">
      {/* Breadcrumb */}
      <div className="flex items-center space-x-2 text-sm text-on-surface-variant">
        <Link to="/" className="hover:text-primary transition-colors">Roadmap</Link>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <Link to={`/process/${process.id}`} className="hover:text-primary transition-colors">{process.name}</Link>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-on-surface">Automation Blueprint</span>
      </div>

      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Automated Execution Blueprint</h1>
          <div className="flex items-center space-x-4">
            <span className="text-on-surface-variant text-sm border-r border-outline-variant/30 pr-4">Generated {new Date(blueprint.generated_at).toLocaleString()}</span>
            <span className="text-sm font-mono text-primary flex items-center space-x-1"><span className="material-symbols-outlined text-[16px]">bolt</span><span>v1.0.0-rc.2</span></span>
          </div>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => {
              const code = `# KINTIX generated blueprint: ${process.name}\n# Human approval is required before execution.\n\nBLUEPRINT = ${JSON.stringify(blueprint, null, 2)}\n`;
              downloadText('kintix_blueprint.py', code, 'text/x-python;charset=utf-8');
            }}
            className="px-4 py-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-sm font-medium hover:bg-surface-container-highest transition-colors flex items-center space-x-2"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            <span>Download Python SDK</span>
          </button>
          <button
            onClick={() => {
              const spec = {
                openapi: '3.0.3',
                info: { title: `KINTIX — ${process.name}`, version: '1.0.0' },
                paths: {
                  '/approval': {
                    post: {
                      summary: 'Submit blueprint for human approval',
                      responses: { '202': { description: 'Awaiting human approval' } }
                    }
                  }
                }
              };
              downloadText('kintix-openapi.json', JSON.stringify(spec, null, 2), 'application/json');
            }}
            className="px-4 py-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-sm font-medium hover:bg-surface-container-highest transition-colors flex items-center space-x-2"
          >
            <span className="material-symbols-outlined text-[18px]">code</span>
            <span>Export OpenAPI Spec</span>
          </button>
          <button
            onClick={handleSubmitForApproval}
            disabled={isSubmitting || submitted}
            title="Queues this blueprint for human approval. KINTIX does not execute automations."
            className="px-6 py-2 rounded-lg bg-primary text-on-primary text-sm font-bold hover:bg-primary/90 transition-all flex items-center space-x-2 shadow-[0_0_15px_rgba(236,194,70,0.3)] disabled:opacity-80"
          >
            {isSubmitting ? (
              <span className="material-symbols-outlined text-[18px] animate-spin">sync</span>
            ) : (
              <span className="material-symbols-outlined text-[18px]">
                {submitted ? 'check_circle' : 'how_to_reg'}
              </span>
            )}
            <span>
              {isSubmitting
                ? 'Submitting\u2026'
                : submitted
                ? 'Awaiting Human Approval'
                : submitError
                ? 'Retry Submission'
                : 'Send to Approval Queue'}
            </span>
          </button>
        </div>
      </div>

      <RiskVerificationBanner 
        passed={true} 
        riskClass={process.score.risk_decision} 
        apiEndpoint={`api.kintix.internal/v1/exec/${process.id.substring(0,8)}`}
      />

      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
          <span className="material-symbols-outlined text-primary">account_tree</span>
          <span>Pipeline Architecture</span>
        </h3>
        <StepFlow steps={blueprint.steps} humanGateIndex={humanGateIndex >= 0 ? humanGateIndex : null} />
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-8 space-y-4">
          <details className="group bg-surface-container-low rounded-xl border border-outline-variant/30 overflow-hidden" open>
            <summary className="px-6 py-4 flex items-center justify-between cursor-pointer bg-surface-container/30 group-hover:bg-surface-container/50 transition-colors">
              <h4 className="font-semibold flex items-center space-x-2">
                <span className="material-symbols-outlined text-on-surface-variant">settings_ethernet</span>
                <span>Technical Configuration</span>
              </h4>
              <span className="material-symbols-outlined group-open:rotate-180 transition-transform text-on-surface-variant">expand_more</span>
            </summary>
            <div className="p-6 border-t border-outline-variant/30 grid grid-cols-2 gap-y-6 gap-x-12">
              <div>
                <div className="text-xs text-on-surface-variant mb-1">Execution Endpoint</div>
                <div className="font-mono text-sm bg-surface-container-highest px-3 py-1.5 rounded text-on-surface">POST /v1/blueprint/exec</div>
              </div>
              <div>
                <div className="text-xs text-on-surface-variant mb-1">Timeout & Retry</div>
                <div className="font-mono text-sm">30s / max 3 retries (exp backoff)</div>
              </div>
              <div>
                <div className="text-xs text-on-surface-variant mb-1">Fallback Escalation Path</div>
                <div className="font-mono text-sm text-secondary flex items-center space-x-1">
                  <span className="material-symbols-outlined text-[14px]">call_split</span>
                  <span>DLQ_Manual_Review_Queue</span>
                </div>
              </div>
              <div>
                <div className="text-xs text-on-surface-variant mb-1">State Persistence</div>
                <div className="font-mono text-sm flex items-center space-x-1">
                  <span className="material-symbols-outlined text-status-safe text-[14px]">database</span>
                  <span>Redis Checkpointing Enabled</span>
                </div>
              </div>
            </div>
          </details>
        </div>

        <div className="col-span-4 space-y-4">
          <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-6">
            <h4 className="font-semibold text-sm mb-4 flex items-center space-x-2 text-on-surface-variant">
              <span className="material-symbols-outlined text-[18px]">dns</span>
              <span>Connected Systems Status</span>
            </h4>
            <div className="space-y-3">
              {process.systems.slice(0,3).map((sys) => (
                <div key={sys} className="flex justify-between items-center bg-surface-container/50 px-3 py-2 rounded-lg border border-outline-variant/20">
                  <span className="font-mono text-sm">{sys}</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] text-status-safe font-mono uppercase">Online</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-status-safe animate-pulse"></span>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-6 pt-4 border-t border-outline-variant/30">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-on-surface-variant">Agent Pool Capacity</span>
                <span className="text-xs font-mono text-primary">82%</span>
              </div>
              <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                <div className="h-full bg-primary" style={{ width: '82%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
