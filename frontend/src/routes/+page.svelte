<script lang="ts">
  import { onMount } from 'svelte';
  import { userStore, loadingUser, addToast } from '$lib/stores';
  import { api } from '$lib/api';
  import type { StatsSummary, Workout, GoalItem, ExerciseItem } from '$lib/types';
  import QuickLogModal from '$lib/components/QuickLogModal.svelte';
  import LogWorkoutModal from '$lib/components/LogWorkoutModal.svelte';
  import GoalProgressCard from '$lib/components/GoalProgressCard.svelte';

  let stats = $state<StatsSummary | null>(null);
  let todayWorkout = $state<Workout | null>(null);
  let recentWorkouts = $state<Workout[]>([]);
  let goals = $state<GoalItem[]>([]);
  let exercises = $state<ExerciseItem[]>([]);
  let isLoadingData = $state(true);

  // Modals state
  let isQuickLogOpen = $state(false);
  let quickLogDefaultEx = $state('Push-ups');
  let isLogWorkoutOpen = $state(false);

  let pushupPct = $derived(
    Math.min(100, Math.round(((stats?.today.pushups || 0) / ($userStore?.preferences?.daily_pushup_target || 100)) * 100))
  );

  let situpPct = $derived(
    Math.min(100, Math.round(((stats?.today.situps || 0) / ($userStore?.preferences?.daily_situp_target || 50)) * 100))
  );

  onMount(async () => {
    await refreshDashboard();
  });

  $effect(() => {
    if ($userStore) {
      refreshDashboard();
    }
  });

  async function refreshDashboard() {
    if (!$userStore) {
      isLoadingData = false;
      return;
    }

    try {
      isLoadingData = true;
      const [statsData, todayData, workoutsData, goalsData, exData] = await Promise.all([
        api.getStatsSummary().catch(() => null),
        api.getTodayWorkout().catch(() => null),
        api.getWorkouts({}).catch(() => []),
        api.getGoals().catch(() => []),
        api.getExercises().catch(() => [])
      ]);

      stats = statsData;
      todayWorkout = todayData;
      recentWorkouts = (workoutsData || []).slice(0, 5);
      goals = goalsData || [];
      exercises = exData || [];
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingData = false;
    }
  }

  async function directQuickLog(exerciseName: string, reps: number) {
    try {
      await api.quickLog({
        exercise_name: exerciseName,
        reps,
      });
      addToast('Logged! 🔥', `+${reps} ${exerciseName} added to today's workout!`, 'success');
      await refreshDashboard();
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to log reps', 'error');
    }
  }

  function openQuickLog(exercise: string = 'Push-ups') {
    quickLogDefaultEx = exercise;
    isQuickLogOpen = true;
  }

  async function handleDemoLogin() {
    try {
      await api.demoLogin();
      addToast('Welcome Athlete!', 'Signed in with demo profile with sample data.', 'success');
      await refreshDashboard();
    } catch (e: any) {
      addToast('Error', e.message || 'Demo login failed', 'error');
    }
  }
</script>

