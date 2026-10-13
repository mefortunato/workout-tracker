<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { addToast } from '$lib/stores';
  import type { StatsSummary, PersonalRecord, ChartDay } from '$lib/types';
  import StatsChart from '$lib/components/StatsChart.svelte';

  let summary = $state<StatsSummary | null>(null);
  let prs = $state<PersonalRecord[]>([]);
  let chartData = $state<ChartDay[]>([]);
  let selectedDays = $state(14);
  let isLoading = $state(true);

  onMount(async () => {
    await loadStats();
  });

  async function loadStats() {
    isLoading = true;
    try {
      const [sumData, prData, cData] = await Promise.all([
        api.getStatsSummary(),
        api.getPRs(),
        api.getChartData(selectedDays)
      ]);
      summary = sumData;
      prs = prData || [];
      chartData = cData || [];
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to load analytics', 'error');
    } finally {
      isLoading = false;
    }
  }

  async function handleDaysChange(days: number) {
    selectedDays = days;
    try {
      chartData = await api.getChartData(days);
    } catch (e: any) {
      addToast('Error', 'Failed to update chart data', 'error');
    }
  }
</script>

<div class="container stats-container">
  <div class="page-header">
    <div>
      <h1 class="page-title">📈 Analytics & Personal Records</h1>
      <p class="page-sub">Track your progress, consistency streaks, and all-time records.</p>
    </div>
  </div>

  {#if isLoading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Crunching your performance metrics...</p>
    </div>
  {:else}
    <!-- Lifetime Totals Grid -->
    <div class="totals-grid">
      <div class="total-card glass-card">
        <span class="total-icon">🏆</span>
        <div class="total-data">
          <span class="total-label">Total Workouts</span>
          <span class="total-val">{summary?.total_workouts || 0}</span>
        </div>
      </div>

      <div class="total-card glass-card">
        <span class="total-icon">💪</span>
        <div class="total-data">
          <span class="total-label">Total Push-ups</span>
          <span class="total-val text-emerald">{summary?.total_pushups || 0}</span>
        </div>
      </div>

      <div class="total-card glass-card">
        <span class="total-icon">🛡️</span>
        <div class="total-data">
          <span class="total-label">Total Sit-ups</span>
          <span class="total-val text-cyan">{summary?.total_situps || 0}</span>
        </div>
      </div>

      <div class="total-card glass-card">
        <span class="total-icon">⚡</span>
        <div class="total-data">
          <span class="total-label">Total Reps Logged</span>
          <span class="total-val">{summary?.total_reps || 0}</span>
        </div>
      </div>

      <div class="total-card glass-card">
        <span class="total-icon">🔥</span>
        <div class="total-data">
          <span class="total-label">Active Streak</span>
          <span class="total-val text-amber">{summary?.current_streak_days || 0} Days</span>
          <span class="total-sub">Longest: {summary?.longest_streak_days || 0} Days</span>
        </div>
      </div>
    </div>

    <!-- Chart Section with Range Toggle -->
    <div class="chart-section">
      <div class="range-toggle-bar">
        <span class="range-label">Timeframe:</span>
        <div class="pill-group">
          <button
            class="pill-btn"
            class:active={selectedDays === 7}
            onclick={() => handleDaysChange(7)}
          >
            Last 7 Days
          </button>
          <button
            class="pill-btn"
            class:active={selectedDays === 14}
            onclick={() => handleDaysChange(14)}
          >
            Last 14 Days
          </button>
          <button
            class="pill-btn"
            class:active={selectedDays === 30}
            onclick={() => handleDaysChange(30)}
          >
            Last 30 Days
          </button>
        </div>
      </div>

      <StatsChart data={chartData} title="Reps & Volume Distribution" />
    </div>

    <!-- Personal Records Showcase -->
    <div class="pr-section">
      <div class="pr-header">
        <h2 class="section-title">🥇 Personal Records (PRs)</h2>
        <span class="section-sub">Your all-time single-set and single-day maxes</span>
      </div>

      {#if prs.length === 0}
        <div class="empty-state glass-card">
          <span>No records logged yet. Complete some workout sets to establish your PRs!</span>
        </div>
      {:else}
        <div class="pr-grid">
          {#each prs as pr}
            <div class="pr-card glass-card animate-pop-in">
              <div class="pr-card-top">
                <h3 class="pr-ex-name">{pr.exercise_name}</h3>
                <span class="badge badge-emerald">{pr.total_sessions} Sessions</span>
              </div>

              <div class="pr-stats-row">
                <div class="pr-stat-box">
                  <span class="stat-lbl">Max Single Set</span>
                  <span class="stat-num">{pr.max_set_reps} <small>reps</small></span>
                </div>

                <div class="pr-stat-box">
                  <span class="stat-lbl">Max in One Day</span>
                  <span class="stat-num">{pr.max_daily_reps} <small>reps</small></span>
                </div>

                {#if pr.max_weight > 0}
                  <div class="pr-stat-box">
                    <span class="stat-lbl">Max Weight</span>
                    <span class="stat-num text-amber">{pr.max_weight} <small>kg</small></span>
                  </div>
                {/if}

                {#if pr.max_duration_seconds > 0}
                  <div class="pr-stat-box">
                    <span class="stat-lbl">Max Hold</span>
                    <span class="stat-num text-cyan">{pr.max_duration_seconds} <small>sec</small></span>
                  </div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .stats-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

  /* Totals Grid */
  .totals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.25rem;
  }

  .total-card {
    padding: 1.25rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .total-icon {
    font-size: 2rem;
  }

  .total-data {
    display: flex;
    flex-direction: column;
  }

  .total-label {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .total-val {
    font-size: 1.6rem;
    font-weight: 900;
    line-height: 1.2;
  }

  .total-sub {
    font-size: 0.72rem;
    color: var(--text-dim);
  }

  .text-emerald { color: var(--accent-emerald-light); }
  .text-cyan { color: var(--accent-cyan-light); }
  .text-amber { color: #fbbf24; }

  /* Chart Section */
  .chart-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .range-toggle-bar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.75rem;
  }

  .range-label {
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--text-dim);
  }

  .pill-group {
    display: flex;
    background: rgba(255, 255, 255, 0.04);
    padding: 0.2rem;
    border-radius: var(--radius-sm);
    gap: 0.25rem;
  }

  .pill-btn {
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-muted);
    border-radius: var(--radius-sm);
    transition: all 0.2s;
  }
  .pill-btn:hover { color: var(--text-main); }
  .pill-btn.active {
    background: var(--accent-emerald);
    color: #041212;
    font-weight: 700;
  }

  /* PR Showcase */
  .pr-section {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .section-title {
    font-size: 1.35rem;
    font-weight: 800;
  }

  .section-sub {
    font-size: 0.85rem;
    color: var(--text-dim);
  }

  .pr-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.25rem;
  }

  .pr-card {
    padding: 1.35rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .pr-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .pr-ex-name {
    font-size: 1.15rem;
    font-weight: 800;
  }

  .pr-stats-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .pr-stat-box {
    flex: 1;
    min-width: 100px;
    background: rgba(255, 255, 255, 0.03);
    padding: 0.75rem;
    border-radius: var(--radius-sm);
    display: flex;
    flex-direction: column;
  }

  .stat-lbl {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .stat-num {
    font-size: 1.35rem;
    font-weight: 900;
    color: var(--accent-emerald-light);
  }

  .stat-num small {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
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
