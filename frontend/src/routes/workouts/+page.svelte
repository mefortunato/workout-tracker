<script lang="ts">
  import { onMount } from 'svelte';
  import { userStore, addToast } from '$lib/stores';
  import { api } from '$lib/api';
  import type { Workout, ExerciseItem } from '$lib/types';
  import LogWorkoutModal from '$lib/components/LogWorkoutModal.svelte';

  let workouts = $state<Workout[]>([]);
  let exercisesLibrary = $state<ExerciseItem[]>([]);
  let isLoading = $state(true);

  // Filters
  let filterTime = $state('all'); // 'all', '7d', '30d'
  let filterExercise = $state('');
  let searchQuery = $state('');

  let isLogModalOpen = $state(false);

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    isLoading = true;
    try {
      const [wData, exData] = await Promise.all([
        api.getWorkouts({}),
        api.getExercises()
      ]);
      workouts = wData || [];
      exercisesLibrary = exData || [];
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to load workouts', 'error');
    } finally {
      isLoading = false;
    }
  }

  let filteredWorkouts = $derived(
    workouts.filter((w) => {
      // Time filter
      if (filterTime === '7d') {
        const d = new Date(w.date);
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        if (d < weekAgo) return false;
      } else if (filterTime === '30d') {
        const d = new Date(w.date);
        const monthAgo = new Date();
        monthAgo.setDate(monthAgo.getDate() - 30);
        if (d < monthAgo) return false;
      }

      // Exercise filter
      if (filterExercise) {
        const hasEx = w.exercises.some(e => e.exercise_name.toLowerCase() === filterExercise.toLowerCase());
        if (!hasEx) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = w.title.toLowerCase().includes(q);
        const matchNotes = (w.notes || '').toLowerCase().includes(q);
        const matchEx = w.exercises.some(e => e.exercise_name.toLowerCase().includes(q));
        if (!matchTitle && !matchNotes && !matchEx) return false;
      }

      return true;
    })
  );

  async function handleDelete(id: string, title: string) {
    if (!confirm(`Delete workout "${title}"?`)) return;
    try {
      await api.deleteWorkout(id);
      addToast('Workout Deleted', 'Workout log removed.', 'info');
      workouts = workouts.filter(w => w._id !== id);
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to delete workout', 'error');
    }
  }
</script>

