<script lang="ts">
  import { userStore, checkAuth, addToast, themeStore, toggleTheme } from '$lib/stores';
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
    {#if $userStore}
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
        <a href="/challenges" class="nav-link" class:active={page.url.pathname.startsWith('/challenges')}>
          <span class="icon">🏆</span> Challenges
        </a>
      </div>
    {/if}

    <!-- Auth / Profile Section & Theme Switcher -->
    <div class="nav-auth">
      <!-- Theme Switcher Button -->
      <button
        class="theme-toggle-btn"
        onclick={toggleTheme}
        title={$themeStore === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
        aria-label="Toggle theme"
      >
        {#if $themeStore === 'dark'}
          <svg class="theme-icon sun-icon" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        {:else}
          <svg class="theme-icon moon-icon" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        {/if}
      </button>

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

      <!-- Mobile Hamburger Button (only when logged in) -->
      {#if $userStore}
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
      {/if}
    </div>
  </div>

  <!-- Mobile Dropdown Menu -->
  {#if isMobileMenuOpen && $userStore}
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
      <a href="/challenges" class="mobile-link" onclick={() => isMobileMenuOpen = false}>
        <span>🏆</span> Challenges
      </a>
      <button class="mobile-link theme-mobile-link" onclick={toggleTheme}>
        {#if $themeStore === 'dark'}
          <span>☀️</span> Switch to Light Mode
        {:else}
          <span>🌙</span> Switch to Dark Mode
        {/if}
      </button>
      <button class="mobile-link logout-link" onclick={handleLogout}>
        <span>🚪</span> Sign Out ({$userStore.name})
      </button>
    </div>
  {/if}
</nav>

<style>
  .nav-bar {
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--nav-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle);
    transition: background 0.25s ease, border-color 0.25s ease;
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
    background: var(--border-subtle);
  }

  .nav-link.active {
    color: var(--accent-emerald);
    background: rgba(16, 185, 129, 0.12);
  }

  .nav-auth {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }

  .theme-toggle-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    background: var(--nav-user-chip);
    border: 1px solid var(--border-subtle);
    color: var(--text-muted);
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .theme-toggle-btn:hover {
    color: var(--accent-amber);
    background: var(--border-hover);
    border-color: var(--border-hover);
    transform: scale(1.08);
  }

  .theme-icon {
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .theme-toggle-btn:hover .theme-icon {
    transform: rotate(20deg);
  }

  .user-chip {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: var(--nav-user-chip);
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
    color: #ffffff;
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
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-top: 1px solid var(--border-subtle);
    box-shadow: var(--shadow-card);
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
    background: var(--border-subtle);
    transition: all 0.2s ease;
  }

  .mobile-link:hover {
    background: var(--border-hover);
  }

  .theme-mobile-link {
    width: 100%;
    text-align: left;
    color: var(--accent-cyan);
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