<div class="container dashboard-container">
  {#if $loadingUser}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading your training center...</p>
    </div>
  {:else if !$userStore}
    <!-- Logged out Hero View -->
    <div class="hero-card glass-card animate-pop-in">
      <div class="hero-badge">
        <span class="badge badge-emerald">⚡ Full-Stack Workout Tracking</span>
      </div>
      <h1 class="hero-title">Track Every Push-up.<br/><span class="highlight">Conquer Every Goal.</span></h1>
      <p class="hero-sub">
        Frictionless rep logging for push-ups, sit-ups, pull-ups and core workouts. Set daily targets, build consistency streaks, and analyze your progress with detailed analytics.
      </p>

      <div class="hero-actions">
        <a href="/login" class="btn btn-primary btn-lg">
          <span>Sign In with Google</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </a>
        <button class="btn btn-secondary btn-lg" onclick={handleDemoLogin}>
          <span>⚡ Try Instant Demo</span>
        </button>
      </div>

      <!-- Feature preview grid -->
      <div class="feature-grid">
        <div class="feature-box">
          <span class="feature-icon">🔥</span>
          <h4>One-Tap Logging</h4>
          <p>Instantly log +10, +25, or +50 reps with zero friction.</p>
        </div>
        <div class="feature-box">
          <span class="feature-icon">🎯</span>
          <h4>Daily & Weekly Targets</h4>
          <p>Stay accountable with live progress bars and reminders.</p>
        </div>
        <div class="feature-box">
          <span class="feature-icon">📈</span>
          <h4>Personal Records & Stats</h4>
          <p>Track your PRs, volume trends, and active workout streaks.</p>
        </div>
      </div>
    </div>
  {:else}
    <!-- Logged In Dashboard View -->
    <!-- Top Welcome & Streak Banner -->
    <div class="welcome-banner glass-card animate-pop-in">
      <div class="banner-left">
        <h2 class="welcome-heading">Welcome back, <span class="highlight">{$userStore.name.split(' ')[0]}</span>! 💪</h2>
        <p class="welcome-sub">Let's hit today's targets and keep the momentum alive.</p>
      </div>
      <div class="streak-widget">
        <div class="streak-flame flame-animated">🔥</div>
        <div class="streak-details">
          <span class="streak-count">{stats?.current_streak_days || 0} DAY STREAK</span>
          <span class="streak-sub">Longest: {stats?.longest_streak_days || 0} days</span>
        </div>
      </div>
    </div>

    <!-- Quick Logging Power Station -->
    <div class="quick-station glass-card animate-pop-in">
      <div class="station-header">
        <div class="station-title-group">
          <h3 class="station-title">⚡ Quick Log Station</h3>
          <span class="station-sub">1-Tap instant rep tracking to today's workout</span>
        </div>
        <div class="station-header-actions">
          <button class="btn btn-outline btn-sm" onclick={() => openQuickLog('Push-ups')}>
            + Custom Reps
          </button>
          <button class="btn btn-primary btn-sm" onclick={() => isLogWorkoutOpen = true}>
            🏋️ Log Full Workout
          </button>
        </div>
      </div>

      <div class="quick-buttons-grid">
        <!-- Push-ups Quick Group -->
        <div class="exercise-quick-card">
          <div class="quick-card-top">
            <span class="quick-ex-name">Push-ups</span>
            <span class="badge badge-emerald">Today: {stats?.today.pushups || 0}</span>
          </div>
          <div class="quick-btn-row">
            <button class="btn-rep-fast" onclick={() => directQuickLog('Push-ups', 10)}>+10</button>
            <button class="btn-rep-fast" onclick={() => directQuickLog('Push-ups', 25)}>+25</button>
            <button class="btn-rep-fast" onclick={() => directQuickLog('Push-ups', 50)}>+50</button>
            <button class="btn-rep-fast btn-custom" onclick={() => openQuickLog('Push-ups')}>...</button>
          </div>
        </div>

        <!-- Sit-ups Quick Group -->
        <div class="exercise-quick-card">
          <div class="quick-card-top">
            <span class="quick-ex-name">Sit-ups</span>
            <span class="badge badge-cyan">Today: {stats?.today.situps || 0}</span>
          </div>
          <div class="quick-btn-row">
            <button class="btn-rep-fast cyan" onclick={() => directQuickLog('Sit-ups', 10)}>+10</button>
            <button class="btn-rep-fast cyan" onclick={() => directQuickLog('Sit-ups', 25)}>+25</button>
            <button class="btn-rep-fast cyan" onclick={() => directQuickLog('Sit-ups', 50)}>+50</button>
            <button class="btn-rep-fast cyan btn-custom" onclick={() => openQuickLog('Sit-ups')}>...</button>
          </div>
        </div>

        <!-- Pull-ups / Squats Quick Group -->
        <div class="exercise-quick-card">
          <div class="quick-card-top">
            <span class="quick-ex-name">Pull-ups / Squats</span>
            <span class="badge badge-amber">Other Reps</span>
          </div>
          <div class="quick-btn-row">
            <button class="btn-rep-fast amber" onclick={() => directQuickLog('Pull-ups', 5)}>+5 Pull</button>
            <button class="btn-rep-fast amber" onclick={() => directQuickLog('Pull-ups', 10)}>+10 Pull</button>
            <button class="btn-rep-fast amber" onclick={() => directQuickLog('Squats', 25)}>+25 Squat</button>
            <button class="btn-rep-fast amber btn-custom" onclick={() => openQuickLog('Squats')}>...</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Today's Scoreboard & Metrics -->
    <div class="metrics-grid">
      <div class="metric-card glass-card">
        <div class="metric-icon-box pushups-icon">💪</div>
        <div class="metric-data">
          <span class="metric-label">Push-ups Today</span>
          <div class="metric-value-row">
            <span class="metric-value">{stats?.today.pushups || 0}</span>
            <span class="metric-target">/ {$userStore.preferences?.daily_pushup_target || 100}</span>
          </div>
          <div class="mini-progress-track">
            <div class="mini-progress-fill" style="width: {pushupPct}%;"></div>
          </div>
        </div>
      </div>

      <div class="metric-card glass-card">
        <div class="metric-icon-box situps-icon">🛡️</div>
        <div class="metric-data">
          <span class="metric-label">Sit-ups Today</span>
          <div class="metric-value-row">
            <span class="metric-value">{stats?.today.situps || 0}</span>
            <span class="metric-target">/ {$userStore.preferences?.daily_situp_target || 50}</span>
          </div>
          <div class="mini-progress-track">
            <div class="mini-progress-fill cyan-fill" style="width: {situpPct}%;"></div>
          </div>
        </div>
      </div>

      <div class="metric-card glass-card">
        <div class="metric-icon-box total-icon">⚡</div>
        <div class="metric-data">
          <span class="metric-label">Total Reps Today</span>
          <div class="metric-value-row">
            <span class="metric-value">{stats?.today.total_reps || 0}</span>
            <span class="metric-target">reps</span>
          </div>
          <span class="metric-hint">Lifetime: {stats?.total_reps || 0} reps across {stats?.total_workouts || 0} sessions</span>
        </div>
      </div>
    </div>

    <!-- Active Goals Section -->
    {#if goals.length > 0}
      <div class="section-block">
        <div class="section-header">
          <h3 class="section-title">🎯 Active Goals</h3>
          <a href="/goals" class="section-link">Manage Goals →</a>
        </div>
        <div class="goals-grid">
          {#each goals.slice(0, 3) as goal (goal._id)}
            <GoalProgressCard {goal} onrefresh={refreshDashboard} />
          {/each}
        </div>
      </div>
    {/if}

    <!-- Recent Activity Feed -->
    <div class="section-block">
      <div class="section-header">
        <h3 class="section-title">🏋️ Recent Workouts</h3>
        <a href="/workouts" class="section-link">View All History →</a>
      </div>

      {#if recentWorkouts.length === 0}
        <div class="empty-state glass-card">
          <span>No workouts logged yet. Use the Quick Log station above to record your first set!</span>
        </div>
      {:else}
        <div class="workouts-feed">
          {#each recentWorkouts as w (w._id)}
            <div class="workout-feed-card glass-card">
              <div class="feed-header">
                <div>
                  <h4 class="workout-title">{w.title}</h4>
                  <span class="workout-date">{new Date(w.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                </div>
                {#if w.duration_minutes > 0}
                  <span class="badge badge-emerald">{w.duration_minutes} mins</span>
                {/if}
              </div>

              <div class="feed-exercises">
                {#each w.exercises as ex}
                  <div class="feed-exercise-pill">
                    <span class="ex-name">{ex.exercise_name}:</span>
                    <span class="ex-reps">{ex.total_reps} reps ({ex.sets.length} sets)</span>
                  </div>
                {/each}
              </div>

              {#if w.notes}
                <p class="workout-notes">"{w.notes}"</p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Modals -->
<QuickLogModal
  isOpen={isQuickLogOpen}
  defaultExercise={quickLogDefaultEx}
  {exercises}
  onclose={() => isQuickLogOpen = false}
  onlogged={refreshDashboard}
/>

<LogWorkoutModal
  isOpen={isLogWorkoutOpen}
  exercisesLibrary={exercises}
  onclose={() => isLogWorkoutOpen = false}
  oncreated={refreshDashboard}
/>

<style>
  .dashboard-container {
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 6rem 1rem;
    color: var(--text-muted);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent-emerald);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Hero Section for Logged Out View */
  .hero-card {
    padding: 3.5rem 2rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    border: 1px solid var(--border-emerald);
    background: radial-gradient(circle at top, rgba(16, 185, 129, 0.12), transparent 70%), var(--bg-card);
  }

  .hero-title {
    font-size: 2.8rem;
    font-weight: 900;
    line-height: 1.15;
    letter-spacing: -0.03em;
  }

  .hero-title .highlight {
    background: var(--gradient-emerald-cyan);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .hero-sub {
    max-width: 650px;
    font-size: 1.1rem;
    color: var(--text-muted);
    line-height: 1.6;
  }

  .hero-actions {
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.25rem;
    width: 100%;
    margin-top: 2rem;
    text-align: left;
  }

  .feature-box {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1.25rem;
  }

  .feature-icon {
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
    display: inline-block;
  }

  .feature-box h4 {
    font-size: 1.05rem;
    margin-bottom: 0.25rem;
    color: var(--text-main);
  }

  .feature-box p {
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  /* Logged In Dashboard Styles */
  .welcome-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 1.75rem;
    flex-wrap: wrap;
    gap: 1rem;
    background: linear-gradient(135deg, rgba(22, 30, 49, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
  }

  .welcome-heading {
    font-size: 1.5rem;
    font-weight: 800;
  }

  .welcome-heading .highlight {
    color: var(--accent-emerald-light);
  }

  .welcome-sub {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
  }

  .streak-widget {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 0.65rem 1.1rem;
    border-radius: var(--radius-md);
  }

  .streak-flame {
    font-size: 2rem;
  }

  .streak-details {
    display: flex;
    flex-direction: column;
  }

  .streak-count {
    font-size: 1.05rem;
    font-weight: 800;
    color: #fbbf24;
    letter-spacing: 0.02em;
  }

  .streak-sub {
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  /* Quick Log Station */
  .quick-station {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    border: 1px solid rgba(16, 185, 129, 0.2);
  }

  .station-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .station-title {
    font-size: 1.25rem;
    font-weight: 800;
  }

  .station-sub {
    font-size: 0.85rem;
    color: var(--text-dim);
  }

  .station-header-actions {
    display: flex;
    gap: 0.5rem;
  }

  .quick-buttons-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }

  .exercise-quick-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .quick-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .quick-ex-name {
    font-weight: 700;
    font-size: 1rem;
  }

  .quick-btn-row {
    display: flex;
    gap: 0.5rem;
  }

  .btn-rep-fast {
    flex: 1;
    padding: 0.65rem 0;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: var(--accent-emerald-light);
    border-radius: var(--radius-sm);
    font-weight: 800;
    font-size: 0.95rem;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .btn-rep-fast:hover {
    background: var(--accent-emerald);
    color: #041212;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
  }

  .btn-rep-fast.cyan {
    background: rgba(6, 182, 212, 0.12);
    border-color: rgba(6, 182, 212, 0.3);
    color: var(--accent-cyan-light);
  }
  .btn-rep-fast.cyan:hover {
    background: var(--accent-cyan);
    color: #041212;
    box-shadow: 0 4px 12px rgba(6, 182, 212, 0.4);
  }

  .btn-rep-fast.amber {
    background: rgba(245, 158, 11, 0.12);
    border-color: rgba(245, 158, 11, 0.3);
    color: #fbbf24;
  }
  .btn-rep-fast.amber:hover {
    background: var(--accent-amber);
    color: #041212;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
  }

  .btn-custom {
    flex: 0 0 42px;
  }

  /* Metrics Grid */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.25rem;
  }

  .metric-card {
    padding: 1.25rem;
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .metric-icon-box {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    flex-shrink: 0;
  }
  .pushups-icon { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); }
  .situps-icon { background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.3); }
  .total-icon { background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); }

  .metric-data {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .metric-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .metric-value-row {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
  }

  .metric-value {
    font-size: 1.75rem;
    font-weight: 900;
    color: var(--text-main);
  }

  .metric-target {
    font-size: 0.85rem;
    color: var(--text-dim);
  }

  .metric-hint {
    font-size: 0.72rem;
    color: var(--text-dim);
  }

  .mini-progress-track {
    width: 100%;
    height: 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-full);
    overflow: hidden;
    margin-top: 0.35rem;
  }

  .mini-progress-fill {
    height: 100%;
    background: var(--accent-emerald);
    border-radius: var(--radius-full);
  }

  .cyan-fill {
    background: var(--accent-cyan);
  }

  /* Goals & Feed Sections */
  .section-block {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .section-title {
    font-size: 1.25rem;
    font-weight: 800;
  }

  .section-link {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--accent-emerald-light);
  }
  .section-link:hover {
    text-decoration: underline;
  }

  .goals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }

  .workouts-feed {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .workout-feed-card {
    padding: 1.15rem 1.35rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .feed-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .workout-title {
    font-size: 1.05rem;
    font-weight: 700;
  }

  .workout-date {
    font-size: 0.8rem;
    color: var(--text-dim);
  }

  .feed-exercises {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .feed-exercise-pill {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    padding: 0.3rem 0.65rem;
    border-radius: var(--radius-sm);
    font-size: 0.82rem;
    display: flex;
    gap: 0.35rem;
  }

  .ex-name {
    font-weight: 700;
    color: var(--text-main);
  }

  .ex-reps {
    color: var(--accent-emerald-light);
    font-weight: 600;
  }

  .workout-notes {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-style: italic;
  }

  .empty-state {
    padding: 2.5rem;
    text-align: center;
    color: var(--text-dim);
    font-size: 0.95rem;
  }

  @media (max-width: 640px) {
    .hero-title {
      font-size: 2.1rem;
    }
  }
</style>
