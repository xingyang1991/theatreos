// ============================================
// TheatreOS 前端类型定义
// ============================================

// -------------------- 基础类型 --------------------

export type RingLevel = 'A' | 'B' | 'C';

export type SlotPhase = 'watching' | 'gate_lobby' | 'settling' | 'echo';

export type GateType = 'public' | 'fate' | 'council';

export type GateStatus = 'pending' | 'open' | 'closed' | 'settling' | 'settled';

export type EvidenceGrade = 'A' | 'B' | 'C';

export type EvidenceType = 
  | 'ticket'      // 票据
  | 'timestamp'   // 时间码
  | 'surveillance'// 监控帧
  | 'note'        // 手写纸条
  | 'seal'        // 印章
  | 'audio'       // 音频片段
  | 'photo';      // 照片

// -------------------- 用户相关 --------------------

export interface User {
  user_id: string;
  username: string;
  display_name?: string;
  ring_level?: RingLevel;
  role?: 'player' | 'admin' | 'moderator';
  tickets?: number;
  shards?: number;
  passes?: number;
  created_at?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// -------------------- 剧场/世界相关 --------------------

export interface Theatre {
  theatre_id: string;
  city: string;
  name?: string;
  timezone?: string;
  theme_id?: string;
  theme_version?: string;
  status?: string;
  current_tick?: number;
  world_state?: WorldState;
  created_at?: string;
}

export interface WorldState {
  tension: number;        // 紧张度 0-100
  heat: number;           // 热度 0-100
  active_threads: string[];
  recent_events: string[];
}

// -------------------- 排程相关 --------------------

export interface Slot {
  slot_id: string;
  theatre_id: string;
  hour: number;
  start_time: string;
  end_time: string;
  phase: SlotPhase;
  stages: Stage[];
  gates: Gate[];
}

export interface Stage {
  stage_id: string;
  name: string;
  location: string;
  description: string;
  current_scene: Scene | null;
  ring_required: RingLevel;
  is_active: boolean;
  viewer_count: number;
}

export interface Scene {
  scene_id: string;
  stage_id: string;
  title: string;
  media: SceneMedia;
  evidences: Evidence[];
  duration_seconds: number;
  created_at: string;
}

export interface SceneMedia {
  video_url?: string;
  thumbnail_url?: string;
  audio_url?: string;
  subtitle?: string;
  fallback_images?: string[];
}

// -------------------- 门相关 --------------------

export interface Gate {
  gate_id: string;
  slot_id: string;
  stage_id: string;
  gate_type: GateType;
  status: GateStatus;
  question: string;
  options: GateOption[];
  open_time: string;
  close_time: string;
  settle_time: string;
  total_votes: number;
  total_bets: number;
  evidence_slots: number;
  submitted_evidences: number;
}

export interface GateOption {
  option_id: string;
  label: string;
  description?: string;
  odds?: number;
  vote_count: number;
  bet_amount: number;
  is_winner?: boolean;
}

export interface GateParticipation {
  gate_id: string;
  user_id: string;
  option_id: string;
  vote_amount: number;
  bet_amount: number;
  submitted_evidence_ids: string[];
  created_at: string;
}

// -------------------- 证物相关 --------------------

export interface Evidence {
  evidence_id: string;
  user_id: string;
  scene_id: string;
  evidence_type: EvidenceType;
  grade: EvidenceGrade;
  title: string;
  description: string;
  image_url?: string;
  audio_url?: string;
  metadata: Record<string, any>;
  expires_at?: string;
  is_verified: boolean;
  created_at: string;
}

// -------------------- Explain Card 相关 --------------------

export interface ExplainCard {
  card_id: string;
  gate_id: string;
  result: ExplainResult;
  reason: ExplainReason;
  consequence: ExplainConsequence;
  echo: ExplainEcho;
  created_at: string;
}

export interface ExplainResult {
  winner_option_id: string;
  winner_label: string;
  total_participants: number;
  total_bets: number;
}

export interface ExplainReason {
  base_probability: number;
  key_evidence_types: EvidenceType[];
  world_variables: Record<string, number>;
  explanation_text: string;
}

export interface ExplainConsequence {
  world_changes: WorldChange[];
  user_rewards: UserReward[];
  permission_changes: PermissionChange[];
}

export interface WorldChange {
  variable: string;
  old_value: number;
  new_value: number;
  description: string;
}

export interface UserReward {
  user_id: string;
  reward_type: 'ticket' | 'shard' | 'pass' | 'evidence';
  amount: number;
  description: string;
}

export interface PermissionChange {
  user_id: string;
  change_type: 'upgrade' | 'downgrade' | 'unlock';
  description: string;
}

export interface ExplainEcho {
  next_hour_hints: string[];
  related_stage_ids: string[];
  storyline_tags: string[];
  tracking_points: EchoTrackingPoint[];
}

export interface EchoTrackingPoint {
  point_id: string;
  label: string;
  target_type: 'stage' | 'storyline' | 'gate';
  target_id: string;
  expected_time?: string;
}

// -------------------- 档案相关 --------------------

export interface Archive {
  user_id: string;
  participated_gates: GateRecord[];
  collected_evidences: Evidence[];
  echo_history: EchoRecord[];
  crew_contributions: CrewContribution[];
}

export interface GateRecord {
  gate_id: string;
  gate_type: GateType;
  question: string;
  my_option: string;
  winner_option: string;
  is_winner: boolean;
  bet_amount: number;
  reward_amount: number;
  participated_at: string;
  is_verified: boolean;  // 是否已印证
}

export interface EchoRecord {
  echo_id: string;
  source_gate_id: string;
  hint: string;
  is_fulfilled: boolean;
  fulfilled_at?: string;
  related_gate_id?: string;
}

export interface CrewContribution {
  contribution_id: string;
  crew_id: string;
  contribution_type: 'evidence_share' | 'vote_coordination' | 'intel_report';
  description: string;
  contributed_at: string;
}

// -------------------- Crew 相关 --------------------

export interface Crew {
  crew_id: string;
  name: string;
  description: string;
  leader_id: string;
  members: CrewMember[];
  shared_evidences: Evidence[];
  recent_gates: GateRecord[];
  tier: number;
  created_at: string;
}

export interface CrewMember {
  user_id: string;
  username: string;
  display_name: string;
  role: 'leader' | 'officer' | 'member';
  joined_at: string;
  is_online: boolean;
  current_stage_id?: string;
}

// -------------------- 故事线相关 --------------------

export interface Storyline {
  storyline_id: string;
  name: string;
  description: string;
  tags: string[];
  related_stages: string[];
  next_appearance?: StorylineAppearance;
  my_relation: 'following' | 'participated' | 'nearby' | 'none';
  pending_verifications: number;
}

export interface StorylineAppearance {
  stage_id: string;
  stage_name: string;
  expected_time: string;
  confidence: 'high' | 'medium' | 'low';
}

// -------------------- 实时推送相关 --------------------

export interface RealtimeEvent {
  event_type: 
    | 'slot_phase_change'
    | 'gate_status_change'
    | 'scene_update'
    | 'explain_card_ready'
    | 'echo_fulfilled'
    | 'crew_activity'
    | 'system_alert'
    | 'evidence_drop';
  payload: any;
  timestamp: string;
}

// -------------------- API 响应类型 --------------------

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// -------------------- 状态机类型 --------------------

export type PageState = 
  | 'loading'
  | 'empty'
  | 'error'
  | 'permission_denied'
  | 'countdown_critical'
  | 'degraded'
  | 'safety_alert'
  | 'ready';

export interface PageStateInfo {
  state: PageState;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}
