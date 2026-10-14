<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { addToast } from '$lib/stores';
  import type { ExerciseItem } from '$lib/types';

  let exercises = $state<ExerciseItem[]>([]);
  let isLoading = $state(true);

  // Filters
  let activeCategory = $state('All');
  let searchQuery = $state('');

  // New Exercise Form
  let isAddModalOpen = $state(false);
  let newName = $state('');
  let newCategory = $state('Upper Body');
  let newType = $state('reps');
  let newDescription = $state('');
  let isSubmitting = $state(false);

  const categories = ['All', 'Upper Body', 'Core', 'Lower Body', 'Full Body'];

  onMount(async () => {
    await loadExercises();
  });

  async function loadExercises() {
    isLoading = true;
    try {
      exercises = await api.getExercises();
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to load exercises', 'error');
    } finally {
      isLoading = false;
    }
  }

  let filteredExercises = $derived(
    exercises.filter((ex) => {
      if (activeCategory !== 'All' && ex.category !== activeCategory) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = ex.name.toLowerCase().includes(q);
        const matchDesc = (ex.description || '').toLowerCase().includes(q);
        if (!matchName && !matchDesc) return false;
      }
      return true;
    })
  );

  async function handleCreateExercise(e: SubmitEvent) {
    e.preventDefault();
    if (!newName.trim()) {
      addToast('Missing Name', 'Please provide an exercise name.', 'error');
      return;
    }

    isSubmitting = true;
    try {
      const created = await api.createExercise({
        name: newName.trim(),
        category: newCategory,
        type: newType,
        description: newDescription.trim()
      });
      addToast('Exercise Created! 🌟', `"${created.name}" was added to your exercises.`, 'success');
      exercises = [...exercises, created];
      isAddModalOpen = false;
      newName = '';
      newDescription = '';
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to create exercise', 'error');
    } finally {
      isSubmitting = false;
    }
  }

  async function handleDeleteExercise(id: string, name: string) {
    if (!confirm(`Delete custom exercise "${name}"?`)) return;
    try {
      await api.deleteExercise(id);
      addToast('Exercise Removed', `"${name}" was deleted.`, 'info');
      exercises = exercises.filter(e => e._id !== id);
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to delete exercise', 'error');
    }
  }
</script>

<div class="container exercises-container">
  <div class="page-header">
    <div>
      <h1 class="page-title">📖 Exercise Directory</h1>
      <p class="page-sub">Browse standard movements and create your own custom exercises.</p>
    </div>
    <button class="btn btn-primary" onclick={() => isAddModalOpen = true}>
      <span>+ Add Custom Movement</span>
    </button>
  </div>

  <!-- Filters -->
  <div class="filters-card glass-card">
    <div class="categories-bar">
      {#each categories as cat}
        <button
          class="cat-pill"
          class:active={activeCategory === cat}
          onclick={() => activeCategory = cat}
        >
          {cat}
        </button>
      {/each}
    </div>

    <div class="search-box">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Search exercises by name or description..."
        class="input-field"
      />
    </div>
  </div>

  <!-- Exercises Grid -->
  {#if isLoading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading exercise movements...</p>
    </div>
  {:else if filteredExercises.length === 0}
    <div class="empty-state glass-card">
      <span class="empty-icon">🔍</span>
      <h3>No movements found</h3>
      <p>Try searching for a different term or add a new exercise!</p>
    </div>
  {:else}
    <div class="exercises-grid">
      {#each filteredExercises as ex (ex._id)}
        <div class="exercise-card glass-card animate-pop-in">
          <div class="ex-card-header">
            <div>
              <h3 class="ex-name">{ex.name}</h3>
              <span class="badge {ex.category === 'Core' ? 'badge-cyan' : ex.category === 'Upper Body' ? 'badge-emerald' : 'badge-amber'}">
                {ex.category}
              </span>
            </div>
            {#if !ex.is_default}
              <button
                class="btn-delete"
                onclick={() => handleDeleteExercise(ex._id, ex.name)}
                title="Delete custom exercise"
              >
                ✕
              </button>
            {/if}
          </div>

          <p class="ex-desc">{ex.description || 'Standard training movement.'}</p>

          <div class="ex-footer">
            <span class="ex-type-badge">Type: {ex.type}</span>
            {#if ex.is_default}
              <span class="system-badge">System Standard</span>
            {:else}
              <span class="custom-badge">Custom</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Exercise Modal -->
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
        <h3 class="modal-title">✨ Create Custom Exercise</h3>
        <button class="modal-close-btn" onclick={() => isAddModalOpen = false}>✕</button>
      </div>

      <form onsubmit={handleCreateExercise} class="modal-form">
        <div class="form-group">
          <label class="form-label" for="ex-name">Movement Name</label>
          <input
            id="ex-name"
            type="text"
            bind:value={newName}
            placeholder="e.g., Archer Push-ups, Incline Push-ups"
            class="input-field"
            required
          />
        </div>

        <div class="grid-row">
          <div class="form-group flex-1">
            <label class="form-label" for="ex-cat">Target Category</label>
            <select id="ex-cat" bind:value={newCategory} class="input-field">
              <option value="Upper Body">Upper Body</option>
              <option value="Core">Core</option>
              <option value="Lower Body">Lower Body</option>
              <option value="Full Body">Full Body</option>
              <option value="Cardio">Cardio</option>
            </select>
          </div>

          <div class="form-group flex-1">
            <label class="form-label" for="ex-type">Measurement Type</label>
            <select id="ex-type" bind:value={newType} class="input-field">
              <option value="reps">Reps (Push-ups, Sit-ups)</option>
              <option value="duration">Duration (Seconds/Plank)</option>
              <option value="weight_reps">Weight & Reps</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="ex-desc">Movement Description</label>
          <textarea
            id="ex-desc"
            bind:value={newDescription}
            rows="2"
            placeholder="Cues, technique notes, variations..."
            class="input-field"
          ></textarea>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={() => isAddModalOpen = false}>Cancel</button>
          <button type="submit" class="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Exercise 🌟'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .exercises-container {
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
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .categories-bar {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  .cat-pill {
    padding: 0.45rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted);
    background: var(--border-subtle);
    border-radius: var(--radius-sm);
    transition: all 0.2s;
  }
  .cat-pill:hover { color: var(--text-main); }
  .cat-pill.active {
    background: var(--accent-emerald);
    color: #ffffff;
    font-weight: 700;
  }

  .search-box {
    flex: 1;
    min-width: 250px;
  }

  /* Exercises Grid */
  .exercises-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.25rem;
  }

  .exercise-card {
    padding: 1.35rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.85rem;
  }

  .ex-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .ex-name {
    font-size: 1.2rem;
    font-weight: 800;
    margin-bottom: 0.35rem;
  }

  .btn-delete {
    color: var(--text-dim);
    font-size: 0.95rem;
    padding: 0.25rem;
  }
  .btn-delete:hover {
    color: var(--accent-rose);
  }

  .ex-desc {
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .ex-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--border-subtle);
    padding-top: 0.75rem;
    font-size: 0.78rem;
  }

  .ex-type-badge {
    color: var(--text-dim);
    font-weight: 600;
    text-transform: capitalize;
  }

  .system-badge {
    color: var(--text-dim);
    font-size: 0.72rem;
  }

  .custom-badge {
    color: var(--accent-cyan-light);
    font-weight: 700;
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
