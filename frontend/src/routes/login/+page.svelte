<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { userStore, addToast } from '$lib/stores';
  import { goto } from '$app/navigation';

  let authConfig = $state<{ google_client_id: string; google_auth_enabled: boolean; dev_login_enabled: boolean } | null>(null);
  let isLoading = $state(true);
  let isLoggingIn = $state(false);

  // Email / Password Form State
  let authMode = $state<'login' | 'register'>('login');
  let email = $state('');
  let password = $state('');
  let name = $state('');
  let formError = $state('');

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
  });

  async function handleEmailAuth(e: Event) {
    e.preventDefault();
    formError = '';

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      formError = 'Please enter a valid email address.';
      return;
    }

    if (!password || password.length < 6) {
      formError = 'Password must be at least 6 characters long.';
      return;
    }

    if (authMode === 'register' && !name.trim()) {
      formError = 'Please enter your full name.';
      return;
    }

    isLoggingIn = true;
    try {
      if (authMode === 'register') {
        const data = await api.registerWithEmail(cleanEmail, password, name.trim());
        userStore.set(data.user);
        addToast('Account Created! 🚀', `Welcome to PulseFit, ${data.user.name}!`, 'success');
        goto('/');
      } else {
        const data = await api.loginWithEmail(cleanEmail, password);
        userStore.set(data.user);
        addToast('Welcome Back! 🔥', `Signed in as ${data.user.name}.`, 'success');
        goto('/');
      }
    } catch (err: any) {
      formError = err.message || 'Authentication failed. Please check your credentials.';
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
    <!-- Brand Header -->
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
        <!-- Primary & Prominent: Google Sign In -->
        <div class="google-prominent-section">
          {#if authConfig?.google_auth_enabled}
            <a href="/api/auth/google/login" class="google-prominent-card animate-pop-in">
              <div class="google-icon-bubble">
                <svg width="22" height="22" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
              </div>
              <div class="google-card-content">
                <span class="google-main-title">Continue with Google</span>
                <span class="google-subtitle">Recommended • 1-click instant access</span>
              </div>
              <div class="google-arrow">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M5 12h14"></path>
                  <path d="M12 5l7 7-7 7"></path>
                </svg>
              </div>
            </a>
          {:else}
            <!-- Notice when Google credentials are not yet configured -->
            <div class="google-setup-notice">
              <span class="notice-icon">ℹ️</span>
              <div class="notice-content">
                <strong>Google OAuth Ready</strong>
                <p>To enable 1-click Google Sign-In, add your <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> to your <code>.env</code> file.</p>
              </div>
            </div>
          {/if}
        </div>

        <!-- Divider -->
        <div class="divider">
          <span>OR SIGN IN WITH EMAIL</span>
        </div>

        <!-- Secondary: Email / Password Section -->
        <div class="email-section">
          <!-- Auth Tabs: Sign In / Create Account -->
          <div class="auth-tabs">
            <button
              type="button"
              class="tab-btn"
              class:active={authMode === 'login'}
              onclick={() => { authMode = 'login'; formError = ''; }}
            >
              Sign In
            </button>
            <button
              type="button"
              class="tab-btn"
              class:active={authMode === 'register'}
              onclick={() => { authMode = 'register'; formError = ''; }}
            >
              Create Account
            </button>
          </div>

          {#if formError}
            <div class="form-error-alert animate-pop-in">
              <span class="error-icon">⚠️</span>
              <span class="error-text">{formError}</span>
            </div>
          {/if}

          <!-- Email & Password Form -->
          <form class="email-auth-form" onsubmit={handleEmailAuth}>
            {#if authMode === 'register'}
              <div class="input-group">
                <label for="name-input">Full Name</label>
                <div class="input-field-wrapper">
                  <span class="field-icon">👤</span>
                  <input
                    id="name-input"
                    type="text"
                    placeholder="e.g. Alex Hunter"
                    bind:value={name}
                    required
                    autocomplete="name"
                  />
                </div>
              </div>
            {/if}

            <div class="input-group">
              <label for="email-input">Email Address</label>
              <div class="input-field-wrapper">
                <span class="field-icon">✉️</span>
                <input
                  id="email-input"
                  type="email"
                  placeholder="athlete@example.com"
                  bind:value={email}
                  required
                  autocomplete="email"
                />
              </div>
            </div>

            <div class="input-group">
              <label for="password-input">Password</label>
              <div class="input-field-wrapper">
                <span class="field-icon">🔒</span>
                <input
                  id="password-input"
                  type="password"
                  placeholder={authMode === 'register' ? 'At least 6 characters' : 'Enter your password'}
                  bind:value={password}
                  required
                  minlength="6"
                  autocomplete={authMode === 'register' ? 'new-password' : 'current-password'}
                />
              </div>
            </div>

            <button
              type="submit"
              class="btn btn-secondary btn-submit"
              disabled={isLoggingIn}
            >
              {#if isLoggingIn}
                <div class="spinner-small"></div>
                <span>Processing...</span>
              {:else if authMode === 'register'}
                <span>Create Account</span>
              {:else}
                <span>Sign In with Email</span>
              {/if}
            </button>
          </form>
        </div>

        <!-- Demo Login Option -->
        {#if authConfig?.dev_login_enabled}
          <div class="demo-section">
            <button
              type="button"
              class="btn-demo-link"
              disabled={isLoggingIn}
              onclick={handleDemoLogin}
            >
              <span>⚡ Want to preview first? <strong>Try Demo Mode</strong></span>
            </button>
          </div>
        {/if}
      {/if}
    </div>

    <div class="login-footer">
      <span>Safe & Secure • Direct Email & OAuth2 • MongoDB Storage</span>
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
    padding: 2.25rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    border: 1px solid var(--border-hover);
    box-shadow: var(--shadow-card);
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

  /* Prominent Google Sign-In Card */
  .google-prominent-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .google-prominent-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.95rem 1.25rem;
    background: var(--google-card-bg);
    border: 1.5px solid rgba(66, 133, 244, 0.4);
    border-radius: var(--radius-md);
    text-decoration: none;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: var(--shadow-sm), 0 0 15px rgba(66, 133, 244, 0.12);
    position: relative;
  }

  .google-prominent-card:hover {
    border-color: #4285f4;
    background: var(--google-card-bg);
    box-shadow: var(--shadow-card), 0 0 24px rgba(66, 133, 244, 0.25);
    transform: translateY(-2px);
  }

  .google-icon-bubble {
    width: 40px;
    height: 40px;
    background: #ffffff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
  }

  .google-card-content {
    display: flex;
    flex-direction: column;
    text-align: left;
    flex: 1;
    gap: 0.15rem;
  }

  .google-main-title {
    font-size: 1.02rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.01em;
  }

  .google-subtitle {
    font-size: 0.76rem;
    color: var(--accent-cyan-light);
    font-weight: 500;
  }

  .google-arrow {
    color: var(--text-muted);
    transition: transform 0.2s ease, color 0.2s ease;
  }

  .google-prominent-card:hover .google-arrow {
    color: #ffffff;
    transform: translateX(4px);
  }

  .google-setup-notice {
    background: rgba(6, 182, 212, 0.08);
    border: 1px solid rgba(6, 182, 212, 0.25);
    border-radius: var(--radius-md);
    padding: 0.75rem 0.85rem;
    display: flex;
    gap: 0.65rem;
    text-align: left;
    font-size: 0.8rem;
  }

  .notice-icon {
    font-size: 1.1rem;
  }

  .notice-content strong {
    color: var(--accent-cyan-light);
    display: block;
    margin-bottom: 0.15rem;
  }

  .notice-content p {
    color: var(--text-muted);
    line-height: 1.35;
  }

  .notice-content code {
    background: rgba(0, 0, 0, 0.3);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    color: var(--text-main);
  }

  /* Divider */
  .divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: var(--text-dim);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    width: 100%;
    margin: 0.25rem 0;
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

  /* Secondary: Email Section */
  .email-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .auth-tabs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    background: rgba(15, 23, 42, 0.6);
    padding: 4px;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
  }

  .tab-btn {
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 0.55rem 0.5rem;
    font-size: 0.85rem;
    font-weight: 600;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .tab-btn:hover {
    color: var(--text-main);
  }

  .tab-btn.active {
    background: rgba(30, 41, 59, 0.9);
    color: var(--accent-emerald-light);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
  }

  .form-error-alert {
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: var(--radius-md);
    padding: 0.65rem 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    text-align: left;
    font-size: 0.84rem;
    color: #fca5a5;
  }

  .email-auth-form {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    text-align: left;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .input-group label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .input-field-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .field-icon {
    position: absolute;
    left: 0.85rem;
    font-size: 0.95rem;
    pointer-events: none;
    opacity: 0.7;
  }

  .input-field-wrapper input {
    width: 100%;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.65rem 0.85rem 0.65rem 2.4rem;
    color: var(--text-main);
    font-size: 0.9rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .input-field-wrapper input:focus {
    outline: none;
    border-color: var(--accent-emerald);
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
  }

  .btn-submit {
    width: 100%;
    padding: 0.7rem 1rem;
    font-size: 0.92rem;
    font-weight: 600;
    margin-top: 0.15rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  /* Demo Link */
  .demo-section {
    display: flex;
    justify-content: center;
    margin-top: 0.25rem;
  }

  .btn-demo-link {
    background: none;
    border: none;
    color: var(--text-dim);
    font-size: 0.82rem;
    cursor: pointer;
    padding: 0.4rem;
    transition: color 0.2s ease;
  }

  .btn-demo-link:hover {
    color: var(--text-main);
  }

  .btn-demo-link strong {
    color: var(--accent-emerald-light);
    text-decoration: underline;
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

  .spinner-small {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-top-color: #ffffff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }
</style>
