import { ProcessDetail, ProcessListItem, Blueprint, Score, WeightsConfig, AuditEntry } from '../types';

interface ProcessListResponse {
  items: ProcessListItem[];
  total_count: number;
}

const BASE_URL = import.meta.env.VITE_API_URL || '';

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const headers: Record<string, string> = isFormData
    ? {}
    : { 'Content-Type': 'application/json', ...options?.headers as Record<string, string> };
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const error = await res.json();
      detail = error.detail || detail;
    } catch {
      // Ignore JSON parse error
    }
    throw new APIError(res.status, detail || 'Unknown error');
  }
  return res.json();
}

export const api = {
  getHealth: () => fetchAPI<{status: string; version: string}>('/health'),
  getProcesses: (params?: { risk_class?: string; sort_by?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.risk_class) searchParams.append('risk_class', params.risk_class);
      if (params.sort_by) searchParams.append('sort_by', params.sort_by);
      if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());
      if (params.offset !== undefined) searchParams.append('offset', params.offset.toString());
    }
    const qs = searchParams.toString();
    // Backend returns { items, total_count }; callers work with the array.
    return fetchAPI<ProcessListResponse>(`/api/processes${qs ? `?${qs}` : ''}`)
      .then((r) => r.items);
  },
  getProcess: (id: string) => fetchAPI<ProcessDetail>(`/api/processes/${id}`),
  getBlueprint: (processId: string) => fetchAPI<Blueprint>(`/api/processes/${processId}/blueprint`),
  reevaluate: (processId: string) => fetchAPI<Score>(`/api/processes/${processId}/reevaluate`, { method: 'POST' }),
  getWeights: () => fetchAPI<WeightsConfig>('/api/weights'),
  updateWeights: (weights: Record<string, number>) => fetchAPI<WeightsConfig>('/api/weights', { method: 'PUT', body: JSON.stringify({ weights }) }),
  getAuditLog: (params?: { process_id?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.process_id) searchParams.append('process_id', params.process_id);
      if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());
      if (params.offset !== undefined) searchParams.append('offset', params.offset.toString());
    }
    const qs = searchParams.toString();
    return fetchAPI<AuditEntry[]>(`/api/audit${qs ? `?${qs}` : ''}`);
  },
  submitForApproval: (processId: string) =>
    fetchAPI<{ status: string; process_id: string }>(
      `/api/processes/${processId}/blueprint/submit-for-approval`,
      { method: 'POST' }
    ),
  ingest: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchAPI<{ message: string; events_ingested: number; discovery?: object }>('/api/ingest', {
      method: 'POST',
      body: formData,
    });
  },
};


// Named export used by BlueprintPage's approval action.
export const submitForApproval = (processId: string) => api.submitForApproval(processId);
