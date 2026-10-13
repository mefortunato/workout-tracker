<script lang="ts">
  import { api } from '$lib/api';
  import { addToast } from '$lib/stores';
  import type { GoalItem } from '$lib/types';

  let {
    goal,
    onrefresh
  }: {
    goal: GoalItem;
    onrefresh?: () => void;
  } = $props();

  let isLogging = $state(false);

  async function handleQuickAdd(amount: number) {
    if (!goal.exercise_name) return;
    isLogging = true;
    try {
      await api.quickLog({
        exercise_name: goal.exercise_name,
        reps: amount,
      });
      addToast('Goal Boost! 🎯', `Added +${amount} ${goal.exercise_name} towards your goal!`, 'success');
      onrefresh?.();
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to log reps', 'error');
    } finally {
      isLogging = false;
    }
  }

  async function handleDelete() {
    if (!confirm(`Are you sure you want to delete the goal: "${goal.title}"?`)) return;
    try {
      await api.deleteGoal(goal._id);
      addToast('Goal Deleted', 'Goal was removed.', 'info');
      onrefresh?.();
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to delete goal', 'error');
    }
  }
</script>

<div class="goal-card glass-card" class:completed={goal.progress_percentage >= 100}>
  <div class="goal-header">
    <div class="goal-title-area">
      <span class="badge {goal.period === 'daily' ? 'badge-emerald' : 'badge-cyan'}">
        {goal.period}
      </span>
      <h4 class="goal-title">{goal.title}</h4>
    </div>
    <button class="delete-btn" onclick={handleDelete} title="Delete Goal">✕</button>
  </div>

  <div class="progress-stats">
    <div class="current-value">
      <span class="val-number">{goal.current_value}</span>
      <span class="target-number">/ {goal.target_value} {goal.unit}</span>
    </div>
    <div class="percentage-badge">
      {#if goal.progress_percentage >= 100}
        <span class="completed-text">COMPLETE! 🏆</span>
      {:else}
        <span>{goal.progress_percentage}%</span>
      {/if}
    </div>
  </div>

  <!-- Progress Bar -->
  <div class="progress-track">
    <div
      class="progress-fill"
      class:fill-completed={goal.progress_percentage >= 100}
      style="width: {Math.min(goal.progress_percentage, 100)}%;"
    ></div>
  </div>

  <!-- Quick Action Buttons -->
  {#if goal.exercise_name && goal.progress_percentage < 100}
    <div class="goal-quick-actions">
      <span class="quick-label">Quick Add:</span>
      <button
        class="btn-goal-step"
        disabled={isLogging}
        onclick={() => handleQuickAdd(10)}
      >
        +10
      </button>
      <button
        class="btn-goal-step"
        disabled={isLogging}
        onclick={() => handleQuickAdd(25)}
      >
        +25
      </button>
      <button
        class="btn-goal-step"
        disabled={isLogging}
        onclick={() => handleQuickAdd(50)}
      >
        +50
      </button>
    </div>
  {/if}
</div>

<style>
  .goal-card {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }

  .goal-card.completed {
    border-color: rgba(16, 185, 129, 0.4);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.15);
  }

  .goal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .goal-title-area {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .goal-title {
    font-size: 1.05rem;
    font-weight: 700;
  }

  .delete-btn {
    color: var(--text-dim);
    font-size: 0.85rem;
    padding: 0.2rem;
  }
  .delete-btn:hover {
    color: var(--accent-rose);
  }

  .progress-stats {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .current-value {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
  }

  .val-number {
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--accent-emerald-light);
  }

  .target-number {
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .percentage-badge {
    font-size: 0.9rem;
    font-weight: 800;
    color: var(--text-main);
  }

  .completed-text {
    color: var(--accent-emerald-light);
    letter-spacing: 0.05em;
  }

  .progress-track {
    width: 100%;
    height: 10px;
    background: rgba(255, 255, 255, 0.07);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--gradient-emerald-cyan);
    border-radius: var(--radius-full);
    transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .fill-completed {
    background: linear-gradient(90deg, #10b981, #34d399);
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.8);
  }

  .goal-quick-actions {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-top: 0.2rem;
  }

  .quick-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-dim);
  }

  .btn-goal-step {
    padding: 0.25rem 0.65rem;
    font-size: 0.78rem;
    font-weight: 700;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-main);
    transition: all 0.2s;
  }
  .btn-goal-step:hover {
    background: rgba(16, 185, 129, 0.2);
    border-color: var(--accent-emerald);
    color: var(--accent-emerald-light);
  }
</style>
