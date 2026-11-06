export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const ROLES = [
  { id: 'engineering', label: 'Engineering' },
  { id: 'hr', label: 'HR' },
  { id: 'finance', label: 'Finance' },
];

export const INITIAL_MESSAGES = [
  {
    id: 'msg-1',
    sender: 'user',
    text: 'What is our maximum PostgreSQL failover RTO and how does Patroni promote replicas?',
  },
  {
    id: 'msg-2',
    sender: 'assistant',
    status: 'success',
    answer:
      'Based on the verified engineering architecture policies:\n\n' +
      '• The maximum Recovery Time Objective (RTO) for PostgreSQL failover is strictly 30 seconds.\n' +
      '• Patroni leverages the Distributed Configuration Store (DCS) leader lock to coordinate failover and automatically promote the healthiest synchronous replica.\n' +
      '• Split-brain scenarios are prevented via strict lease timeouts and fencing mechanisms on the primary node.',
    citations: [
      {
        id: 1,
        source_file: 'pg_failover_policy.pdf',
        department: 'engineering',
        snippet: 'Section 4.2: Maximum PostgreSQL failover RTO is capped at 30 seconds. Synchronous replication standby nodes must maintain WAL lag below 16MB.',
        score: 0.94,
      },
      {
        id: 2,
        source_file: 'patroni_config.md',
        department: 'engineering',
        snippet: 'Patroni utilizes etcd/Consul DCS atomic compare-and-swap operations to elect a new leader and trigger pg_ctl promote on the replica.',
        score: 0.89,
      },
    ],
  },
];

export const INITIAL_INGESTION_HISTORY = [
  { id: 'ing-1', fileName: 'system_architecture.pdf', policy: 'Engineering', status: 'Processing...' },
  { id: 'ing-2', fileName: 'employee_handbook.docx', policy: 'HR', status: 'Completed' },
];