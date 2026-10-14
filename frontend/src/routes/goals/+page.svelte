<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { addToast } from '$lib/stores';
  import type { GoalItem, ExerciseItem } from '$lib/types';
  import GoalProgressCard from '$lib/components/GoalProgressCard.svelte';

  let goals = $state<GoalItem[]>([]);
  let exercises = $state<ExerciseItem[]>([]);
  let isLoading = $state(true);

  // New Goal modal
  let isAddModalOpen = $state(false);
  let title = $state('Daily 100 Push-ups');
  let exerciseName = $state('Push-ups');
  let period = $state<'daily' | 'weekly' | 'monthly'>('daily');
  let targetValue = $state(100);
  let unit = $state('reps');
  let isSubmitting = $state(false);

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    isLoading = true;
    try {
      const [goalsData, exData] = await Promise.all([
        api.getGoals(),
        api.getExercises()
      ]);
      goals = goalsData || [];
      exercises = exData || [];
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to load goals', 'error');
    } finally {
      isLoading = false;
    }
  }

  async function handleCreateGoal(e: SubmitEvent) {
    e.preventDefault();
    if (!title.trim() || targetValue <= 0) {
      addToast('Invalid Input', 'Please provide a valid goal title and target value.', 'error');
      return;
    }

    isSubmitting = true;
    try {
      const created = await api.createGoal({
        title: title.trim(),
        exercise_name: exerciseName,
        period,
        target_value: Number(targetValue),
        unit
      });
      addToast('Goal Set! 🎯', `Target "${created.title}" is now active!`, 'success');
      goals = [created, ...goals];
      isAddModalOpen = false;
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to create goal', 'error');
    } finally {
      isSubmitting = false;
    }
  }
</script>

<div class="container goals-container">
  <div class="page-header">
    <div>
      <h1 class="page-title">🎯 Training Targets & Goals</h1>
      <p class="page-sub">Set daily and weekly benchmarks for push-ups, sit-ups, and routines.</p>
    </div>
    <button class="btn btn-primary" onclick={() => isAddModalOpen = true}>
      <span>+ Set New Target</span>
    </button>
  </div>

  {#if isLoading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Calculating active target progress...</p>
    </div>
  {:else if goals.length === 0}
    <div class="empty-state glass-card">
      <span class="empty-icon">🎯</span>
      <h3>No active targets yet</h3>
      <p>Set a daily challenge like "100 Push-ups" to stay consistent!</p>
      <button class="btn btn-outline" onclick={() => isAddModalOpen = true}>
        Create First Target
      </button>
    </div>
  {:else}
    <div class="goals-grid">
      {#each goals as goal (goal._id)}
        <GoalProgressCard {goal} onrefresh={loadData} />
      {/each}
    </div>
  {/if}
</div>

<!-- Add Goal Modal -->
{#if isAddModalOpen}
  <div
    class="modal-backdrop"
    onclick={() => isAddModalOpen = false}
    onkeydown={(e) => e.key === 'Escape' && (isAddModalOpen = false)}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <div
      class="modal-content animate-pop-in"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
      role="document"
      tabindex="0"
    >
      <div class="modal-header">
        <h3 class="modal-title">🎯 Set Workout Target</h3>
        <button class="modal-close-btn" onclick={() => isAddModalOpen = false}>✕</button>
      </div>

      <form onsubmit={handleCreateGoal} class="modal-form">
        <div class="form-group">
          <label class="form-label" for="goal-title">Goal Name</label>
          <input
            id="goal-title"
            type="text"
            bind:value={title}
            placeholder="e.g. Daily 100 Push-ups"
            class="input-field"
            required
          />
        </div>

        <div class="grid-row">
          <div class="form-group flex-1">
            <label class="form-label" for="goal-ex">Exercise</label>
            <select id="goal-ex" bind:value={exerciseName} class="input-field">
              <option value="Push-ups">Push-ups</option>
              <option value="Sit-ups">Sit-ups</option>
              <option value="Pull-ups">Pull-ups</option>
              <option value="Squats">Squats</option>
              <option value="Dips">Dips</option>
              {#each exercises as ex}
                {#if !['Push-ups', 'Sit-ups', 'Pull-ups', 'Squats', 'Dips'].includes(ex.name)}
                  <option value={ex.name}>{ex.name}</option>
                {/if}
              {/each}
            </select>
          </div>

          <div class="form-group flex-1">
            <label class="form-label" for="goal-period">Period</label>
            <select id="goal-period" bind:value={period} class="input-field">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </div>

        <div class="grid-row">
          <div class="form-group flex-1">
            <label class="form-label" for="goal-target">Target Count</label>
            <input
              id="goal-target"
              type="number"
              bind:value={targetValue}
              min="1"
              max="10000"
              class="input-field"
              required
            />
          </div>

          <div class="form-group flex-1">
            <label class="form-label" for="goal-unit">Unit</label>
            <select id="goal-unit" bind:value={unit} class="input-field">
              <option value="reps">Reps</option>
              <option value="workouts">Workouts</option>
              <option value="seconds">Seconds (Plank)</option>
            </select>
          </div>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={() => isAddModalOpen = false}>Cancel</button>
          <button type="submit" class="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Set Target 🎯'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .goals-container {
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

  .goals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1.25rem;
  }

  /* Modal Form */
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
  }

  .modal-title {
    font-size: 1.25rem;
    font-weight: 700;
  }

  .modal-close-btn {
    color: var(--text-dim);
    font-size: 1.1rem;
  }

  .modal-form {
    display: flex;
    flex-direction: column;
    gap: 1.15rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .form-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
  }

  .grid-row {
    display: flex;
    gap: 1rem;
  }
  .flex-1 { flex: 1; }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 0.5rem;
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
  .empty-icon { font-size: 3rem; }
  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid var(--border-hover);
    border-top-color: var(--accent-emerald);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