<div class="container workouts-container">
  <!-- Top Bar -->
  <div class="page-header">
    <div>
      <h1 class="page-title">🏋️ Workout History</h1>
      <p class="page-sub">Review your past sessions, sets, volume, and notes.</p>
    </div>
    <button class="btn btn-primary" onclick={() => isLogModalOpen = true}>
      <span>+ Log New Workout</span>
    </button>
  </div>

  <!-- Filters Bar -->
  <div class="filters-card glass-card">
    <div class="filter-group">
      <span class="filter-label">Timeframe:</span>
      <div class="pill-group">
        <button
          class="pill-btn"
          class:active={filterTime === 'all'}
          onclick={() => filterTime = 'all'}
        >
          All Time
        </button>
        <button
          class="pill-btn"
          class:active={filterTime === '7d'}
          onclick={() => filterTime = '7d'}
        >
          Last 7 Days
        </button>
        <button
          class="pill-btn"
          class:active={filterTime === '30d'}
          onclick={() => filterTime = '30d'}
        >
          Last 30 Days
        </button>
      </div>
    </div>

    <div class="filter-group">
      <span class="filter-label">Exercise:</span>
      <select bind:value={filterExercise} class="input-field select-filter">
        <option value="">All Exercises</option>
        <option value="Push-ups">Push-ups</option>
        <option value="Sit-ups">Sit-ups</option>
        <option value="Pull-ups">Pull-ups</option>
        <option value="Squats">Squats</option>
        <option value="Dips">Dips</option>
      </select>
    </div>

    <div class="filter-group search-group">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Search workouts or notes..."
        class="input-field search-input"
      />
    </div>
  </div>

  <!-- Workout List -->
  {#if isLoading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading your workouts...</p>
    </div>
  {:else if filteredWorkouts.length === 0}
    <div class="empty-state glass-card">
      <span class="empty-icon">📋</span>
      <h3>No workouts found</h3>
      <p>Try adjusting your filters or record a new session!</p>
      <button class="btn btn-outline" onclick={() => isLogModalOpen = true}>
        Log First Workout
      </button>
    </div>
  {:else}
    <div class="workouts-list">
      {#each filteredWorkouts as w (w._id)}
        {@const totalReps = w.exercises.reduce((sum, e) => sum + e.total_reps, 0)}
        <div class="workout-card glass-card animate-pop-in">
          <div class="workout-card-header">
            <div class="header-main">
              <h3 class="w-title">{w.title}</h3>
              <div class="w-meta">
                <span class="meta-date">
                  📅 {new Date(w.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
                {#if w.duration_minutes > 0}
                  <span class="meta-dot">•</span>
                  <span class="meta-dur">⏱️ {w.duration_minutes} min</span>
                {/if}
              </div>
            </div>

            <div class="header-badges">
              <span class="badge badge-emerald">{totalReps} Total Reps</span>
              <button
                class="btn-delete"
                onclick={() => handleDelete(w._id, w.title)}
                title="Delete workout log"
              >
                ✕
              </button>
            </div>
          </div>

          <!-- Exercises Breakdown -->
          <div class="w-exercises-grid">
            {#each w.exercises as ex}
              <div class="w-exercise-item">
                <div class="ex-item-header">
                  <span class="ex-item-name">{ex.exercise_name}</span>
                  <span class="badge badge-cyan">{ex.total_reps} reps</span>
                </div>
                <div class="sets-chips">
                  {#each ex.sets as s}
                    <div class="set-chip">
                      <span class="set-chip-num">S{s.set_number}:</span>
                      <span class="set-chip-reps">{s.reps}r</span>
                      {#if s.weight > 0}
                        <span class="set-chip-wt">@{s.weight}kg</span>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>

          {#if w.notes}
            <div class="w-notes-box">
              <span class="notes-quote">"{w.notes}"</span>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Modal -->
<LogWorkoutModal
  isOpen={isLogModalOpen}
  {exercisesLibrary}
  onclose={() => isLogModalOpen = false}
  oncreated={loadData}
/>

<style>
  .workouts-container {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 800;
  }

  .page-sub {
    font-size: 0.95rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
  }

  /* Filters */
  .filters-card {
    padding: 1.25rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .filter-label {
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .pill-group {
    display: flex;
    gap: 0.35rem;
    background: rgba(255, 255, 255, 0.04);
    padding: 0.2rem;
    border-radius: var(--radius-sm);
  }

  .pill-btn {
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-muted);
    border-radius: var(--radius-sm);
    transition: all 0.2s;
  }
  .pill-btn:hover {
    color: var(--text-main);
  }
  .pill-btn.active {
    background: var(--accent-emerald);
    color: #041212;
    font-weight: 700;
  }

  .select-filter {
    padding: 0.35rem 0.75rem;
    font-size: 0.85rem;
    width: auto;
  }

  .search-group {
    flex: 1;
    min-width: 200px;
  }

  .search-input {
    padding: 0.45rem 0.85rem;
    font-size: 0.85rem;
  }

  /* Workouts List */
  .workouts-list {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .workout-card {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .workout-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .w-title {
    font-size: 1.25rem;
    font-weight: 800;
  }

  .w-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
  }

  .meta-dot {
    color: var(--text-dim);
  }

  .header-badges {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .btn-delete {
    color: var(--text-dim);
    font-size: 0.95rem;
    padding: 0.3rem;
    border-radius: var(--radius-sm);
    transition: color 0.2s, background 0.2s;
  }
  .btn-delete:hover {
    color: var(--accent-rose);
    background: rgba(244, 63, 94, 0.1);
  }

  /* Exercises Inside Workout */
  .w-exercises-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 0.85rem;
  }

  .w-exercise-item {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .ex-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .ex-item-name {
    font-weight: 700;
    font-size: 0.95rem;
  }

  .sets-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .set-chip {
    background: rgba(255, 255, 255, 0.06);
    padding: 0.2rem 0.45rem;
    border-radius: 4px;
    font-size: 0.78rem;
    display: flex;
    gap: 0.25rem;
  }

  .set-chip-num {
    color: var(--text-dim);
    font-weight: 600;
  }

  .set-chip-reps {
    color: var(--accent-emerald-light);
    font-weight: 700;
  }

  .set-chip-wt {
    color: #fbbf24;
    font-size: 0.72rem;
  }

  .w-notes-box {
    background: rgba(255, 255, 255, 0.02);
    border-left: 3px solid var(--accent-cyan);
    padding: 0.6rem 0.85rem;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  }

  .notes-quote {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-style: italic;
  }

  .loading-state, .empty-state {
    padding: 4rem 1rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    color: var(--text-muted);
  }

  .empty-icon {
    font-size: 3rem;
  }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent-emerald);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
