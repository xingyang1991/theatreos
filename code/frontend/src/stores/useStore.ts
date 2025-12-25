// ============================================
// TheatreOS 全局状态管理 (Zustand)
// ============================================

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  User,
  Theatre,
  Slot,
  Stage,
  Gate,
  Evidence,
  Crew,
  Storyline,
  RingLevel,
  SlotPhase,
  RealtimeEvent,
} from '@/types';

// -------------------- Auth Store --------------------

interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,
      
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        if (token) {
          localStorage.setItem('theatreos_token', token);
        } else {
          localStorage.removeItem('theatreos_token');
        }
        set({ token });
      },
      setLoading: (isLoading) => set({ isLoading }),
      logout: () => {
        localStorage.removeItem('theatreos_token');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'theatreos-auth',
      partialize: (state) => ({ token: state.token }),
    }
  )
);

// -------------------- Theatre Store --------------------

interface TheatreStore {
  currentTheatre: Theatre | null;
  currentSlot: Slot | null;
  currentPhase: SlotPhase;
  phaseEndTime: Date | null;
  stages: Stage[];
  gates: Gate[];
  
  setCurrentTheatre: (theatre: Theatre | null) => void;
  setCurrentSlot: (slot: Slot | null) => void;
  setCurrentPhase: (phase: SlotPhase) => void;
  setPhaseEndTime: (time: Date | null) => void;
  setStages: (stages: Stage[]) => void;
  setGates: (gates: Gate[]) => void;
  updateGate: (gateId: string, updates: Partial<Gate>) => void;
}

export const useTheatreStore = create<TheatreStore>((set) => ({
  currentTheatre: null,
  currentSlot: null,
  currentPhase: 'watching',
  phaseEndTime: null,
  stages: [],
  gates: [],
  
  setCurrentTheatre: (currentTheatre) => set({ currentTheatre }),
  setCurrentSlot: (currentSlot) => set({ currentSlot }),
  setCurrentPhase: (currentPhase) => set({ currentPhase }),
  setPhaseEndTime: (phaseEndTime) => set({ phaseEndTime }),
  setStages: (stages) => set({ stages }),
  setGates: (gates) => set({ gates }),
  updateGate: (gateId, updates) => set((state) => ({
    gates: state.gates.map((g) => g.gate_id === gateId ? { ...g, ...updates } : g),
  })),
}));

// -------------------- Location Store --------------------

interface LocationStore {
  currentRing: RingLevel;
  latitude: number | null;
  longitude: number | null;
  locationError: string | null;
  isLocationEnabled: boolean;
  
  setCurrentRing: (ring: RingLevel) => void;
  setLocation: (coords: { latitude: number; longitude: number }) => void;
  setLocationError: (error: string | null) => void;
  setLocationEnabled: (enabled: boolean) => void;
}

export const useLocationStore = create<LocationStore>((set) => ({
  currentRing: 'C',
  latitude: null,
  longitude: null,
  locationError: null,
  isLocationEnabled: false,
  
  setCurrentRing: (currentRing) => set({ currentRing }),
  setLocation: (coords) => set({ latitude: coords.latitude, longitude: coords.longitude, locationError: null }),
  setLocationError: (locationError) => set({ locationError }),
  setLocationEnabled: (isLocationEnabled) => set({ isLocationEnabled }),
}));

// -------------------- Evidence Store --------------------

interface EvidenceStore {
  myEvidences: Evidence[];
  selectedEvidences: string[];
  
  setMyEvidences: (evidences: Evidence[]) => void;
  addEvidence: (evidence: Evidence) => void;
  toggleSelectEvidence: (evidenceId: string) => void;
  clearSelectedEvidences: () => void;
}

