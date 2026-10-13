<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import Navbar from '$lib/components/Navbar.svelte';
  import ToastContainer from '$lib/components/ToastContainer.svelte';
  import { checkAuth, userStore, loadingUser, addToast } from '$lib/stores';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';

  let { children } = $props();

  function isPublicRoute(pathname: string): boolean {
    const clean = pathname.replace(/\/$/, '') || '/';
    return clean === '/' || clean === '/login';
  }

  onMount(async () => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (url.searchParams.get('auth_success') === '1') {
        url.searchParams.delete('auth_success');
        window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
        addToast('Welcome Back! 🔥', 'Successfully authenticated with Google.', 'success');
      }
    }
    const user = await checkAuth();
    if (!user && !isPublicRoute(page.url.pathname)) {
      goto('/login', { replaceState: true });
    }
  });

  $effect(() => {
    // Reactive route guard: redirect to /login if user is not authenticated on a protected route
    if (!$loadingUser && !$userStore && !isPublicRoute(page.url.pathname)) {
      goto('/login', { replaceState: true });
    }
  });
</script>

<div class="app-layout">
  <Navbar />
  <main class="main-content">
    {#if isPublicRoute(page.url.pathname)}
      {@render children()}
    {:else if $loadingUser}
      <div class="auth-gate-loading">
        <div class="spinner"></div>
        <p>Checking authentication...</p>
      </div>
    {:else if $userStore}
      {@render children()}
    {/if}
  </main>
  <ToastContainer />
</div>

<style>
  .app-layout {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  .main-content {
    flex: 1;
  }

  .auth-gate-loading {
    min-height: calc(100vh - 80px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    color: var(--text-muted);
    font-size: 0.95rem;
  }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent-emerald);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
