<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import Navbar from '$lib/components/Navbar.svelte';
  import ToastContainer from '$lib/components/ToastContainer.svelte';
  import { checkAuth, addToast } from '$lib/stores';

  let { children } = $props();

  onMount(async () => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (url.searchParams.get('auth_success') === '1') {
        url.searchParams.delete('auth_success');
        window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
        addToast('Welcome Back! 🔥', 'Successfully authenticated with Google.', 'success');
      }
    }
    await checkAuth();
  });
</script>

<div class="app-layout">
  <Navbar />
  <main class="main-content">
    {@render children()}
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
</style>
