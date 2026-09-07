export type TaskType =
  | 'LEGAL'
  | 'CLIENT'
  | 'DOCUMENT'
  | 'COMMUNICATION'
  | 'FOLLOW_UP'
  | 'FINANCIAL'
  | 'ADMINISTRATIVE'
  | 'OTHER';

export type TaskStatus = 'OPEN' | 'IN_PROGRESS' | 'WAITING' | 'COMPLETED' | 'CANCELLED';

export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export type ActionOwnerType = 'INTERNAL' | 'CLIENT' | 'EXTERNAL';

export type WaitingOn =
  | 'CLIENT'
  | 'OPPOSING_COUNSEL'
  | 'COURT'
  | 'GOVERNMENT'
  | 'PAYMENT'
  | 'SIGNATURE'
  | 'DOCUMENT'
  | 'INTERNAL_APPROVAL'
  | 'OTHER';

export interface TaskResponse {
  task_id: string;
  matter_key: string;
  title: string;
  description: string | null;
  task_type: TaskType;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to: string | null;
  created_by: string | null;
  action_owner_type: ActionOwnerType;
  waiting_on: string | null;
  waiting_reason: string | null;
  waiting_since: string | null;
  due_at: string | null;
  next_action_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  total: number;
  limit: number;
  offset: number;
  tasks: TaskResponse[];
}

export interface TaskCreate {
  matter_key: string;
  title: string;
  description?: string | null;
  task_type: TaskType;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigned_to?: string | null;
  created_by?: string | null;
  action_owner_type?: ActionOwnerType;
  waiting_on?: WaitingOn | null;
  waiting_reason?: string | null;
  waiting_since?: string | null;
  due_at?: string | null;
  next_action_at?: string | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  task_type?: TaskType;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigned_to?: string | null;
  action_owner_type?: ActionOwnerType;
  waiting_on?: WaitingOn | null;
  waiting_reason?: string | null;
  waiting_since?: string | null;
  due_at?: string | null;
  next_action_at?: string | null;
}
