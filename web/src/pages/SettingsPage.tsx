import { useState, useEffect } from 'react';
import { useWeights } from '../hooks/useProcesses';
import { api } from '../api/client';

export default function SettingsPage() {
  const { data, isLoading } = useWeights();
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (data?.weights) {
      setWeights(data.weights);
    }
  }, [data]);

  const handleWeightChange = (key: string, value: string) => {
    setWeights(prev => ({ ...prev, [key]: parseFloat(value) / 100 }));
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
    </div>
  );
}
