import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWeights } from '../hooks/useProcesses';
import { api } from '../api/client';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useWeights();
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const handleReset = async () => {
    const ok = window.confirm(
      'This permanently clears ALL processes, uploaded work logs, scores, blueprints and audit entries. This cannot be undone. Continue?'
    );
    if (!ok) return;
    setIsResetting(true);
    try {
      const res = await api.resetAllData();
      // Refresh every cached query so the dashboard shows the empty state.
      await queryClient.invalidateQueries();
      alert(res.message || 'All data cleared.');
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to reset data.');
    } finally {
      setIsResetting(false);
    }
  };

  useEffect(() => {
    if (data?.weights) {
      setWeights(data.weights);
    }
  }, [data]);

  // Moving one factor proportionally rebalances the others so the set always
  // sums to 1.0. Without this the total drifts off 100% and Save stays disabled
  // until the user manually re-balances every slider by hand.
  const handleWeightChange = (key: string, value: string) => {
    const newVal = Math.min(1, Math.max(0, parseFloat(value) / 100));
    setWeights(prev => {
      const others = Object.keys(prev).filter(k => k !== key);
      const remaining = 1 - newVal;
      const othersSum = others.reduce((s, k) => s + prev[k], 0);
      const next: Record<string, number> = { ...prev, [key]: newVal };
      if (othersSum > 0) {
        others.forEach(k => { next[k] = (prev[k] / othersSum) * remaining; });
      } else if (others.length) {
        others.forEach(k => { next[k] = remaining / others.length; });
      }
      return next;
    });
  };

  const totalSum = Object.values(weights).reduce((a, b) => a + b, 0);
  const isValid = Math.abs(totalSum - 1.0) < 0.001;

  const handleSave = async () => {
    if (!isValid) return;
    setIsSaving(true);
    try {
      await api.updateWeights(weights);
      alert('Weights updated successfully');
    } catch (e) {
      alert('Failed to update weights');
    }
    setIsSaving(false);
  };

  if (isLoading) return <div className="p-8">Loading...</div>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">Scoring Weights Configuration</h1>
        <p className="text-on-surface-variant text-sm">Adjust the relative importance of factors used in the Viability Index.</p>
      </div>

      <div className="bg-surface-container-low rounded-xl p-6 border border-outline-variant/30 space-y-6">
        {Object.entries(weights).map(([key, val]) => (
          <div key={key} className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="font-medium capitalize">{key.replace(/_/g, ' ')}</span>
              <span className="font-mono text-primary">{(val * 100).toFixed(0)}%</span>
            </div>
            <input 
              type="range" 
              min="0" max="100" step="1"
              value={val * 100}
              onChange={(e) => handleWeightChange(key, e.target.value)}
              className="w-full accent-primary"
            />
          </div>
        ))}

        <div className="pt-6 border-t border-outline-variant/30 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">Total:</span>
            <span className={`text-lg font-mono font-bold ${isValid ? 'text-status-safe' : 'text-error'}`}>
              {(totalSum * 100).toFixed(0)}%
            </span>
            {!isValid && <span className="text-xs text-error ml-2">Must equal 100%</span>}
          </div>
          <button 
            onClick={handleSave}
            disabled={!isValid || isSaving}
            className="px-6 py-2 bg-primary text-on-primary rounded-lg font-bold disabled:opacity-50 hover:bg-primary/90 transition-colors"
          >
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>

      <div className="bg-surface-container-low rounded-xl p-6 border border-outline-variant/30">
        <h3 className="text-lg font-semibold mb-4">Version History</h3>
        <div className="text-sm text-on-surface-variant italic">No previous versions found.</div>
      </div>

      <div className="bg-surface-container-low rounded-xl p-6 border border-error/40">
        <h3 className="text-lg font-semibold mb-1 text-error">Danger Zone</h3>
        <p className="text-sm text-on-surface-variant mb-4">
          Clear all processes and uploaded work logs to return the console to an empty state.
          Upload a new work log to repopulate it. This cannot be undone.
        </p>
        <button
          onClick={handleReset}
          disabled={isResetting}
          className="px-6 py-2 bg-error text-on-error rounded-lg font-bold disabled:opacity-50 hover:bg-error/90 transition-colors"
        >
          {isResetting ? 'Clearing…' : 'Reset all data'}
        </button>
      </div>
    </div>
  );
}
