<script lang="ts">
  import { toasts, removeToast } from '$lib/stores';
</script>

<div class="toast-container">
  {#each $toasts as toast (toast.id)}
    <div class="toast-item {toast.type} animate-pop-in">
      <div class="toast-icon">
        {#if toast.type === 'success'}
          ✓
        {:else if toast.type === 'error'}
          ✕
        {:else}
          ℹ
        {/if}
      </div>
      <div class="toast-content">
        <strong class="toast-title">{toast.title}</strong>
        <p class="toast-msg">{toast.message}</p>
      </div>
      <button class="toast-close" onclick={() => removeToast(toast.id)}>✕</button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-width: 360px;
    width: calc(100% - 2rem);
    pointer-events: none;
  }

  .toast-item {
    pointer-events: auto;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    background: #111827;
    border-radius: var(--radius-md);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.7);
    border: 1px solid var(--border-hover);
  }

  .toast-item.success {
    border-left: 4px solid var(--accent-emerald);
  }
  .toast-item.success .toast-icon {
    color: var(--accent-emerald);
    background: rgba(16, 185, 129, 0.15);
  }

  .toast-item.error {
    border-left: 4px solid var(--accent-rose);
  }
  .toast-item.error .toast-icon {
    color: var(--accent-rose);
    background: rgba(244, 63, 94, 0.15);
  }

  .toast-item.info {
    border-left: 4px solid var(--accent-cyan);
  }
  .toast-item.info .toast-icon {
    color: var(--accent-cyan);
    background: rgba(6, 182, 212, 0.15);
  }

  .toast-icon {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  .toast-content {
    flex: 1;
  }

  .toast-title {
    font-size: 0.9rem;
    display: block;
    color: var(--text-main);
  }

  .toast-msg {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 0.15rem;
  }

  .toast-close {
    color: var(--text-dim);
    font-size: 0.85rem;
    padding: 0.2rem;
  }

  .toast-close:hover {
    color: var(--text-main);
  }
</style>
