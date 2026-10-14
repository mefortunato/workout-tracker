<script lang="ts">
  import { onDestroy } from 'svelte';
  import { themeStore } from '$lib/stores';
  import type { ChartDay } from '$lib/types';
  import Chart from 'chart.js/auto';

  let {
    data = [],
    title = 'Volume & Reps Over Time',
    chartType = $bindable<'bar' | 'line'>('bar')
  }: {
    data?: ChartDay[];
    title?: string;
    chartType?: 'bar' | 'line';
  } = $props();

  let canvasEl = $state<HTMLCanvasElement | null>(null);
  let chartInstance: Chart | null = null;

  function formatDate(dStr: string) {
    if (!dStr) return '';
    const parts = dStr.split('-');
    if (parts.length < 3) return dStr;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function renderChart() {
    if (!canvasEl || data.length === 0) {
      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }
      return;
    }

    const isLight = $themeStore === 'light';
    const isLine = chartType === 'line';
    const labels = data.map(d => formatDate(d.date));

    // Theme-tailored colors
    const pushupColor = isLight ? '#059669' : '#10b981';
    const situpColor = isLight ? '#0284c7' : '#06b6d4';
    const otherColor = isLight ? '#7c3aed' : '#8b5cf6';

    const pushupFill = isLight ? 'rgba(5, 150, 105, 0.12)' : 'rgba(16, 185, 129, 0.16)';
    const situpFill = isLight ? 'rgba(2, 132, 199, 0.12)' : 'rgba(6, 182, 212, 0.16)';
    const otherFill = isLight ? 'rgba(124, 58, 237, 0.12)' : 'rgba(139, 92, 246, 0.16)';

    const axisBorderColor = isLight ? 'rgba(15, 23, 42, 0.15)' : 'rgba(255, 255, 255, 0.12)';
    const gridColor = isLight ? 'rgba(15, 23, 42, 0.06)' : 'rgba(255, 255, 255, 0.06)';
    const tickColor = isLight ? '#475569' : '#94a3b8';
    const tickMuted = isLight ? '#94a3b8' : '#64748b';

    // Tooltip styling
    const tooltipBg = isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(15, 23, 42, 0.94)';
    const tooltipBorder = isLight ? 'rgba(15, 23, 42, 0.12)' : 'rgba(255, 255, 255, 0.14)';
    const tooltipTitleColor = isLight ? '#0f172a' : '#f8fafc';
    const tooltipBodyColor = isLight ? '#334155' : '#cbd5e1';

    const datasets = isLine
      ? [
          {
            type: 'line' as const,
            label: 'Push-ups',
            data: data.map(d => d.pushups),
            borderColor: pushupColor,
            backgroundColor: pushupFill,
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: data.length > 20 ? 3 : 4.5,
            pointHoverRadius: 6.5,
            pointBackgroundColor: pushupColor,
            pointBorderColor: isLight ? '#ffffff' : '#0f172a',
            pointBorderWidth: 2,
          },
          {
            type: 'line' as const,
            label: 'Sit-ups',
            data: data.map(d => d.situps),
            borderColor: situpColor,
            backgroundColor: situpFill,
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: data.length > 20 ? 3 : 4.5,
            pointHoverRadius: 6.5,
            pointBackgroundColor: situpColor,
            pointBorderColor: isLight ? '#ffffff' : '#0f172a',
            pointBorderWidth: 2,
          },
          {
            type: 'line' as const,
            label: 'Other',
            data: data.map(d => d.other_reps),
            borderColor: otherColor,
            backgroundColor: otherFill,
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: data.length > 20 ? 3 : 4.5,
            pointHoverRadius: 6.5,
            pointBackgroundColor: otherColor,
            pointBorderColor: isLight ? '#ffffff' : '#0f172a',
            pointBorderWidth: 2,
          }
        ]
      : [
          {
            type: 'bar' as const,
            label: 'Push-ups',
            data: data.map(d => d.pushups),
            backgroundColor: pushupColor,
            stack: 'stack0',
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            type: 'bar' as const,
            label: 'Sit-ups',
            data: data.map(d => d.situps),
            backgroundColor: situpColor,
            stack: 'stack0',
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            type: 'bar' as const,
            label: 'Other',
            data: data.map(d => d.other_reps),
            backgroundColor: otherColor,
            stack: 'stack0',
            borderRadius: 4,
            borderSkipped: false,
          }
        ];

    const chartConfig = {
      type: chartType,
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 400,
          easing: 'easeOutQuart' as const,
        },
        interaction: {
          mode: 'index' as const,
          intersect: false,
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: tooltipBg,
            borderColor: tooltipBorder,
            borderWidth: 1,
            titleColor: tooltipTitleColor,
            bodyColor: tooltipBodyColor,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            cornerRadius: 10,
            titleFont: {
              family: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
              size: 13,
              weight: 'bold' as const,
            },
            bodyFont: {
              family: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
              size: 12,
              weight: 500,
            },
            callbacks: {
              title: (tooltipItems: any[]) => {
                if (!tooltipItems.length) return '';
                const idx = tooltipItems[0].dataIndex;
                const item = data[idx];
                if (!item) return tooltipItems[0].label;
                const parts = item.date.split('-');
                const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
                return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
              },
              afterTitle: (tooltipItems: any[]) => {
                if (!tooltipItems.length) return '';
                const idx = tooltipItems[0].dataIndex;
                const item = data[idx];
                return `${item?.total_reps || 0} Total Reps\n`;
              }
            }
          }
        },
        scales: {
          x: {
            stacked: !isLine,
            grid: {
              display: false,
            },
            border: {
              color: axisBorderColor,
            },
            ticks: {
              color: tickColor,
              font: {
                family: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                size: 11,
                weight: 500,
              },
              autoSkip: true,
              autoSkipPadding: 14,
              maxRotation: 0,
            }
          },
          y: {
            stacked: !isLine,
            beginAtZero: true,
            grid: {
              color: gridColor,
            },
            border: {
              display: false,
              dash: [4, 4],
            },
            ticks: {
              color: tickMuted,
              font: {
                family: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                size: 10,
                weight: 500,
              },
              padding: 8,
              precision: 0,
            }
          }
        }
      }
    };

    if (chartInstance) {
      if (chartInstance.config.type !== chartType) {
        chartInstance.destroy();
        chartInstance = new Chart(canvasEl, chartConfig as any);
      } else {
        chartInstance.data = chartConfig.data as any;
        chartInstance.options = chartConfig.options as any;
        chartInstance.update();
      }
    } else {
      chartInstance = new Chart(canvasEl, chartConfig as any);
    }
  }

  $effect(() => {
    // Re-render whenever data, chartType, theme, or canvas element changes
    const _d = data;
    const _t = $themeStore;
    const _type = chartType;
    const _el = canvasEl;
    if (_el && _d) {
      renderChart();
    }
  });

  onDestroy(() => {
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
  });
</script>

<div class="chart-wrapper">
  <div class="chart-header">
    <div class="title-group">
      <h3 class="chart-title">{title}</h3>
      <span class="chart-subtitle">
        {chartType === 'line' ? 'Daily Exercise Trajectories & Rep Volume' : 'Daily Push-ups, Sit-ups & Total Reps'}
      </span>
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
    <div class="chart-canvas-container">
      <canvas bind:this={canvasEl}></canvas>
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

  .chart-canvas-container {
    position: relative;
    width: 100%;
    height: 270px;
  }

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
