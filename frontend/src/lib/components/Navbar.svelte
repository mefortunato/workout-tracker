<script lang="ts">
  import { userStore, checkAuth, addToast } from '$lib/stores';
  import { api } from '$lib/api';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';

  let isMobileMenuOpen = $state(false);

  async function handleLogout() {
    try {
      await api.logout();
      userStore.set(null);
      addToast('Logged Out', 'You have been safely signed out.', 'info');
      goto('/login');
    } catch (e: any) {
      addToast('Error', e.message || 'Logout failed', 'error');
    }
  }

  function toggleMobileMenu() {
    isMobileMenuOpen = !isMobileMenuOpen;
  }
</script>

<nav class="nav-bar">
  <div class="nav-container">
    <!-- Brand -->
    <a href="/" class="brand-logo">
      <div class="logo-icon">⚡</div>
      <div class="brand-text">
        <span class="brand-title">PULSE<span class="highlight">FIT</span></span>
        <span class="brand-sub">WORKOUT TRACKER</span>
      </div>
    </a>

    <!-- Desktop Navigation Links -->
    <div class="nav-links">
      <a href="/" class="nav-link" class:active={page.url.pathname === '/'}>
        <span class="icon">📊</span> Dashboard
      </a>
      <a href="/workouts" class="nav-link" class:active={page.url.pathname.startsWith('/workouts')}>
        <span class="icon">🏋️</span> Workouts
      </a>
      <a href="/exercises" class="nav-link" class:active={page.url.pathname.startsWith('/exercises')}>
        <span class="icon">📖</span> Exercises
      </a>
      <a href="/goals" class="nav-link" class:active={page.url.pathname.startsWith('/goals')}>
        <span class="icon">🎯</span> Goals
      </a>
      <a href="/stats" class="nav-link" class:active={page.url.pathname.startsWith('/stats')}>
        <span class="icon">📈</span> Analytics
      </a>
    </div>

    <!-- Auth / Profile Section -->
    <div class="nav-auth">
      {#if $userStore}
        <div class="user-chip">
          {#if $userStore.picture}
            <img src={$userStore.picture} alt={$userStore.name} class="avatar" />
          {:else}
            <div class="avatar-fallback">{$userStore.name ? $userStore.name[0].toUpperCase() : 'A'}</div>
          {/if}
          <div class="user-info">
            <span class="user-name">{$userStore.name}</span>
          </div>
          <button class="logout-btn" onclick={handleLogout} title="Sign Out">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      {:else}
        <a href="/login" class="btn btn-primary btn-sm">
          <span>Sign In</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </a>
      {/if}

      <!-- Mobile Hamburger Button -->
      <button class="mobile-toggle" onclick={toggleMobileMenu} aria-label="Toggle Navigation">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          {#if isMobileMenuOpen}
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          {:else}
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          {/if}
        </svg>
      </button>
    </div>
  </div>

  <!-- Mobile Dropdown Menu -->
  {#if isMobileMenuOpen}
    <div class="mobile-menu animate-pop-in">
      <a href="/" class="mobile-link" onclick={() => isMobileMenuOpen = false}>
        <span>📊</span> Dashboard
      </a>
      <a href="/workouts" class="mobile-link" onclick={() => isMobileMenuOpen = false}>
        <span>🏋️</span> Workouts
      </a>
      <a href="/exercises" class="mobile-link" onclick={() => isMobileMenuOpen = false}>
        <span>📖</span> Exercises
      </a>
      <a href="/goals" class="mobile-link" onclick={() => isMobileMenuOpen = false}>
        <span>🎯</span> Goals
      </a>
      <a href="/stats" class="mobile-link" onclick={() => isMobileMenuOpen = false}>
        <span>📈</span> Analytics
      </a>
      {#if $userStore}
        <button class="mobile-link logout-link" onclick={handleLogout}>
          <span>🚪</span> Sign Out ({$userStore.name})
        </button>
      {:else}
        <a href="/login" class="mobile-link login-link" onclick={() => isMobileMenuOpen = false}>
          <span>⚡</span> Sign In
        </a>
      {/if}
    </div>
  {/if}
</nav>

<style>
  .nav-bar {
    position: sticky;
    top: 0;
    z-index: 50;
    background: rgba(9, 13, 22, 0.85);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle);
  }

  .nav-container {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1.25rem;
  }

  .brand-logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-icon {
    width: 38px;
    height: 38px;
    background: var(--gradient-emerald-cyan);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
  }

  .brand-text {
    display: flex;
    flex-direction: column;
  }

  .brand-title {
    font-size: 1.25rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    color: var(--text-main);
  }

  .brand-title .highlight {
    color: var(--accent-emerald-light);
  }

  .brand-sub {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-dim);
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .nav-link {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.5rem 0.85rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-muted);
    border-radius: var(--radius-sm);
    transition: all 0.2s ease;
  }

  .nav-link:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.05);
  }

  .nav-link.active {
    color: var(--accent-emerald-light);
    background: rgba(16, 185, 129, 0.12);
  }

  .nav-auth {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .user-chip {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-subtle);
    padding: 0.3rem 0.6rem;
    border-radius: var(--radius-full);
  }

  .avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    object-fit: cover;
  }

  .avatar-fallback {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--gradient-emerald-cyan);
    color: #041212;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.85rem;
  }

  .user-name {
    font-size: 0.85rem;
    font-weight: 600;
    max-width: 110px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .logout-btn {
    color: var(--text-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem;
    border-radius: 50%;
    transition: color 0.2s ease, background 0.2s;
  }

  .logout-btn:hover {
    color: var(--accent-rose);
    background: rgba(244, 63, 94, 0.1);
  }

  .mobile-toggle {
    display: none;
    color: var(--text-main);
    padding: 0.4rem;
  }

  .mobile-menu {
    display: flex;
    flex-direction: column;
    background: #0d1322;
    border-top: 1px solid var(--border-subtle);
    padding: 1rem;
    gap: 0.5rem;
  }

  .mobile-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border-radius: var(--radius-md);
    color: var(--text-main);
    font-weight: 600;
    background: rgba(255, 255, 255, 0.03);
  }

  .logout-link {
    color: #f87171;
    border: 1px solid rgba(244, 63, 94, 0.2);
    width: 100%;
    text-align: left;
  }

  @media (max-width: 768px) {
    .nav-links {
      display: none;
    }
    .mobile-toggle {
      display: block;
    }
    .user-chip .user-info {
      display: none;
    }
  }
</style>
