// ============================================
// TheatreOS API 服务层
// ============================================

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  User,
  Theatre,
  Slot,
  Stage,
  Scene,
  Gate,
  GateParticipation,
  Evidence,
  ExplainCard,
  Archive,
  Crew,
  Storyline,
  ApiResponse,
  PaginatedResponse,
  RingLevel,
} from '@/types';

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/v1';

// 创建 Axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('theatreos_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token 过期，清除并跳转登录
      localStorage.removeItem('theatreos_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);


// =============================================================================
// P0 Adapters (FE types <-> BE v1.2 routes)
// 目标：让现有页面不改/少改即可跑通闭环（Showbill/StageLive/GateLobby）
// =============================================================================

/** 读取本地缓存的 theatre_id（由 App.tsx 写入） */
function getStoredTheatreId(): string | null {
  try {
    return localStorage.getItem('theatreos_theatre_id');
  } catch {
    return null;
  }
}

/** BE SlotPhase -> FE SlotPhase (frontend/src/types) */
function mapSlotPhaseFromBE(phase?: string): 'watching' | 'gate_lobby' | 'settling' | 'echo' {
  const p = (phase || '').toLowerCase();
  if (p === 'gate_open' || p === 'gate' || p === 'gate_lobby') return 'gate_lobby';
  if (p === 'resolving' || p === 'resolve' || p === 'settling') return 'settling';
  if (p === 'echo') return 'echo';
  return 'watching';
}

/** BE GateType -> FE GateType */
function mapGateTypeFromBE(type?: string): 'public' | 'fate' | 'council' {
  const t = (type || '').toLowerCase();
  if (t.includes('council')) return 'council';
  if (t.includes('fate')) return 'fate';
  return 'public';
}

/** BE GateStatus/is_open -> FE GateStatus */
function mapGateStatusFromBE(status?: string, isOpen?: boolean): 'pending' | 'open' | 'closed' | 'settling' | 'settled' {
  if (isOpen) return 'open';
  const s = (status || '').toUpperCase();
  if (s === 'OPEN') return 'open';
  if (s === 'RESOLVING' || s === 'SETTLING') return 'settling';
  if (s === 'RESOLVED' || s === 'SETTLED' || s === 'COMPLETED') return 'settled';
  if (s === 'PENDING' || s === 'SCHEDULED') return 'pending';
  return 'closed';
}

/** BE evidence tier -> FE EvidenceGrade */
function mapEvidenceGradeFromBE(tier?: string): 'A' | 'B' | 'C' {
  const t = (tier || '').toUpperCase();
  if (t === 'A') return 'A';
  if (t === 'B') return 'B';
  return 'C';
}

/** 由 type_id 兜底推断 EvidenceType（后端目前返回 type_id，自由度较高） */
function inferEvidenceType(typeId?: string): 'ticket' | 'timestamp' | 'surveillance' | 'note' | 'seal' | 'audio' | 'photo' {
  const t = (typeId || '').toLowerCase();
  if (t.includes('ticket')) return 'ticket';
  if (t.includes('time') || t.includes('timestamp')) return 'timestamp';
  if (t.includes('surveillance') || t.includes('cctv') || t.includes('cam')) return 'surveillance';
  if (t.includes('seal') || t.includes('stamp')) return 'seal';
  if (t.includes('audio') || t.includes('voice')) return 'audio';
  if (t.includes('photo') || t.includes('image')) return 'photo';
  return 'note';
}

/** Showbill SlotResponse -> FE Slot */
function adaptSlotFromShowbill(slot: any, theatreId: string): Slot {
  const start = slot?.start_at || slot?.start_time || slot?.startAt || new Date().toISOString();
  const end = slot?.end_at || slot?.end_time || slot?.endAt || start;
  const hour = (() => {
    const d = new Date(start);
    return Number.isFinite(d.getTime()) ? d.getHours() : 0;
  })();

  const stages: Stage[] = Array.isArray(slot?.stages)
    ? slot.stages.map((sc: any) => ({
        stage_id: sc?.stage_id,
        name: sc?.name || sc?.stage_name || '未命名舞台',
        location: '',
        description: sc?.scene_title ? `正在上演：${sc.scene_title}` : '',
        ring_required: (sc?.ring_level || sc?.ring_required || 'C') as RingLevel,
        is_active: true,
        viewer_count: 0,
        current_scene: null,
      }))
    : [];

  return {
    slot_id: slot?.slot_id,
    theatre_id: theatreId,
    hour,
    start_time: start,
    end_time: end,
    phase: mapSlotPhaseFromBE(slot?.phase),
    stages,
    gates: [],
  };
}

/** NearbyStageItem -> FE Stage */
function adaptNearbyStageToStage(item: any): Stage {
  const distanceM = typeof item?.distance_m === 'number' ? Math.round(item.distance_m) : null;
  const tags = Array.isArray(item?.tags) ? item.tags : [];
  const status = (item?.status || '').toUpperCase();

  return {
    stage_id: item?.stage_id,
    name: item?.name || '未命名舞台',
    location: distanceM != null ? `距你约 ${distanceM}m` : '附近',
    description: tags.length ? tags.join(' · ') : '城市剧场舞台',
    ring_required: 'C',
    is_active: status === 'OPEN' || status === 'ACTIVE',
    viewer_count: 0,
    current_scene: null,
  };
}

/** GateLobbyResponse -> FE Gate */
function adaptGateLobbyToGate(lobby: any): Gate {
  const optionsRaw = Array.isArray(lobby?.options) ? lobby.options : [];
  const options = optionsRaw.map((opt: any) => ({
    option_id: opt?.option_id,
    text: opt?.label || opt?.text || '选项',
    vote_count: Number(opt?.vote_count || 0),
    bet_amount: Number(opt?.stake_total || opt?.bet_amount || 0),
  }));

  const totalVotes = options.reduce((sum: number, o: any) => sum + (Number(o.vote_count) || 0), 0);
  const totalBets = options.reduce((sum: number, o: any) => sum + (Number(o.bet_amount) || 0), 0);

  const userEvidenceCount = Array.isArray(lobby?.user_participation?.evidence_submitted)
    ? lobby.user_participation.evidence_submitted.length
    : 0;

  return {
    gate_id: lobby?.gate_instance_id,
    slot_id: lobby?.slot_id,
    // 当前前端 Gate 类型强制要求 stage_id；P0 阶段以“本小时之门”作为虚拟舞台占位
    stage_id: lobby?.stage_id || 'hour_gate',
    gate_type: mapGateTypeFromBE(lobby?.type),
    question: lobby?.title || '本小时之门',
    options,
    open_time: lobby?.open_at,
    close_time: lobby?.close_at,
    settle_time: lobby?.resolve_at || lobby?.close_at,
    status: mapGateStatusFromBE(lobby?.status, lobby?.is_open),
    total_votes: totalVotes,
    total_bets: totalBets,
    evidence_slots: Number(lobby?.evidence_slots || 0),
    // 后端暂未返回全局提交数；P0 用"我提交了几条"占位，后续建议后端补 total_evidence_submissions
    submitted_evidences: userEvidenceCount,
  };
}

/** SlotDetailResponse( /slots/{slot_id}/details ) 的 stage -> FE Scene (+补充字段用于现有 StageLive) */
function adaptSlotDetailStageToScene(slotDetail: any, stage: any): Scene {
  const sc = stage?.scene || {};
  const mediaUrl = sc?.media_url || sc?.video_url || undefined;
  const thumbUrl = sc?.thumbnail_url || undefined;

  // Scene 类型本身不含 ring_required / stage_name，但 StageLive 页面会通过 (scene as any).xxx 读取
  return {
    scene_id: sc?.scene_id || `scene_${slotDetail?.slot_id || 'slot'}_${stage?.stage_id || 'stage'}`,
    stage_id: stage?.stage_id,
    title: sc?.title || stage?.name || '未命名场景',
    description: sc?.beat_type ? `Beat: ${sc.beat_type}` : '',
    media: {
      video_url: mediaUrl,
      thumbnail_url: thumbUrl,
      // 下面字段后端 v1.2 details 暂未提供，保留扩展位
      audio_url: (sc as any)?.audio_url,
      subtitle: (sc as any)?.subtitle,
      fallback_images: (sc as any)?.fallback_images,
    },
    evidences: [],
    duration_seconds: Number(sc?.duration_seconds || 0),
    created_at: slotDetail?.start_at || new Date().toISOString(),
    ...( {
      ring_required: (stage?.ring_level || 'C') as RingLevel,
      stage_name: stage?.name || stage?.stage_id,
    } as any ),
  } as any;
}

/** EvidenceResponse -> FE Evidence */
function adaptEvidenceResponse(e: any, userId: string): Evidence {
  return {
    evidence_id: e?.instance_id,
    user_id: userId,
    scene_id: e?.source_scene_id || '',
    evidence_type: inferEvidenceType(e?.type_id),
    grade: mapEvidenceGradeFromBE(e?.tier),
    title: e?.name || '证物',
    description: e?.description || '',
    image_url: undefined,
    audio_url: undefined,
    metadata: {},
    expires_at: e?.expires_at || undefined,
    is_verified: String(e?.verification_status || '').toUpperCase() === 'VERIFIED',
    created_at: e?.created_at || new Date().toISOString(),
  };
}


// -------------------- Auth API --------------------

export const authApi = {
  register: async (username: string, password: string, displayName?: string) => {
    const response = await apiClient.post<ApiResponse<{ user_id: string; token: string }>>('/auth/register', {
      username,
      password,
      display_name: displayName,
    });
    return response.data;
  },

  login: async (username: string, password: string) => {
    const response = await apiClient.post<ApiResponse<{ user_id: string; token: string; expires_at: string }>>('/auth/login', {
      username_or_email: username,
      password,
    });
    return response.data;
  },

  getMe: async () => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  refreshToken: async () => {
    const response = await apiClient.post<ApiResponse<{ token: string; expires_at: string }>>('/auth/refresh');
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/auth/logout');
    return response.data;
  },
};

// -------------------- Theatre API --------------------

export const theatreApi = {
  create: async (city: string) => {
    const response = await apiClient.post<{ theatre_id: string }>('/theatres', { city });
    return response.data;
  },

  getWorldState: async (theatreId: string) => {
    const response = await apiClient.get<Theatre>(`/theatres/${theatreId}/world`);
    return response.data;
  },

  getTheatre: async (theatreId: string) => {
    const response = await apiClient.get<Theatre>(`/theatres/${theatreId}`);
    return response.data;
  },

  tick: async (theatreId: string) => {
    const response = await apiClient.post(`/theatres/${theatreId}/tick`);
    return response.data;
  },
};

// -------------------- Schedule API --------------------

export const scheduleApi = {
  /**
   * Showbill（戏单）
   * ✅ P0: 改用 /theatres/{theatre_id}/showbill （Slot&Showbill v1.2）
   * 并做字段映射：start_at -> start_time, end_at -> end_time, phase 映射等
   */
  getShowbill: async (theatreId: string, hours: number = 2) => {
    try {
      const response = await apiClient.get<any>(`/theatres/${theatreId}/showbill`, {
        params: { lookahead_hours: hours },
      });

      const slotsRaw = response.data?.slots || [];
      const slots: Slot[] = Array.isArray(slotsRaw)
        ? slotsRaw.map((s: any) => adaptSlotFromShowbill(s, theatreId))
        : [];

      return {
        slots,
        current_slot_id: response.data?.current_slot_id,
        server_time: response.data?.current_time,
      };
    } catch (e) {
      // P0：不让戏单崩（准点开演允许降级，不能空白）
      return { slots: [] as Slot[] };
    }
  },

  /**
   * 当前 Slot
   * ✅ P0: 用 showbill(lookahead=1) 推断当前 slot；保持返回值类型不变（Slot|null）
   */
  getCurrentSlot: async (theatreId: string) => {
    const showbill = await scheduleApi.getShowbill(theatreId, 1);
    const slots = showbill?.slots || [];

    // 1) 优先用后端 current_slot_id（更可靠）
    const currentById =
      (showbill as any)?.current_slot_id &&
      slots.find((s: Slot) => s.slot_id === (showbill as any).current_slot_id);

    if (currentById) return currentById;

    // 2) 兜底：按时间落在 start/end 之间
    const now = new Date();
    const currentByTime =
      slots.find((s: Slot) => now >= new Date(s.start_time) && now < new Date(s.end_time)) || null;

    if (currentByTime) return currentByTime;

    // 3) 再兜底：取最近一条
    return slots.length ? slots[0] : null;
  },

  /**
   * Slot 详情
   * P0 阶段前端暂未使用；保留原接口，方便后续页面逐步切到 /slots/{slot_id}/details
   */
  getSlotDetail: async (slotId: string) => {
    const response = await apiClient.get<any>(`/slots/${slotId}`);
    return response.data as Slot;
  },

  /**
   * ✅ P0 新增：Slot Details（包含每个舞台的当前 Scene 投影）
   * /slots/{slot_id}/details 由 slot_routes.py 提供
   */
  getSlotDetails: async (slotId: string) => {
    const response = await apiClient.get<any>(`/slots/${slotId}/details`);
    return response.data;
  },
};


// -------------------- Stage API --------------------

export const stageApi = {
  /**
   * 获取舞台列表（附近舞台）
   * ✅ P0: /theatres/{theatre_id}/stages/nearby 返回 NearbyStageItem，需要映射到 FE Stage
   */
  getStages: async (theatreId: string) => {
    try {
      const response = await apiClient.get<any>(`/theatres/${theatreId}/stages/nearby`, {
        params: { lat: 31.2304, lng: 121.4737, radius_m: 50000 }, // 上海市中心，50km半径（P0 默认）
      });

      const raw = response.data?.stages || [];
      const stages: Stage[] = Array.isArray(raw) ? raw.map((s: any) => adaptNearbyStageToStage(s)) : [];

      return { stages };
    } catch (e) {
      return { stages: [] as Stage[] };
    }
  },

  /**
   * Stage 详情
   * 当前后端 v1.2 未提供通用 /stages/{stage_id} 详情（只有 nearby / datapack）
   * P0 阶段页面未强依赖：先保持接口但可能 404
   */
  getStageDetail: async (stageId: string) => {
    const response = await apiClient.get<Stage>(`/stages/${stageId}`);
    return response.data;
  },

  /**
   * 当前场景（StageLive 用）
   * ✅ P0: 改为：
   *  1) 读取本地 theatre_id
   *  2) showbill 推断当前 slot
   *  3) /slots/{slot_id}/details 里找到该 stage 的 scene
   *  4) 映射为 FE Scene（并附带 ring_required/stage_name 给现有页面使用）
   */
  getCurrentScene: async (stageId: string) => {
    try {
      const theatreId = getStoredTheatreId();
      if (!theatreId) {
        // 无 theatreId 时返回降级占位，避免 StageLive 崩
        return {
          scene_id: `scene_placeholder_${stageId}`,
          stage_id: stageId,
          title: '暂无剧场信息',
          description: '缺少 theatre_id，已降级到占位内容',
          media: {},
          evidences: [],
          duration_seconds: 0,
          created_at: new Date().toISOString(),
          ...( { ring_required: 'C', stage_name: stageId } as any ),
        } as any;
      }

      const currentSlot = await scheduleApi.getCurrentSlot(theatreId);
      if (!currentSlot) {
        return {
          scene_id: `scene_placeholder_${stageId}`,
          stage_id: stageId,
          title: '本小时未排片',
          description: '当前无可用 Slot（已降级）',
          media: {},
          evidences: [],
          duration_seconds: 0,
          created_at: new Date().toISOString(),
          ...( { ring_required: 'C', stage_name: stageId } as any ),
        } as any;
      }

      const slotDetail = await scheduleApi.getSlotDetails(currentSlot.slot_id);
      const stage = Array.isArray(slotDetail?.stages)
        ? slotDetail.stages.find((s: any) => s?.stage_id === stageId)
        : null;

      if (!stage) {
        return {
          scene_id: `scene_placeholder_${stageId}`,
          stage_id: stageId,
          title: '该舞台本小时未开演',
          description: '你可以返回戏单选择其他舞台',
          media: {},
          evidences: [],
          duration_seconds: 0,
          created_at: new Date().toISOString(),
          ...( { ring_required: 'C', stage_name: stageId } as any ),
        } as any;
      }

      return adaptSlotDetailStageToScene(slotDetail, stage);
    } catch (e) {
      // 任何异常都降级为占位场景（确保“准点开演”）
      return {
        scene_id: `scene_placeholder_${stageId}`,
        stage_id: stageId,
        title: '投影信号不稳定',
        description: '已降级到静帧模式',
        media: {},
        evidences: [],
        duration_seconds: 0,
        created_at: new Date().toISOString(),
        ...( { ring_required: 'C', stage_name: stageId } as any ),
      } as any;
    }
  },

  /**
   * nearby stages（保留）
   */
  getNearbyStages: async (theatreId: string, lat: number, lng: number, radiusKm: number = 5) => {
    const response = await apiClient.get<{ stages: Stage[] }>(`/theatres/${theatreId}/stages/nearby`, {
      params: { lat, lng, radius_m: radiusKm * 1000 },
    });
    return response.data;
  },
};


// -------------------- Gate API --------------------

export const gateApi = {
  /**
   * Slot Gates
   * ✅ P0: slot 只有一个“本小时之门”，后端用两步：
   *  1) GET /slots/{slot_id}/gate -> gate_instance_id
   *  2) GET /gates/{gate_instance_id}/lobby -> GateLobbyResponse
   *  3) 映射为 FE Gate 并返回 {gates:[...]}
   */
  getGates: async (slotId: string) => {
    try {
      const slotGateResp = await apiClient.get<any>(`/slots/${slotId}/gate`);
      const gateId = slotGateResp.data?.gate_instance_id;
      if (!gateId) return { gates: [] as Gate[] };

      const lobbyResp = await apiClient.get<any>(`/gates/${gateId}/lobby`);
      const gate = adaptGateLobbyToGate(lobbyResp.data);

      return { gates: [gate] };
    } catch (e) {
      // slot 可能没有 gate（或未发布）→ 返回空数组即可
      return { gates: [] as Gate[] };
    }
  },

  /**
   * Gate 详情（P0 页面未强依赖）
   * 后端 v1.2 推荐用 /gates/{id}/lobby 或 /gates/{id}/explain
   */
  getGateDetail: async (gateId: string) => {
    const response = await apiClient.get<any>(`/gates/${gateId}/lobby`);
    return adaptGateLobbyToGate(response.data);
  },

  /**
   * 投票
   * ✅ P0: /gates/{id}/vote 仅需要 option_id + ring_level（不需要 amount）
   */
  vote: async (gateId: string, optionId: string, amount: number = 1) => {
    const response = await apiClient.post(`/gates/${gateId}/vote`, {
      option_id: optionId,
      ring_level: 'C',
      // amount 在 BE v1.2 不生效；保留参数仅为兼容现有调用
      _amount_ignored: amount,
    });
    return response.data;
  },

  /**
   * 下注
   * ✅ P0: /gates/{id}/stake（替代 /bet）
   */
  bet: async (gateId: string, optionId: string, amount: number) => {
    const response = await apiClient.post(`/gates/${gateId}/stake`, {
      option_id: optionId,
      currency: 'ticket',
      amount,
      ring_level: 'C',
    });
    return response.data;
  },

  /**
   * 提交证物
   * ✅ P0: /gates/{id}/evidence 单次只收一条 evidence_instance_id
   * 现有前端传数组 → 这里逐条提交（并返回聚合结果）
   */
  submitEvidence: async (gateId: string, evidenceIds: string[]) => {
    const submitted: string[] = [];
    const failed: { evidence_id: string; error: any }[] = [];

    await Promise.all(
      evidenceIds.map(async (eid) => {
        try {
          await apiClient.post(`/gates/${gateId}/evidence`, {
            evidence_instance_id: eid,
          });
          submitted.push(eid);
        } catch (err) {
          failed.push({ evidence_id: eid, error: err });
        }
      })
    );

    return {
      success: failed.length === 0,
      submitted,
      failed,
    };
  },

  /**
   * Explain Card（暂保留原路径，后端需要补齐 v1.2 ExplainCard 结构）
   */
  getExplainCard: async (gateId: string) => {
    const response = await apiClient.get<ExplainCard>(`/gates/${gateId}/explain`);
    return response.data;
  },

  claimRewards: async (gateId: string) => {
    const response = await apiClient.post(`/gates/${gateId}/claim-rewards`);
    return response.data;
  },

  /**
   * 参与信息
   * 后端 v1.2: /gates/{id}/participation
   */
  getMyParticipation: async (gateId: string) => {
    const response = await apiClient.get<any>(`/gates/${gateId}/participation`);
    return response.data as GateParticipation;
  },
};


// -------------------- Evidence API --------------------

export const evidenceApi = {
  /**
   * 我的证物列表
   * ✅ P0: 改用 /me/evidence?limit&offset（Evidence v1.2）
   * 并映射为 FE 的 PaginatedResponse<Evidence>
   */
  getMyEvidences: async (page: number = 1, pageSize: number = 20) => {
    try {
      const limit = pageSize;
      const offset = Math.max(0, (page - 1) * pageSize);

      const response = await apiClient.get<any>('/me/evidence', {
        params: { limit, offset },
      });

      const userId = response.data?.user_id || '';
      const total = Number(response.data?.total_count || 0);
      const evidenceRaw = response.data?.evidence || [];

      const items: Evidence[] = Array.isArray(evidenceRaw)
        ? evidenceRaw.map((e: any) => adaptEvidenceResponse(e, userId))
        : [];

      return {
        items,
        total: total || items.length,
        page,
        page_size: pageSize,
        has_more: offset + items.length < (total || items.length),
      } as PaginatedResponse<Evidence>;
    } catch (e) {
      return {
        items: [],
        total: 0,
        page,
        page_size: pageSize,
        has_more: false,
      } as PaginatedResponse<Evidence>;
    }
  },

  /**
   * Evidence 详情（P1）
   * 后端 v1.2: /evidence/{instance_id}
   */
  getEvidenceDetail: async (evidenceId: string) => {
    const response = await apiClient.get<any>(`/evidence/${evidenceId}`);
    // 单条详情接口目前返回 EvidenceResponse（缺少 user_id），这里保留原样，后续可做适配
    return response.data as Evidence;
  },

  /**
   * 收集证物（P1）
   * 后端 v1.2 暂无 /scenes/{scene}/collect-evidence 通用接口，先保留
   */
  collectEvidence: async (sceneId: string) => {
    const response = await apiClient.post<Evidence>(`/scenes/${sceneId}/collect-evidence`);
    return response.data;
  },

  /**
   * 验证证物（P1）
   * 后端 v1.2: POST /evidence/{instance_id}/verify
   */
  verifyEvidence: async (evidenceId: string) => {
    const response = await apiClient.post(`/evidence/${evidenceId}/verify`);
    return response.data;
  },
};


// -------------------- Archive API --------------------

export const archiveApi = {
  getMyArchive: async (page: number = 1, limit: number = 20, threadId?: string) => {
    const response = await apiClient.get<Archive>('/users/me/archive', {
      params: { page, limit, thread_id: threadId },
    });
    return response.data;
  },

  getEchoes: async (page: number = 1, limit: number = 20, threadId?: string, result?: string) => {
    const response = await apiClient.get<{ echoes: any[]; total: number }>('/users/me/archive/echoes', {
      params: { page, limit, thread_id: threadId, result },
    });
    return response.data;
  },

  getEvidences: async (page: number = 1, limit: number = 20, grade?: string, type?: string) => {
    const response = await apiClient.get<{ evidences: any[]; total: number }>('/users/me/archive/evidences', {
      params: { page, limit, grade, type },
    });
    return response.data;
  },

  getStats: async () => {
    const response = await apiClient.get<any>('/users/me/archive/stats');
    return response.data;
  },

  getGateHistory: async (page: number = 1, pageSize: number = 20) => {
    const response = await apiClient.get<PaginatedResponse<any>>('/archive/gates', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  getEchoHistory: async () => {
    const response = await apiClient.get<{ echoes: any[] }>('/archive/echoes');
    return response.data;
  },
};

// -------------------- Crew API --------------------

export const crewApi = {
  getMyCrew: async () => {
    const response = await apiClient.get<Crew>('/crews/mine');
    return response.data;
  },

  createCrew: async (name: string, description?: string) => {
    const response = await apiClient.post<Crew>('/crews', { name, description });
    return response.data;
  },

  joinCrew: async (crewId: string) => {
    const response = await apiClient.post(`/crews/${crewId}/join`);
    return response.data;
  },

  leaveCrew: async (crewId: string) => {
    const response = await apiClient.post(`/crews/${crewId}/leave`);
    return response.data;
  },

  shareEvidence: async (crewId: string, evidenceId: string) => {
    const response = await apiClient.post(`/crews/${crewId}/share-evidence`, {
      evidence_id: evidenceId,
    });
    return response.data;
  },

  getSharedEvidences: async (crewId: string) => {
    const response = await apiClient.get<{ evidences: Evidence[] }>(`/crews/${crewId}/shared-evidences`);
    return response.data;
  },
};

// -------------------- Storyline API --------------------

export const storylineApi = {
  getMyStorylines: async () => {
    const response = await apiClient.get<{ storylines: Storyline[] }>('/storylines/mine');
    return response.data;
  },

  followStoryline: async (storylineId: string) => {
    const response = await apiClient.post(`/storylines/${storylineId}/follow`);
    return response.data;
  },

  unfollowStoryline: async (storylineId: string) => {
    const response = await apiClient.post(`/storylines/${storylineId}/unfollow`);
    return response.data;
  },
};

// -------------------- Location API --------------------

export const locationApi = {
  evaluateRing: async (theatreId: string, stageId: string, lat: number, lng: number) => {
    const response = await apiClient.post<{ ring: RingLevel; distance_km: number }>(`/theatres/${theatreId}/evaluate-ring`, {
      stage_id: stageId,
      lat,
      lng,
    });
    return response.data;
  },

  updateLocation: async (lat: number, lng: number) => {
    const response = await apiClient.post('/location/update', { lat, lng });
    return response.data;
  },
};

// -------------------- Scene API --------------------

export const sceneApi = {
  getSceneDetail: async (sceneId: string) => {
    const response = await apiClient.get<Scene>(`/scenes/${sceneId}`);
    return response.data;
  },

  collectEvidence: async (sceneId: string) => {
    const response = await apiClient.post<Evidence>(`/scenes/${sceneId}/collect-evidence`);
    return response.data;
  },
};

// -------------------- Realtime API --------------------

export const realtimeApi = {
  getWebSocketUrl: (theatreId: string) => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || window.location.host;
    return `${wsProtocol}//${host}/v1/realtime/ws/${theatreId}`;
  },

  getSSEUrl: (theatreId: string) => {
    return `${API_BASE_URL}/realtime/sse/${theatreId}`;
  },
};

// -------------------- Experience Loop API --------------------

export const experienceLoopApi = {
  // 获取追证任务
  getActiveHunts: async (stageId?: string, threadId?: string, difficulty?: string) => {
    const response = await apiClient.get<{ hunts: any[]; total_active: number }>('/evidence-hunts/active', {
      params: { stage_id: stageId, thread_id: threadId, difficulty },
    });
    return response.data;
  },

  // 获取复访建议
  getRevisitSuggestions: async (priority?: string, reasonType?: string) => {
    const response = await apiClient.get<{ suggestions: any[] }>('/revisit-suggestions', {
      params: { priority, reason_type: reasonType },
    });
    return response.data;
  },
};

// -------------------- Map API --------------------

export const mapApi = {
  getStages: async (lat?: number, lng?: number, radius: number = 5000) => {
    const response = await apiClient.get<{ stages: any[]; regions: any[]; user_location: any }>('/map/stages', {
      params: { lat, lng, radius },
    });
    return response.data;
  },

  getRegions: async () => {
    const response = await apiClient.get<{ regions: any[] }>('/map/regions');
    return response.data;
  },
};

export default apiClient;
