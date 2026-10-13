<script lang="ts">
  import { api } from '$lib/api';
  import { addToast } from '$lib/stores';
  import type { ExerciseItem } from '$lib/types';

  let {
    isOpen = false,
    defaultExercise = 'Push-ups',
    exercises = [],
    onclose,
    onlogged
  }: {
    isOpen: boolean;
    defaultExercise?: string;
    exercises?: ExerciseItem[];
    onclose?: () => void;
    onlogged?: (result: any) => void;
  } = $props();

  let selectedExercise = $state(defaultExercise);
  let reps = $state(25);
  let weight = $state(0);
  let notes = $state('');
  let isSubmitting = $state(false);

  $effect(() => {
    if (isOpen) {
      selectedExercise = defaultExercise;
    }
  });

  function addReps(amount: number) {
    reps = Math.max(1, reps + amount);
  }

  function closeModal() {
    onclose?.();
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (reps <= 0) {
      addToast('Invalid Reps', 'Please enter a number of reps greater than 0', 'error');
      return;
    }

    isSubmitting = true;
    try {
      const result = await api.quickLog({
        exercise_name: selectedExercise,
        reps,
        weight: Number(weight) || 0,
        notes: notes.trim()
      });
      addToast('Workout Logged! 🔥', `Added +${reps} ${selectedExercise} to today's workout!`, 'success');
      onlogged?.(result);
      closeModal();
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to log workout', 'error');
    } finally {
      isSubmitting = false;
    }
  }
</script>

{#if isOpen}
  <div
    class="modal-backdrop"
    onclick={closeModal}
    onkeydown={(e) => e.key === 'Escape' && closeModal()}
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
        <h3 class="modal-title">⚡ Quick Log Workout</h3>
        <button class="modal-close-btn" onclick={closeModal}>✕</button>
      </div>

      <form onsubmit={handleSubmit} class="quick-form">
        <!-- Exercise Selection -->
        <div class="form-group">
          <label class="form-label" for="exercise-select">Exercise</label>
          <select id="exercise-select" bind:value={selectedExercise} class="input-field">
            <option value="Push-ups">Push-ups</option>
            <option value="Sit-ups">Sit-ups</option>
            <option value="Pull-ups">Pull-ups</option>
            <option value="Squats">Squats</option>
            <option value="Dips">Dips</option>
            <option value="Burpees">Burpees</option>
            {#each exercises as ex}
              {#if !['Push-ups', 'Sit-ups', 'Pull-ups', 'Squats', 'Dips', 'Burpees'].includes(ex.name)}
                <option value={ex.name}>{ex.name}</option>
              {/if}
            {/each}
          </select>
        </div>

        <!-- Reps Counter with Fast Increment Buttons -->
        <div class="form-group">
          <label class="form-label" for="reps-input">Reps to Log</label>
          <div class="reps-control-row">
            <button type="button" class="btn-rep-step" onclick={() => addReps(-5)}>-5</button>
            <input
              id="reps-input"
              type="number"
              bind:value={reps}
              min="1"
              max="1000"
              class="input-field reps-big-input"
            />
            <button type="button" class="btn-rep-step" onclick={() => addReps(5)}>+5</button>
          </div>

          <div class="quick-presets">
            <button type="button" class="preset-pill" onclick={() => reps = 10}>10</button>
            <button type="button" class="preset-pill" onclick={() => reps = 20}>20</button>
            <button type="button" class="preset-pill" onclick={() => reps = 25}>25</button>
            <button type="button" class="preset-pill" onclick={() => reps = 50}>50</button>
            <button type="button" class="preset-pill" onclick={() => reps = 100}>100</button>
          </div>
        </div>

        <!-- Optional Weight -->
        <div class="form-group">
          <label class="form-label" for="weight-input">Added Weight (kg / lbs, optional)</label>
          <input
            id="weight-input"
            type="number"
            step="0.5"
            bind:value={weight}
            min="0"
            placeholder="0 for bodyweight"
            class="input-field"
          />
        </div>

        <!-- Notes -->
        <div class="form-group">
          <label class="form-label" for="notes-input">Notes (optional)</label>
          <input
            id="notes-input"
            type="text"
            bind:value={notes}
            placeholder="e.g., Strict form, chest to floor"
            class="input-field"
          />
        </div>

        <!-- Actions -->
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={closeModal}>Cancel</button>
          <button type="submit" class="btn btn-primary" disabled={isSubmitting}>
            {#if isSubmitting}
              <span>Logging...</span>
            {:else}
              <span>Log +{reps} {selectedExercise} 🔥</span>
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.25rem;
  }

  .modal-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-main);
  }

  .modal-close-btn {
    color: var(--text-dim);
    font-size: 1.1rem;
    padding: 0.25rem;
    transition: color 0.2s;
  }
  .modal-close-btn:hover {
    color: var(--text-main);
  }

  .quick-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .form-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
  }

  .reps-control-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .reps-big-input {
    text-align: center;
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--accent-emerald-light);
    height: 3.2rem;
  }

  .btn-rep-step {
    width: 3.2rem;
    height: 3.2rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-main);
    font-weight: 700;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }
  .btn-rep-step:hover {
    background: rgba(255, 255, 255, 0.12);
    border-color: var(--border-hover);
  }

  .quick-presets {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.4rem;
  }

  .preset-pill {
    flex: 1;
    padding: 0.45rem 0;
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: var(--radius-sm);
    color: var(--accent-emerald-light);
    font-size: 0.85rem;
    font-weight: 700;
    transition: all 0.2s;
  }
  .preset-pill:hover {
    background: rgba(16, 185, 129, 0.22);
    transform: translateY(-1px);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 0.5rem;
  }
</style>
