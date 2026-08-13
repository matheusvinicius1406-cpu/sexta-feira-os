import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface KernelStatus {
  connected: boolean
  brainOnline: boolean
  version: string
}

export interface MemoryNode {
  id: string
  title: string
  kind: string
  importance: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  id: string
}

export interface AppState {
  // Auth
  token: string | null
  ownerId: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void

  // Kernel connection
  kernelUrl: string
  kernelStatus: KernelStatus
  setKernelUrl: (url: string) => void
  setKernelStatus: (status: KernelStatus) => void

  // Chat
  messages: ChatMessage[]
  addMessage: (msg: { role: 'user' | 'assistant'; content: string }) => void
  clearMessages: () => void
  isProcessing: boolean
  setProcessing: (v: boolean) => void

  // Memory
  memories: MemoryNode[]
  setMemories: (m: MemoryNode[]) => void

  // UI
  activePanel: 'chat' | 'memory' | 'security' | 'automations' | null
  setActivePanel: (p: 'chat' | 'memory' | 'security' | 'automations' | null) => void
  brainActivity: number // 0-1 normalized activity
  setBrainActivity: (v: number) => void

  // HUD live data
  brainHistory: number[] // last 60 activity samples
  pushBrainActivity: (v: number) => void
  dataStream: { time: string; label: string; value: string }[]
  pushDataStream: (label: string, value: string) => void
  systemMetrics: { cpu: number; memory: number; sessions: number; tokens: number }
  setSystemMetrics: (m: Partial<AppState['systemMetrics']>) => void

  // Audio visualization
  audioAmplitude: number  // 0-1, real-time TTS amplitude
  setAudioAmplitude: (v: number) => void

  // System
  fps: number
  setFps: (v: number) => void
  uptime: number
  tickUptime: () => void
}

/** Hydration flag — set to true after Zustand persist rehydrates from localStorage */
export let storeHydrated = false

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // ── Auth ──────────────────────────────────────────
      token: null,
      ownerId: null,
      isAuthenticated: false,
  login: async (email: string, password: string) => {
    // Uses Vite proxy (/api/v1/auth/login) to avoid CORS
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
        if (!res.ok) throw new Error(`Login falhou: ${res.status}`)
        const data = await res.json()
        set({ token: data.access_token, ownerId: data.owner_id, isAuthenticated: true })
        get().pushDataStream('AUTH', 'Login realizado')
      },
      logout: () => {
        set({
          token: null,
          ownerId: null,
          isAuthenticated: false,
          kernelStatus: { connected: false, brainOnline: false, version: '0.0.0' },
        })
      },

      // ── Kernel ────────────────────────────────────────
      kernelUrl: 'http://127.0.0.1:8000',
      kernelStatus: { connected: false, brainOnline: false, version: '0.0.0' },
      setKernelUrl: (url) => set({ kernelUrl: url }),
      setKernelStatus: (status) => set({ kernelStatus: status }),

      // ── Chat ──────────────────────────────────────────
      messages: [],
      addMessage: (msg) =>
        set((s) => ({
          messages: [
            ...s.messages,
            { ...msg, id: crypto.randomUUID() },
          ].slice(-50), // keep only last 50 messages
        })),
      clearMessages: () => set({ messages: [] }),
      isProcessing: false,
      setProcessing: (v) => set({ isProcessing: v }),

      // ── Memory ────────────────────────────────────────
      memories: [],
      setMemories: (m) => set({ memories: m }),

      // ── UI ────────────────────────────────────────────
      activePanel: null,
      setActivePanel: (p) => set({ activePanel: p }),
      brainActivity: 0.5,
      setBrainActivity: (v) => set({ brainActivity: v }),

      // ── HUD data ──────────────────────────────────────
      brainHistory: Array(60).fill(0.3),
      pushBrainActivity: (v) =>
        set((s) => ({
          brainActivity: v,
          brainHistory: [...s.brainHistory.slice(-59), v],
        })),
      dataStream: [],
      pushDataStream: (label, value) =>
        set((s) => ({
          dataStream: [
            ...s.dataStream.slice(-19),
            { time: new Date().toLocaleTimeString(), label, value },
          ],
        })),
      systemMetrics: { cpu: 0, memory: 0, sessions: 1, tokens: 0 },
      setSystemMetrics: (m) =>
        set((s) => ({ systemMetrics: { ...s.systemMetrics, ...m } })),

      // ── Audio ─────────────────────────────────────────
      audioAmplitude: 0,
      setAudioAmplitude: (v) => set({ audioAmplitude: v }),

      // ── System ────────────────────────────────────────
      fps: 60,
      setFps: (v) => set({ fps: v }),
      uptime: 0,
      tickUptime: () => set((s) => ({ uptime: s.uptime + 1 })),
    }),
    {
      name: 'jarvis-store',
      storage: createJSONStorage(() => localStorage),
      // Persist only auth + config — exclude runtime/volatile data
      partialize: (state) => ({
        token: state.token,
        ownerId: state.ownerId,
        isAuthenticated: state.isAuthenticated,
        kernelUrl: state.kernelUrl,
        messages: state.messages.slice(-50),
        activePanel: state.activePanel,
      }),
      // Merge persisted state on rehydration
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as Partial<AppState>),
      }),
      onRehydrateStorage: () => () => {
        storeHydrated = true
      },
    },
  ),
)
