<script lang="ts">
  import { api } from '$lib/api';
  import { addToast } from '$lib/stores';
  import type { ExerciseItem, WorkoutExercise } from '$lib/types';

  let {
    isOpen = false,
    exercisesLibrary = [],
    onclose,
    oncreated
  }: {
    isOpen: boolean;
    exercisesLibrary?: ExerciseItem[];
    onclose?: () => void;
    oncreated?: (created: any) => void;
  } = $props();

  let title = $state('Workout Session');
  let date = $state(new Date().toISOString().substring(0, 16));
  let durationMinutes = $state(30);
  let notes = $state('');
  let isSubmitting = $state(false);

  let workoutExercises: WorkoutExercise[] = $state([
    {
      exercise_name: 'Push-ups',
      category: 'Upper Body',
      type: 'reps',
      sets: [
        { set_number: 1, reps: 25, weight: 0, duration_seconds: 0, completed: true },
        { set_number: 2, reps: 20, weight: 0, duration_seconds: 0, completed: true }
      ],
      total_reps: 45,
      total_volume: 0
    }
  ]);

  function addExercise() {
    workoutExercises = [
      ...workoutExercises,
      {
        exercise_name: 'Sit-ups',
        category: 'Core',
        type: 'reps',
        sets: [{ set_number: 1, reps: 25, weight: 0, duration_seconds: 0, completed: true }],
        total_reps: 25,
        total_volume: 0
      }
    ];
  }

  function removeExercise(index: number) {
    workoutExercises = workoutExercises.filter((_, i) => i !== index);
  }

  function addSet(exIndex: number) {
    const ex = workoutExercises[exIndex];
    const lastSet = ex.sets[ex.sets.length - 1];
    const newSetNum = ex.sets.length + 1;
    ex.sets = [
      ...ex.sets,
      {
        set_number: newSetNum,
        reps: lastSet ? lastSet.reps : 20,
        weight: lastSet ? lastSet.weight : 0,
        duration_seconds: lastSet ? lastSet.duration_seconds : 0,
        completed: true
      }
    ];
    updateTotals(exIndex);
  }

  function removeSet(exIndex: number, setIndex: number) {
    const ex = workoutExercises[exIndex];
    if (ex.sets.length <= 1) return;
    ex.sets = ex.sets.filter((_, i) => i !== setIndex).map((s, idx) => ({ ...s, set_number: idx + 1 }));
    updateTotals(exIndex);
  }

  function updateTotals(exIndex: number) {
    const ex = workoutExercises[exIndex];
    ex.total_reps = ex.sets.reduce((sum, s) => sum + (Number(s.reps) || 0), 0);
    ex.total_volume = ex.sets.reduce((sum, s) => sum + ((Number(s.reps) || 0) * (Number(s.weight) || 0)), 0);
  }

  function closeModal() {
    onclose?.();
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (workoutExercises.length === 0) {
      addToast('No Exercises', 'Add at least one exercise to your workout.', 'error');
      return;
    }

    isSubmitting = true;
    try {
      const created = await api.createWorkout({
        title: title.trim() || 'Workout Session',
        date: new Date(date).toISOString(),
        duration_minutes: Number(durationMinutes) || 0,
        notes: notes.trim(),
        exercises: workoutExercises
      });
      addToast('Workout Saved! 🏆', 'Workout session logged successfully.', 'success');
      oncreated?.(created);
      closeModal();
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to save workout', 'error');
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
      class="modal-content modal-large animate-pop-in"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
      role="document"
      tabindex="0"
    >
      <div class="modal-header">
        <h3 class="modal-title">🏋️ Log Full Workout Session</h3>
        <button class="modal-close-btn" onclick={closeModal}>✕</button>
      </div>

      <form onsubmit={handleSubmit} class="workout-form">
        <!-- Top Metadata Row -->
        <div class="grid-row">
          <div class="form-group flex-2">
            <label class="form-label" for="workout-title">Session Title</label>
            <input
              id="workout-title"
              type="text"
              bind:value={title}
              placeholder="e.g. Morning Push & Abs"
              class="input-field"
              required
            />
          </div>
          <div class="form-group flex-1">
            <label class="form-label" for="workout-duration">Duration (mins)</label>
            <input
              id="workout-duration"
              type="number"
              bind:value={durationMinutes}
              min="1"
              max="600"
              class="input-field"
            />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="workout-date">Date & Time</label>
          <input
            id="workout-date"
            type="datetime-local"
            bind:value={date}
            class="input-field"
          />
        </div>

        <!-- Exercises Section -->
        <div class="exercises-section">
          <div class="section-title-row">
            <h4>Exercises & Sets</h4>
            <button type="button" class="btn btn-outline btn-sm" onclick={addExercise}>
              + Add Exercise
            </button>
          </div>

          <div class="exercises-list">
            {#each workoutExercises as ex, exIdx}
              <div class="exercise-card">
                <div class="exercise-card-header">
                  <div class="exercise-select-wrap">
                    <select
                      bind:value={ex.exercise_name}
                      onchange={() => updateTotals(exIdx)}
                      class="input-field select-exercise"
                    >
                      <option value="Push-ups">Push-ups</option>
                      <option value="Sit-ups">Sit-ups</option>
                      <option value="Pull-ups">Pull-ups</option>
                      <option value="Squats">Squats</option>
                      <option value="Dips">Dips</option>
                      <option value="Plank">Plank</option>
                      <option value="Burpees">Burpees</option>
                      <option value="Bench Press">Bench Press</option>
                      {#each exercisesLibrary as libEx}
                        {#if !['Push-ups', 'Sit-ups', 'Pull-ups', 'Squats', 'Dips', 'Plank', 'Burpees', 'Bench Press'].includes(libEx.name)}
                          <option value={libEx.name}>{libEx.name}</option>
                        {/if}
                      {/each}
                    </select>
                  </div>
                  <div class="header-right">
                    <span class="badge badge-emerald">{ex.total_reps} Reps</span>
                    <button
                      type="button"
                      class="btn-icon-danger"
                      onclick={() => removeExercise(exIdx)}
                      title="Remove Exercise"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <!-- Sets Table -->
                <div class="sets-table">
                  <div class="set-row header-row">
                    <span class="col-num">Set</span>
                    <span class="col-input">Reps</span>
                    <span class="col-input">Weight (kg)</span>
                    <span class="col-action"></span>
                  </div>
                  {#each ex.sets as s, sIdx}
                    <div class="set-row">
                      <span class="col-num set-badge">{s.set_number}</span>
                      <div class="col-input">
                        <input
                          type="number"
                          bind:value={s.reps}
                          oninput={() => updateTotals(exIdx)}
                          min="0"
                          class="input-field set-input"
                        />
                      </div>
                      <div class="col-input">
                        <input
                          type="number"
                          step="0.5"
                          bind:value={s.weight}
                          oninput={() => updateTotals(exIdx)}
                          min="0"
                          placeholder="0"
                          class="input-field set-input"
                        />
                      </div>
                      <div class="col-action">
                        {#if ex.sets.length > 1}
                          <button
                            type="button"
                            class="btn-remove-set"
                            onclick={() => removeSet(exIdx, sIdx)}
                          >
                            ✕
                          </button>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>

                <div class="add-set-row">
                  <button type="button" class="btn-text-add" onclick={() => addSet(exIdx)}>
                    + Add Set {ex.sets.length + 1}
                  </button>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Notes -->
        <div class="form-group">
          <label class="form-label" for="session-notes">Session Notes</label>
          <textarea
            id="session-notes"
            bind:value={notes}
            rows="2"
            placeholder="How did it feel? Form cues, energy level..."
            class="input-field"
          ></textarea>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={closeModal}>Cancel</button>
          <button type="submit" class="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save Workout 🏋️'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .modal-large {
    max-width: 680px;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.25rem;
  }

  .modal-title {
    font-size: 1.25rem;
    font-weight: 700;
  }

  .modal-close-btn {
    color: var(--text-dim);
    font-size: 1.1rem;
    padding: 0.25rem;
  }
  .modal-close-btn:hover {
    color: var(--text-main);
  }

  .workout-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .grid-row {
    display: flex;
    gap: 1rem;
  }
  .flex-2 { flex: 2; }
  .flex-1 { flex: 1; }

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

  .exercises-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 700;
  }

  .exercises-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .exercise-card {
    background: var(--border-subtle);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1rem;
  }

  .exercise-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .select-exercise {
    font-weight: 700;
    font-size: 1.05rem;
    padding: 0.45rem 0.75rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .btn-icon-danger {
    color: var(--text-dim);
    font-size: 0.9rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
  .btn-icon-danger:hover {
    color: var(--accent-rose);
    background: rgba(244, 63, 94, 0.1);
  }

  .sets-table {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .set-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .header-row {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .col-num {
    width: 32px;
    text-align: center;
  }

  .set-badge {
    font-size: 0.85rem;
    font-weight: 800;
    color: var(--text-muted);
  }

  .col-input {
    flex: 1;
  }

  .set-input {
    padding: 0.45rem 0.65rem;
    font-size: 0.95rem;
  }

  .col-action {
    width: 28px;
  }

  .btn-remove-set {
    color: var(--text-dim);
    font-size: 0.85rem;
    padding: 0.2rem;
  }
  .btn-remove-set:hover {
    color: var(--accent-rose);
  }

  .add-set-row {
    margin-top: 0.5rem;
  }

  .btn-text-add {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--accent-emerald);
    padding: 0.25rem 0.5rem;
    border-radius: var(--radius-sm);
    transition: background 0.2s;
  }
  .btn-text-add:hover {
    background: rgba(16, 185, 129, 0.1);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 0.5rem;
  }
</style>
