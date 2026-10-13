<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { userStore, addToast } from '$lib/stores';
  import { goto } from '$app/navigation';

  let authConfig = $state<{ google_client_id: string; google_auth_enabled: boolean; dev_login_enabled: boolean } | null>(null);
  let isLoading = $state(true);
  let isLoggingIn = $state(false);

  onMount(async () => {
    // If already logged in, redirect to dashboard
    if ($userStore) {
      goto('/');
      return;
    }

    try {
      authConfig = await api.getAuthConfig();
    } catch (e) {
      console.error(e);
    } finally {
      isLoading = false;
    }

    // Initialize Google Identity Services if client ID is set
    initGoogleButton();
  });

  function initGoogleButton() {
    if (typeof window !== 'undefined' && (window as any).google && authConfig?.google_client_id) {
      try {
        (window as any).google.accounts.id.initialize({
          client_id: authConfig.google_client_id,
          callback: handleGoogleCredentialResponse,
        });

        const btnContainer = document.getElementById('google-btn-container');
        if (btnContainer) {
          (window as any).google.accounts.id.renderButton(btnContainer, {
            theme: 'filled_black',
            size: 'large',
            text: 'continue_with',
            shape: 'rectangular',
            width: 280
          });
        }
      } catch (err) {
        console.warn('Google Identity initialization error:', err);
      }
    }
  }

  $effect(() => {
    if (authConfig?.google_client_id) {
      setTimeout(initGoogleButton, 150);
    }
  });

  async function handleGoogleCredentialResponse(response: any) {
    if (!response.credential) return;
    isLoggingIn = true;
    try {
      const data = await api.verifyGoogleToken(response.credential);
      userStore.set(data.user);
      addToast('Welcome Back! 🔥', `Signed in as ${data.user.name}.`, 'success');
      goto('/');
    } catch (err: any) {
      addToast('Authentication Failed', err.message || 'Could not verify Google ID token', 'error');
    } finally {
      isLoggingIn = false;
    }
  }

  async function handleDemoLogin() {
    isLoggingIn = true;
    try {
      const data = await api.demoLogin();
      userStore.set(data.user);
      addToast('Demo Mode Activated! ⚡', 'Logged in as Demo Athlete with preloaded sample workouts.', 'success');
      goto('/');
    } catch (err: any) {
      addToast('Demo Login Failed', err.message || 'Error logging in', 'error');
    } finally {
      isLoggingIn = false;
    }
  }
</script>

<div class="login-page-wrapper">
  <div class="login-card glass-card animate-pop-in">
    <div class="login-brand">
      <div class="logo-icon">⚡</div>
      <h1 class="brand-title">PULSE<span class="highlight">FIT</span></h1>
      <p class="brand-tagline">Track your workouts, reps, and streaks.</p>
    </div>

    <div class="login-body">
      {#if isLoading}
        <div class="login-loading">
          <div class="spinner"></div>
          <p>Connecting to authentication servers...</p>
        </div>
      {:else}
        <!-- Google Sign In Section -->
        <div class="google-auth-section">
          {#if authConfig?.google_auth_enabled}

            <!-- Standard OAuth redirect link -->
            <a href="/api/auth/google/login" class="btn btn-secondary google-direct-btn">
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
              </svg>
              <span>Sign in with Google</span>
            </a>
          {:else}
            <!-- Notice when Google credentials are yet to be put in .env -->
            <div class="google-setup-notice">
              <span class="notice-icon">ℹ️</span>
              <div class="notice-content">
                <strong>Google OAuth Ready</strong>
                <p>To enable live Google Sign-In, add your <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> to your <code>.env</code> file.</p>
              </div>
            </div>
          {/if}
        </div>

        <!-- Demo Login Option -->
        {#if authConfig?.dev_login_enabled}
          <div class="demo-section">
            <div class="divider">
              <span>EXPLORE INSTANTLY</span>
            </div>
            <button
              class="btn btn-primary btn-demo"
              disabled={isLoggingIn}
              onclick={handleDemoLogin}
            >
              <span class="demo-bolt">⚡</span>
              <span>{isLoggingIn ? 'Signing in...' : 'Sign In as Demo Athlete'}</span>
            </button>
            <p class="demo-hint">Explore the full workout tracking interface with pre-seeded history and streak stats!</p>
          </div>
        {/if}
      {/if}
    </div>

    <div class="login-footer">
      <span>Safe & Secure • Direct OAuth2 • MongoDB Storage</span>
    </div>
  </div>
</div>

<style>
  .login-page-wrapper {
    min-height: calc(100vh - 80px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
  }

  .login-card {
    width: 100%;
    max-width: 440px;
    padding: 2.5rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
    border: 1px solid var(--border-hover);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
    text-align: center;
  }

  .login-brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .logo-icon {
    width: 52px;
    height: 52px;
    background: var(--gradient-emerald-cyan);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.75rem;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
    margin-bottom: 0.25rem;
  }

  .brand-title {
    font-size: 1.85rem;
    font-weight: 900;
    letter-spacing: -0.02em;
  }

  .brand-title .highlight {
    color: var(--accent-emerald-light);
  }

  .brand-tagline {
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .login-body {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .google-auth-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  .google-btn-box {
    min-height: 44px;
    display: flex;
    justify-content: center;
  }

  .google-direct-btn {
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 0.95rem;
    gap: 0.75rem;
  }

  .google-setup-notice {
    background: rgba(6, 182, 212, 0.08);
    border: 1px solid rgba(6, 182, 212, 0.25);
    border-radius: var(--radius-md);
    padding: 0.85rem 1rem;
    display: flex;
    gap: 0.75rem;
    text-align: left;
    font-size: 0.82rem;
  }

  .notice-icon {
    font-size: 1.2rem;
  }

  .notice-content strong {
    color: var(--accent-cyan-light);
    display: block;
    margin-bottom: 0.2rem;
  }

  .notice-content p {
    color: var(--text-muted);
    line-height: 1.4;
  }

  .notice-content code {
    background: rgba(0, 0, 0, 0.3);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    color: var(--text-main);
  }

  .divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: var(--text-dim);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    width: 100%;
  }

  .divider::before, .divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid var(--border-subtle);
  }

  .divider:not(:empty)::before {
    margin-right: 0.75em;
  }
  .divider:not(:empty)::after {
    margin-left: 0.75em;
  }

  .demo-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .btn-demo {
    width: 100%;
    padding: 0.8rem 1rem;
    font-size: 1rem;
  }

  .demo-bolt {
    font-size: 1.2rem;
  }

  .demo-hint {
    font-size: 0.78rem;
    color: var(--text-dim);
    line-height: 1.4;
  }

  .login-footer {
    border-top: 1px solid var(--border-subtle);
    padding-top: 1rem;
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .login-loading {
    padding: 2rem 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    color: var(--text-muted);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent-emerald);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
