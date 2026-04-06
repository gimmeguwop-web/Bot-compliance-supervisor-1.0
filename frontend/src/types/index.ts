// TypeScript type definitions for ESKD Validator

export interface Document {
  id: number;
  filename: string;
  uploaded_at: string;
  file_size: number;
  file_path?: string;
  tasks: Task[];
}

export interface Task {
  id: number;
  document_id: number;
  profile_id: string;
  status: TaskStatus;
  progress: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  results?: ValidationResult[];
}

export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ValidationResult {
  id: number;
  rule_id: string;
  rule_description: string;
  status: ValidationStatus;
  severity: 'error' | 'warning' | 'info';
  details?: string;
  page_ref?: number;
  coordinates?: string;
  gost_link?: string;
}

export type ValidationStatus = 'pass' | 'warning' | 'error';

export interface UploadResponse {
  task_id: number;
  document_id: number;
  filename: string;
  status: string;
}

export interface DashboardStats {
  total_documents: number;
  pending_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  total_errors: number;
  total_warnings: number;
}
