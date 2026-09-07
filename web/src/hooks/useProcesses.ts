import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export const useProcesses = (filters?: { risk_class?: string; sort_by?: string; limit?: number; offset?: number }) => {
  return useQuery({
    queryKey: ['processes', filters],
    queryFn: () => api.getProcesses(filters),
  });
};

export const useProcess = (id?: string) => {
  return useQuery({
    queryKey: ['process', id],
    queryFn: () => id ? api.getProcess(id) : Promise.reject('No ID'),
    enabled: !!id,
  });
};

export const useBlueprint = (processId?: string) => {
  return useQuery({
    queryKey: ['blueprint', processId],
    queryFn: () => processId ? api.getBlueprint(processId) : Promise.reject('No Process ID'),
    enabled: !!processId,
    retry: false, // Don't retry 403s
  });
};

export const useWeights = () => {
  return useQuery({
    queryKey: ['weights'],
    queryFn: () => api.getWeights(),
  });
};

export const useAuditLog = (filters?: { process_id?: string; limit?: number; offset?: number }) => {
  return useQuery({
    queryKey: ['audit', filters],
    queryFn: () => api.getAuditLog(filters),
  });
};

export const useReevaluate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (processId: string) => api.reevaluate(processId),
    onSuccess: (_, processId) => {
      queryClient.invalidateQueries({ queryKey: ['process', processId] });
      queryClient.invalidateQueries({ queryKey: ['processes'] });
    },
  });
};


// ---------------------------------------------------------------------------
// Automation Blueprints catalog
// ---------------------------------------------------------------------------

export const useBlueprintsCatalog = () => {
  return useQuery({
    queryKey: ['blueprints'],
    queryFn: () => api.getBlueprintsCatalog(),
  });
};

export const useGenerateBlueprint = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (processId: string) => api.generateBlueprint(processId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
    },
  });
};

export const useSubmitForApproval = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (processId: string) => api.submitForApproval(processId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
    },
  });
};


// ---------------------------------------------------------------------------
// Process Intelligence
// ---------------------------------------------------------------------------

export const useProcessIntelligence = (processId?: string) => {
  return useQuery({
    queryKey: ['intelligence', processId],
    queryFn: () => processId ? api.getProcessIntelligence(processId) : Promise.reject('No ID'),
    enabled: !!processId,
  });
};
