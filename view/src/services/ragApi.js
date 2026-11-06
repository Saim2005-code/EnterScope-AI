import { API_BASE_URL } from '../config/constants';

export async function queryRagAssistant({ query, userRole, topK = 3 }) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      user_role: userRole,
      top_k: Number(topK),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API request failed with status ${response.status}`);
  }

  return response.json();
}

export async function uploadEnterpriseDocument({ file, targetPolicy, adminToken }) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('department', targetPolicy.toLowerCase());

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: 'POST',
    headers: {
      ...(adminToken ? { Authorization: `Bearer ${adminToken}` } : {}),
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Ingestion failed with status ${response.status}`);
  }

  return response.json();
}