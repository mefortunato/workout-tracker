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
  let containerWidth = $state(800);

  // Chart dimensions & layout
  const height = 260;
  const paddingTop = 32;
  const paddingBottom = 42;
  const paddingX = 24;

  let maxVal = $derived(Math.max(...data.map(d => d.total_reps), 50));

  // Dynamic responsive width: fills the container cleanly on wide displays,
  // while ensuring a comfortable minimum slot width for large date ranges (e.g. 30 days)
  const minSlotWidth = 36;
  let chartWidth = $derived(Math.max(containerWidth || 700, data.length * minSlotWidth + paddingX * 2));
  let usableWidth = $derived(chartWidth - paddingX * 2);
  let slotWidth = $derived(data.length > 0 ? usableWidth / data.length : 0);
  let barWidth = $derived(Math.min(Math.max(slotWidth * 0.52, 10), 28));

  // Determine tick interval to prevent crowded or squished date labels
  let labelStep = $derived(
    slotWidth < 26 ? 4 : slotWidth < 46 ? 2 : 1
  );

  function formatDate(dStr: string) {
    if (!dStr) return '';
    const parts = dStr.split('-');
    if (parts.length < 3) return dStr;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function formatTooltipDate(dStr: string) {
    if (!dStr) return '';
    const parts = dStr.split('-');
    if (parts.length < 3) return dStr;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  }

  function shouldShowDate(index: number) {
    if (data.length <= 1) return true;
    if (hoveredIndex === index) return true;
    // Align so today (the last day) is always shown, plus regular steps
    const fromEnd = data.length - 1 - index;
    return fromEnd % labelStep === 0;
  }

  let tooltipX = $derived.by(() => {
    if (hoveredIndex === null || !data[hoveredIndex]) return 0;
    const barCenterX = paddingX + (hoveredIndex + 0.5) * slotWidth;
    return Math.max(12, Math.min(barCenterX - 85, chartWidth - 180));
  });
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
    <div class="svg-container" bind:clientWidth={containerWidth}>
      <svg
        viewBox="0 0 {chartWidth} {height}"
        style="width: {chartWidth}px; height: {height}px;"
        class="chart-svg"
      >
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

        <!-- Background grid lines & subtle reference indicators -->
        <line x1="{paddingX}" y1="{paddingTop}" x2="{chartWidth - paddingX}" y2="{paddingTop}" stroke="var(--chart-grid)" stroke-dasharray="4" />
        <text x="{paddingX}" y="{paddingTop - 8}" class="axis-guide-label">{maxVal} reps</text>

        <line x1="{paddingX}" y1="{(height - paddingBottom + paddingTop) / 2}" x2="{chartWidth - paddingX}" y2="{(height - paddingBottom + paddingTop) / 2}" stroke="var(--chart-grid)" stroke-dasharray="4" />
        <text x="{paddingX}" y="{(height - paddingBottom + paddingTop) / 2 - 8}" class="axis-guide-label">{Math.round(maxVal / 2)}</text>

        <line x1="{paddingX}" y1="{height - paddingBottom}" x2="{chartWidth - paddingX}" y2="{height - paddingBottom}" stroke="var(--chart-axis)" />

        <!-- Bars -->
        {#each data as day, i}
          {@const totalHeight = height - paddingBottom - paddingTop}
          {@const x = paddingX + i * slotWidth + (slotWidth - barWidth) / 2}
          {@const barCenterX = paddingX + (i + 0.5) * slotWidth}

          {@const pushupH = (day.pushups / maxVal) * totalHeight}
          {@const situpH = (day.situps / maxVal) * totalHeight}
          {@const otherH = (day.other_reps / maxVal) * totalHeight}

          <g
            class="bar-group"
            role="group"
            aria-label="{formatDate(day.date)}: {day.total_reps} total reps"
            onmouseenter={() => hoveredIndex = i}
            onmouseleave={() => hoveredIndex = null}
          >
            <!-- Hitbox covering the entire daily column for smooth hovering -->
            <rect
              x={paddingX + i * slotWidth}
              y={paddingTop - 10}
              width={slotWidth}
              height={totalHeight + 15}
              fill="transparent"
              class="bar-hitbox"
            />

            <!-- Stacked Bars: Pushups bottom, Situps middle, Other top -->
            {#if day.pushups > 0}
              <rect
                x={x}
                y={height - paddingBottom - pushupH}
                width={barWidth}
                height={Math.max(pushupH, 3)}
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
                height={Math.max(situpH, 3)}
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
                height={Math.max(otherH, 3)}
                rx="4"
                fill="url(#grad-other)"
                class="bar-part"
              />
            {/if}

            <!-- X-axis Date label -->
            {#if shouldShowDate(i)}
              <text
                x={barCenterX}
                y={height - 14}
                text-anchor="middle"
                class="axis-date-text"
                class:active={hoveredIndex === i}
              >
                {formatDate(day.date)}
              </text>
            {/if}
          </g>
        {/each}
      </svg>

      <!-- Active Tooltip -->
      {#if hoveredIndex !== null && data[hoveredIndex]}
        {@const day = data[hoveredIndex]}
        <div class="tooltip animate-pop-in" style="left: {tooltipX}px;">
          <div class="tooltip-date">{formatTooltipDate(day.date)}</div>
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
    box-shadow: var(--shadow-card);
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
    margin-top: 0.15rem;
  }

  .chart-legend {
    display: flex;
    gap: 1.25rem;
    align-items: center;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
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
    overflow-y: hidden;
    scrollbar-width: thin;
    scrollbar-color: var(--border-hover) transparent;
  }

  .svg-container::-webkit-scrollbar {
    height: 6px;
  }

  .svg-container::-webkit-scrollbar-thumb {
    background: var(--border-hover);
    border-radius: 4px;
  }

  .chart-svg {
    display: block;
    height: 260px;
    max-width: none;
  }

  .bar-hitbox {
    cursor: pointer;
  }

  .bar-group:hover .bar-part {
    filter: brightness(1.25);
  }

  .axis-guide-label {
    font-family: var(--font-family);
    font-size: 10px;
    font-weight: 600;
    fill: var(--text-dim);
    opacity: 0.65;
    user-select: none;
  }

  .axis-date-text {
    font-family: var(--font-family);
    font-size: 11px;
    font-weight: 500;
    fill: var(--text-muted);
    letter-spacing: 0.01em;
    transition: fill 0.15s ease, font-weight 0.15s ease;
    user-select: none;
  }

  .axis-date-text.active {
    fill: var(--text-main);
    font-weight: 700;
  }

  .tooltip {
    position: absolute;
    top: 10px;
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-hover);
    box-shadow: var(--shadow-card);
    padding: 0.65rem 0.9rem;
    border-radius: var(--radius-sm);
    pointer-events: none;
    z-index: 20;
    min-width: 150px;
  }

  .tooltip-date {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-dim);
  }

  .tooltip-total {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--text-main);
    margin: 0.2rem 0;
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
