<script lang="ts">
  import type { ChartDay } from '$lib/types';

  let {
    data = [],
    title = 'Volume & Reps Over Time'
  }: {
    data?: ChartDay[];
    title?: string;
  } = $props();

  let hoveredIndex: number | null = $state(null);

  // Chart dimensions
  const height = 240;
  const paddingBottom = 30;
  const paddingTop = 20;
  const paddingX = 15;

  let maxVal = $derived(Math.max(...data.map(d => d.total_reps), 50));

  function formatDate(dStr: string) {
    if (!dStr) return '';
    const parts = dStr.split('-');
    if (parts.length < 3) return dStr;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
</script>

<div class="chart-wrapper">
  <div class="chart-header">
    <div class="title-group">
      <h3 class="chart-title">{title}</h3>
      <span class="chart-subtitle">Daily Push-ups, Sit-ups & Total Reps</span>
    </div>
    <div class="chart-legend">
      <div class="legend-item">
        <span class="legend-dot dot-pushups"></span>
        <span>Push-ups</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot dot-situps"></span>
        <span>Sit-ups</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot dot-other"></span>
        <span>Other</span>
      </div>
    </div>
  </div>

  {#if data.length === 0}
    <div class="empty-chart">
      <span>No workout data in this timeframe yet. Log some reps to see charts!</span>
    </div>
  {:else}
    <div class="svg-container">
      <svg viewBox="0 0 {Math.max(data.length * 45 + 40, 500)} {height}" preserveAspectRatio="none" class="chart-svg">
        <defs>
          <linearGradient id="grad-pushup" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#10b981" />
            <stop offset="100%" stop-color="#047857" />
          </linearGradient>
          <linearGradient id="grad-situp" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#06b6d4" />
            <stop offset="100%" stop-color="#0e7490" />
          </linearGradient>
          <linearGradient id="grad-other" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#8b5cf6" />
            <stop offset="100%" stop-color="#6d28d9" />
          </linearGradient>
        </defs>

        <!-- Background grid lines -->
        <line x1="0" y1="{paddingTop}" x2="100%" y2="{paddingTop}" stroke="var(--chart-grid)" stroke-dasharray="4" />
        <line x1="0" y1="{(height - paddingBottom + paddingTop) / 2}" x2="100%" y2="{(height - paddingBottom + paddingTop) / 2}" stroke="var(--chart-grid)" stroke-dasharray="4" />
        <line x1="0" y1="{height - paddingBottom}" x2="100%" y2="{height - paddingBottom}" stroke="var(--chart-axis)" />

        <!-- Bars -->
        {#each data as day, i}
          {@const totalHeight = height - paddingBottom - paddingTop}
          {@const barWidth = 24}
          {@const x = paddingX + i * 45 + 15}

          {@const pushupH = (day.pushups / maxVal) * totalHeight}
          {@const situpH = (day.situps / maxVal) * totalHeight}
          {@const otherH = (day.other_reps / maxVal) * totalHeight}

          <g
            class="bar-group"
            onmouseenter={() => hoveredIndex = i}
            onmouseleave={() => hoveredIndex = null}
          >
            <!-- Hitbox -->
            <rect
              x={x - 8}
              y={paddingTop}
              width={barWidth + 16}
              height={totalHeight}
              fill="transparent"
              class="bar-hitbox"
            />

            <!-- Stacked Bars: Pushups bottom, Situps middle, Other top -->
            {#if day.pushups > 0}
              <rect
                x={x}
                y={height - paddingBottom - pushupH}
                width={barWidth}
                height={Math.max(pushupH, 2)}
                rx="4"
                fill="url(#grad-pushup)"
                class="bar-part"
              />
            {/if}

            {#if day.situps > 0}
              <rect
                x={x}
                y={height - paddingBottom - pushupH - situpH}
                width={barWidth}
                height={Math.max(situpH, 2)}
                rx="4"
                fill="url(#grad-situp)"
                class="bar-part"
              />
            {/if}

            {#if day.other_reps > 0}
              <rect
                x={x}
                y={height - paddingBottom - pushupH - situpH - otherH}
                width={barWidth}
                height={Math.max(otherH, 2)}
                rx="4"
                fill="url(#grad-other)"
                class="bar-part"
              />
            {/if}

            <!-- Date label -->
            <text
              x={x + barWidth / 2}
              y={height - 8}
              text-anchor="middle"
              font-size="10"
              font-family="var(--font-family)"
              fill={hoveredIndex === i ? 'var(--text-main)' : 'var(--text-dim)'}
              font-weight={hoveredIndex === i ? '700' : '500'}
            >
              {formatDate(day.date)}
            </text>
          </g>
        {/each}
      </svg>

      <!-- Active Tooltip -->
      {#if hoveredIndex !== null && data[hoveredIndex]}
        {@const day = data[hoveredIndex]}
        <div class="tooltip animate-pop-in" style="left: {Math.min(hoveredIndex * 45 + 30, 400)}px;">
          <div class="tooltip-date">{formatDate(day.date)}</div>
          <div class="tooltip-total">{day.total_reps} Total Reps</div>
          <div class="tooltip-breakdown">
            <span class="text-pushups">Push-ups: {day.pushups}</span>
            <span class="text-situps">Sit-ups: {day.situps}</span>
            {#if day.other_reps > 0}
              <span class="text-other">Other: {day.other_reps}</span>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .chart-wrapper {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    position: relative;
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .chart-title {
    font-size: 1.15rem;
    font-weight: 700;
  }

  .chart-subtitle {
    font-size: 0.8rem;
    color: var(--text-dim);
    display: block;
  }

  .chart-legend {
    display: flex;
    gap: 1rem;
    align-items: center;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .dot-pushups { background: var(--accent-emerald); }
  .dot-situps { background: var(--accent-cyan); }
  .dot-other { background: var(--accent-purple); }

  .svg-container {
    position: relative;
    width: 100%;
    overflow-x: auto;
  }

  .chart-svg {
    width: 100%;
    min-width: 450px;
    height: 240px;
  }

  .bar-hitbox {
    cursor: pointer;
  }

  .bar-group:hover .bar-part {
    filter: brightness(1.25);
  }

  .tooltip {
    position: absolute;
    top: 10px;
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-hover);
    box-shadow: var(--shadow-card);
    padding: 0.6rem 0.85rem;
    border-radius: var(--radius-sm);
    pointer-events: none;
    z-index: 20;
    min-width: 130px;
  }

  .tooltip-date {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-dim);
  }

  .tooltip-total {
    font-size: 1rem;
    font-weight: 800;
    color: var(--text-main);
    margin: 0.15rem 0;
  }

  .tooltip-breakdown {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .text-pushups { color: var(--accent-emerald-light); }
  .text-situps { color: var(--accent-cyan-light); }
  .text-other { color: #c084fc; }

  .empty-chart {
    height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: 0.9rem;
    text-align: center;
  }
</style>
