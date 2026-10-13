export interface UserPreferences {
  weight_unit: 'kg' | 'lbs';
  theme: string;
  daily_pushup_target: number;
  daily_situp_target: number;
}

export interface User {
  _id: string;
  email: string;
  name: string;
  picture?: string;
  preferences: UserPreferences;
  created_at: string;
}

export interface ExerciseSet {
  set_number: number;
  reps: number;
  weight: number;
  duration_seconds: number;
  completed: boolean;
}

export interface WorkoutExercise {
  exercise_id?: string;
  exercise_name: string;
  category: string;
  type: string;
  sets: ExerciseSet[];
  total_reps: number;
  total_volume: number;
}

export interface Workout {
  _id: string;
  user_id: string;
  date: string;
  title: string;
  notes?: string;
  duration_minutes: number;
  exercises: WorkoutExercise[];
  created_at: string;
}

export interface WorkoutCreate {
  date?: string;
  title: string;
  notes?: string;
  duration_minutes: number;
  exercises: WorkoutExercise[];
}

export interface QuickLogRequest {
  exercise_name: string;
  reps: number;
  weight?: number;
  duration_seconds?: number;
  notes?: string;
}

export interface ExerciseItem {
  _id: string;
  name: string;
  category: string;
  type: string;
  description?: string;
  icon?: string;
  is_default: boolean;
  user_id?: string;
}

export interface GoalItem {
  _id: string;
  user_id: string;
  title: string;
  exercise_name?: string;
  period: 'daily' | 'weekly' | 'monthly';
  target_value: number;
  unit: string;
  current_value: number;
  progress_percentage: number;
  is_active: boolean;
  created_at: string;
}

export interface StatsSummary {
  total_workouts: number;
  total_pushups: number;
  total_situps: number;
  total_reps: number;
  total_duration_minutes: number;
  current_streak_days: number;
  longest_streak_days: number;
  today: {
    pushups: number;
    situps: number;
    total_reps: number;
  };
}

export interface PersonalRecord {
  exercise_name: string;
  max_set_reps: number;
  max_daily_reps: number;
  max_weight: number;
  max_duration_seconds: number;
  total_sessions: number;
}

export interface ChartDay {
  date: string;
  pushups: number;
  situps: number;
  other_reps: number;
  total_reps: number;
}

export interface ToastMessage {
  id: string;
  title: string;
  message: string;
  type: 'success' | 'info' | 'error';
}
