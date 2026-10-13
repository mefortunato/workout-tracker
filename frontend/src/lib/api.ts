import type {
  User,
  Workout,
  WorkoutCreate,
  QuickLogRequest,
  ExerciseItem,
  GoalItem,
  StatsSummary,
  PersonalRecord,
  ChartDay,
} from './types';

const API_BASE = '/api';

function getToken(): string | null {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
}

export function setToken(token: string | null) {
  if (typeof localStorage !== 'undefined') {
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include', // sends cookies
  });

  if (!res.ok) {
    if (res.status === 401 && endpoint !== '/auth/me' && endpoint !== '/auth/config' && endpoint !== '/auth/login') {
      setToken(null);
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      // ignore
    }
    throw new Error(errorDetail || `Request failed with status ${res.status}`);
  }

  if (res.status === 204) {
    return null as T;
  }

  return res.json();
}

// Auth API
export const api = {
  getAuthConfig: () => request<{ google_client_id: string; google_auth_enabled: boolean; dev_login_enabled: boolean }>('/auth/config'),
  
  loginWithEmail: async (email: string, password: string) => {
    const data = await request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },

  registerWithEmail: async (email: string, password: string, name: string) => {
    const data = await request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    setToken(data.access_token);
    return data;
  },

  demoLogin: async () => {
    const data = await request<{ access_token: string; user: User }>('/auth/demo-login', {
      method: 'POST',
    });
    setToken(data.access_token);
    return data;
  },

  verifyGoogleToken: async (credential: string) => {
    const data = await request<{ access_token: string; user: User }>('/auth/google/verify', {
      method: 'POST',
      body: JSON.stringify({ credential }),
    });
    setToken(data.access_token);
    return data;
  },

  getCurrentUser: () => request<User>('/auth/me'),

  logout: async () => {
    try {
      await request('/auth/logout', { method: 'POST' });
    } finally {
      setToken(null);
    }
  },

  updatePreferences: (prefs: Partial<User['preferences']>) =>
    request<User>('/auth/preferences', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    }),

  // Workouts API
  getWorkouts: (params: { startDate?: string; endDate?: string; exerciseName?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.startDate) search.set('start_date', params.startDate);
    if (params.endDate) search.set('end_date', params.endDate);
    if (params.exerciseName) search.set('exercise_name', params.exerciseName);
    const query = search.toString() ? `?${search.toString()}` : '';
    return request<Workout[]>(`/workouts${query}`);
  },

  getTodayWorkout: () => request<Workout | null>('/workouts/today'),

  createWorkout: (workout: WorkoutCreate) =>
    request<Workout>('/workouts', {
      method: 'POST',
      body: JSON.stringify(workout),
    }),

  quickLog: (log: QuickLogRequest) =>
    request<Workout>('/workouts/quick-log', {
      method: 'POST',
      body: JSON.stringify(log),
    }),

  updateWorkout: (id: string, workout: Partial<WorkoutCreate>) =>
    request<Workout>(`/workouts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(workout),
    }),

  deleteWorkout: (id: string) =>
    request<void>(`/workouts/${id}`, { method: 'DELETE' }),

  // Exercises API
  getExercises: () => request<ExerciseItem[]>('/exercises'),

  createExercise: (ex: { name: string; category: string; type: string; description?: string }) =>
    request<ExerciseItem>('/exercises', {
      method: 'POST',
      body: JSON.stringify(ex),
    }),

  deleteExercise: (id: string) =>
    request<void>(`/exercises/${id}`, { method: 'DELETE' }),

  // Stats API
  getStatsSummary: () => request<StatsSummary>('/stats/summary'),

  getPRs: () => request<PersonalRecord[]>('/stats/prs'),

  getChartData: (days: number = 14) =>
    request<ChartDay[]>(`/stats/chart-data?days=${days}`),

  // Goals API
  getGoals: () => request<GoalItem[]>('/goals'),

  createGoal: (goal: { title: string; exercise_name?: string; period: string; target_value: number; unit: string }) =>
    request<GoalItem>('/goals', {
      method: 'POST',
      body: JSON.stringify(goal),
    }),

  updateGoal: (id: string, goal: Partial<GoalItem>) =>
    request<GoalItem>(`/goals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(goal),
    }),

  deleteGoal: (id: string) =>
    request<void>(`/goals/${id}`, { method: 'DELETE' }),
};