export const useEvidenceStore = create<EvidenceStore>((set) => ({
  myEvidences: [],
  selectedEvidences: [],
  
  setMyEvidences: (myEvidences) => set({ myEvidences }),
  addEvidence: (evidence) => set((state) => ({
    myEvidences: [evidence, ...state.myEvidences],
  })),
  toggleSelectEvidence: (evidenceId) => set((state) => ({
    selectedEvidences: state.selectedEvidences.includes(evidenceId)
      ? state.selectedEvidences.filter((id) => id !== evidenceId)
      : [...state.selectedEvidences, evidenceId],
  })),
  clearSelectedEvidences: () => set({ selectedEvidences: [] }),
}));

// -------------------- Crew Store --------------------

interface CrewStore {
  myCrew: Crew | null;
  onlineMembers: string[];
  
  setMyCrew: (crew: Crew | null) => void;
  setOnlineMembers: (members: string[]) => void;
  updateMemberStatus: (userId: string, isOnline: boolean) => void;
}

export const useCrewStore = create<CrewStore>((set) => ({
  myCrew: null,
  onlineMembers: [],
  
  setMyCrew: (myCrew) => set({ myCrew }),
  setOnlineMembers: (onlineMembers) => set({ onlineMembers }),
  updateMemberStatus: (userId, isOnline) => set((state) => ({
    onlineMembers: isOnline
      ? [...state.onlineMembers, userId]
      : state.onlineMembers.filter((id) => id !== userId),
  })),
}));

// -------------------- Storyline Store --------------------

interface StorylineStore {
  followedStorylines: Storyline[];
  
  setFollowedStorylines: (storylines: Storyline[]) => void;
  addStoryline: (storyline: Storyline) => void;
  removeStoryline: (storylineId: string) => void;
}

export const useStorylineStore = create<StorylineStore>((set) => ({
  followedStorylines: [],
  
  setFollowedStorylines: (followedStorylines) => set({ followedStorylines }),
  addStoryline: (storyline) => set((state) => ({
    followedStorylines: [...state.followedStorylines, storyline],
  })),
  removeStoryline: (storylineId) => set((state) => ({
    followedStorylines: state.followedStorylines.filter((s) => s.storyline_id !== storylineId),
  })),
}));

// -------------------- Realtime Store --------------------

interface RealtimeStore {
  isConnected: boolean;
  lastEvent: RealtimeEvent | null;
  eventQueue: RealtimeEvent[];
  
  setConnected: (connected: boolean) => void;
  pushEvent: (event: RealtimeEvent) => void;
  clearEventQueue: () => void;
}

export const useRealtimeStore = create<RealtimeStore>((set) => ({
  isConnected: false,
  lastEvent: null,
  eventQueue: [],
  
  setConnected: (isConnected) => set({ isConnected }),
  pushEvent: (event) => set((state) => ({
    lastEvent: event,
    eventQueue: [...state.eventQueue.slice(-99), event], // 保留最近100条
  })),
  clearEventQueue: () => set({ eventQueue: [] }),
}));

// -------------------- UI Store --------------------

interface UIStore {
  isSidebarOpen: boolean;
  isGateLobbyOpen: boolean;
  activeModal: string | null;
  toasts: Toast[];
  
  toggleSidebar: () => void;
  setGateLobbyOpen: (open: boolean) => void;
  openModal: (modalId: string) => void;
  closeModal: () => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

interface Toast {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  duration?: number;
}

// 为了兼容性，添加 useUserStore 别名
export const useUserStore = useAuthStore;

export const useUIStore = create<UIStore>((set) => ({
  isSidebarOpen: false,
  isGateLobbyOpen: false,
  activeModal: null,
  toasts: [],
  
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setGateLobbyOpen: (isGateLobbyOpen) => set({ isGateLobbyOpen }),
  openModal: (activeModal) => set({ activeModal }),
  closeModal: () => set({ activeModal: null }),
  addToast: (toast) => set((state) => ({
    toasts: [...state.toasts, { ...toast, id: Date.now().toString() }],
  })),
  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter((t) => t.id !== id),
  })),
}));
