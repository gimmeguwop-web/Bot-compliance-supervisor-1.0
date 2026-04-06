// Zustand store for application state management
import { create } from 'zustand';
import type { Document, Task, DashboardStats } from '../types';

interface AppState {
  // Documents
  documents: Document[];
  selectedDocument: Document | null;
  
  // Tasks
  activeTasks: Task[];
  
  // UI State
  isUploadModalOpen: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setDocuments: (docs: Document[]) => void;
  setSelectedDocument: (doc: Document | null) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: number, updates: Partial<Task>) => void;
  toggleUploadModal: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  documents: [],
  selectedDocument: null,
  activeTasks: [],
  isUploadModalOpen: false,
  isLoading: false,
  error: null,
  
  // Actions
  setDocuments: (docs) => set({ documents: docs }),
  
  setSelectedDocument: (doc) => set({ selectedDocument: doc }),
  
  addTask: (task) => 
    set((state) => ({ 
      activeTasks: [...state.activeTasks, task] 
    })),
  
  updateTask: (taskId, updates) =>
    set((state) => ({
      activeTasks: state.activeTasks.map((t) =>
        t.id === taskId ? { ...t, ...updates } : t
      ),
    })),
  
  toggleUploadModal: () =>
    set((state) => ({ isUploadModalOpen: !state.isUploadModalOpen })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
}));
