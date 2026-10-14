<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { addToast, userStore } from '$lib/stores';
  import type { ChallengeItem, ChallengeType, ExerciseItem } from '$lib/types';

  let challenges = $state<ChallengeItem[]>([]);
  let exercises = $state<ExerciseItem[]>([]);
  let isLoading = $state(true);

  // Selected challenge for detail / leaderboard view
  let selectedChallenge = $state<ChallengeItem | null>(null);

  // Modals state
  let isCreateModalOpen = $state(false);
  let isJoinModalOpen = $state(false);

  // Create Form State
  let newTitle = $state('October Century Push-ups');
  let newDescription = $state('Race to 1,000 total push-ups this month. First to finish wins bragging rights!');
  let newType = $state<ChallengeType>('total_volume');
  let newExercise = $state('Push-ups');
  let newTargetValue = $state(1000);
  let newStartDate = $state(new Date().toISOString().split('T')[0]);
  let newEndDate = $state(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  let isSubmittingCreate = $state(false);

  // Derive duration in days between start and end date
  let durationDaysDiff = $derived.by(() => {
    if (!newStartDate || !newEndDate) return null;
    const s = new Date(newStartDate).getTime();
    const e = new Date(newEndDate).getTime();
    return Math.round((e - s) / (24 * 60 * 60 * 1000));
  });

  // Join Form State
  let joinCode = $state('');
  let isSubmittingJoin = $state(false);

  // Action states
  let isLeaving = $state(false);
  let isDeleting = $state(false);

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    isLoading = true;
    try {
      const [challengesData, exData] = await Promise.all([
        api.getChallenges(),
        api.getExercises().catch(() => [])
      ]);
      challenges = challengesData || [];
      exercises = exData || [];
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to load challenges', 'error');
    } finally {
      isLoading = false;
    }
  }

  let selectedExerciseObj = $derived(
    exercises.find(e => e.name.toLowerCase() === newExercise.toLowerCase())
  );
  let isDurationExercise = $derived(
    selectedExerciseObj?.type === 'duration' || newExercise.toLowerCase() === 'plank'
  );

  function isDurationChallenge(challenge: ChallengeItem): boolean {
    if (challenge.target_unit === 'minutes') return true;
    const ex = exercises.find(e => e.name.toLowerCase() === (challenge.exercise_name || '').toLowerCase());
    return ex?.type === 'duration' || (challenge.exercise_name || '').toLowerCase() === 'plank';
  }

  function handleExerciseChange() {
    const exObj = exercises.find(e => e.name.toLowerCase() === newExercise.toLowerCase());
    const isDur = exObj?.type === 'duration' || newExercise.toLowerCase() === 'plank';
    if (isDur) {
      if (newType === 'total_volume') {
        newTargetValue = 60; // 60 minutes
        newTitle = `October ${newExercise} Endurance`;
        newDescription = `Race to log cumulative time in ${newExercise}! First to reach target wins bragging rights.`;
      } else {
        newTargetValue = 5; // 5 min/day
        newTitle = `Daily ${newExercise} Streak`;
        newDescription = `Hold a daily ${newExercise} target every single day!`;
      }
    } else {
      if (newType === 'total_volume') {
        newTargetValue = 1000;
        newTitle = `October Century ${newExercise}`;
        newDescription = `Race to 1,000 total ${newExercise.toLowerCase()} this month. First to finish wins bragging rights!`;
      } else {
        newTargetValue = 50;
        newTitle = `Daily ${newExercise} Streak`;
        newDescription = `Hit 50 ${newExercise.toLowerCase()} every day to keep your streak alive!`;
      }
    }
  }

  function setType(type: ChallengeType) {
    newType = type;
    if (isDurationExercise) {
      if (type === 'total_volume') {
        newTargetValue = 60;
      } else {
        newTargetValue = 5;
      }
    } else {
      if (type === 'total_volume') {
        newTargetValue = 1000;
      } else {
        newTargetValue = 50;
      }
    }
  }

  function setDurationDays(days: number) {
    const start = new Date();
    const end = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
    newStartDate = start.toISOString().split('T')[0];
    newEndDate = end.toISOString().split('T')[0];
  }

  async function handleCreateChallenge(e: SubmitEvent) {
    e.preventDefault();
    if (!newTitle.trim()) {
      addToast('Title Required', 'Please enter a title for your challenge.', 'error');
      return;
    }
    if (newTargetValue <= 0) {
      addToast('Invalid Target', 'Target value must be greater than zero.', 'error');
      return;
    }
    if (newEndDate < newStartDate) {
      addToast('Invalid Dates', 'End date cannot be earlier than start date.', 'error');
      return;
    }

    isSubmittingCreate = true;
    try {
      const created = await api.createChallenge({
        title: newTitle.trim(),
        description: newDescription.trim(),
        challenge_type: newType,
        exercise_name: newExercise,
        target_value: Number(newTargetValue),
        target_unit: isDurationExercise ? 'minutes' : 'reps',
        start_date: newStartDate,
        end_date: newEndDate
      });
      addToast('Challenge Created! 🏆', `Invite friends using code: ${created.invite_code}`, 'success');
      challenges = [created, ...challenges];
      isCreateModalOpen = false;
      selectedChallenge = created;
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to create challenge', 'error');
    } finally {
      isSubmittingCreate = false;
    }
  }

  async function handleJoinChallenge(e: SubmitEvent) {
    e.preventDefault();
    const code = joinCode.trim().toUpperCase();
    if (!code) {
      addToast('Code Required', 'Please enter an invite code.', 'error');
      return;
    }

    isSubmittingJoin = true;
    try {
      const joined = await api.joinChallenge(code);
      addToast('Joined Challenge! 🎉', `Welcome to "${joined.title}"!`, 'success');

      // Update in list
      const idx = challenges.findIndex(c => c._id === joined._id);
      if (idx >= 0) {
        challenges[idx] = joined;
      } else {
        challenges = [joined, ...challenges];
      }

      isJoinModalOpen = false;
      joinCode = '';
      selectedChallenge = joined;
    } catch (e: any) {
      addToast('Join Failed', e.message || 'Invalid or expired invite code', 'error');
    } finally {
      isSubmittingJoin = false;
    }
  }

  async function handleCopyInviteCode(code: string) {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(code);
      } else {
        const input = document.createElement('input');
        input.value = code;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
      }
      addToast('Invite Code Copied! 📋', `Share code ${code} with your workout partners.`, 'success');
    } catch {
      addToast('Code: ' + code, 'Copy the invite code manually to share.', 'info');
    }
  }

  async function handleLeaveChallenge(challengeId: string) {
    if (!confirm('Are you sure you want to leave this challenge?')) return;
    isLeaving = true;
    try {
      await api.leaveChallenge(challengeId);
      addToast('Left Challenge', 'You have left the group challenge.', 'info');
      challenges = challenges.filter(c => c._id !== challengeId);
      selectedChallenge = null;
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to leave challenge', 'error');
    } finally {
      isLeaving = false;
    }
  }

  async function handleDeleteChallenge(challengeId: string) {
    if (!confirm('Are you sure you want to delete this challenge for all members? This cannot be undone.')) return;
    isDeleting = true;
    try {
      await api.deleteChallenge(challengeId);
      addToast('Challenge Deleted', 'The challenge was deleted.', 'info');
      challenges = challenges.filter(c => c._id !== challengeId);
      selectedChallenge = null;
    } catch (e: any) {
      addToast('Error', e.message || 'Failed to delete challenge', 'error');
    } finally {
      isDeleting = false;
    }
  }

  async function refreshSelectedChallenge() {
    if (!selectedChallenge) return;
    try {
      const refreshed = await api.getChallenge(selectedChallenge._id);
      selectedChallenge = refreshed;
      const idx = challenges.findIndex(c => c._id === refreshed._id);
      if (idx >= 0) challenges[idx] = refreshed;
    } catch {
      // ignore
    }
  }

  function formatDate(dStr: string) {
    if (!dStr) return '';
    const parts = dStr.split('-');
    if (parts.length < 3) return dStr;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
</script>

<div class="container challenges-container">
  <!-- Page Header -->
  <div class="page-header animate-fade-in">
    <div class="header-left">
      <h1 class="page-title">
        <span class="icon">🏆</span> Group Challenges
      </h1>
      <p class="page-sub">
        Compete with friends, track group progress in real time, and climb the live leaderboard.
      </p>
    </div>
    <div class="header-actions">
      <button class="btn btn-secondary" onclick={() => isJoinModalOpen = true}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
          <polyline points="10 17 15 12 10 7"></polyline>
          <line x1="15" y1="12" x2="3" y2="12"></line>
        </svg>
        <span>Join with Code</span>
      </button>
      <button class="btn btn-primary" onclick={() => isCreateModalOpen = true}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        <span>Create Challenge</span>
      </button>
    </div>
  </div>

  <!-- Summary Stats Banner -->
  <div class="stats-overview-grid animate-fade-in">
    <div class="summary-metric-card glass-card">
      <span class="metric-icon">🔥</span>
      <div class="metric-info">
        <span class="metric-val">{challenges.filter(c => c.status === 'active').length}</span>
        <span class="metric-lbl">Active Challenges</span>
      </div>
    </div>
    <div class="summary-metric-card glass-card">
      <span class="metric-icon">👥</span>
      <div class="metric-info">
        <span class="metric-val">
          {challenges.reduce((acc, c) => acc + c.participants_count, 0)}
        </span>
        <span class="metric-lbl">Total Competitors</span>
      </div>
    </div>
    <div class="summary-metric-card glass-card">
      <span class="metric-icon">🥇</span>
      <div class="metric-info">
        <span class="metric-val">
          {challenges.filter(c => c.user_progress?.rank === 1).length}
        </span>
        <span class="metric-lbl">#1 Podium Spots</span>
      </div>
    </div>
    <div class="summary-metric-card glass-card">
      <span class="metric-icon">🎉</span>
      <div class="metric-info">
        <span class="metric-val">
          {challenges.filter(c => c.user_progress?.is_completed).length}
        </span>
        <span class="metric-lbl">Completed Goals</span>
      </div>
    </div>
  </div>

  <!-- Content Section -->
  {#if isLoading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading your group challenges...</p>
    </div>
  {:else if challenges.length === 0}
    <div class="empty-state glass-card animate-pop-in">
      <div class="empty-icon">🏆</div>
      <h2>No Group Challenges Yet</h2>
      <p>
        Challenge your workout partners or squad! Create a total volume race or a daily consistency streak,
        then share the invite code.
      </p>
      <div class="empty-actions">
        <button class="btn btn-primary btn-lg" onclick={() => isCreateModalOpen = true}>
          <span>⚡ Create First Challenge</span>
        </button>
        <button class="btn btn-secondary btn-lg" onclick={() => isJoinModalOpen = true}>
          <span>🔑 Enter Invite Code</span>
        </button>
      </div>
    </div>
  {:else}
    <div class="challenges-grid">
      {#each challenges as challenge (challenge._id)}
        {@const userProg = challenge.user_progress}
        {@const isVolume = challenge.challenge_type === 'total_volume'}
        {@const isDur = isDurationChallenge(challenge)}
        <div class="challenge-card glass-card animate-pop-in">
          <!-- Card Header Badges -->
          <div class="card-badges-row">
            <div class="type-pill" class:pill-volume={isVolume} class:pill-streak={!isVolume}>
              {#if isVolume}
                <span>⚡ Total Volume Target</span>
              {:else}
                <span>🔥 Daily Streak Target</span>
              {/if}
            </div>
            <span class="status-badge" class:status-active={challenge.status === 'active'} class:status-completed={challenge.status === 'completed'}>
              {challenge.status === 'active' ? `${challenge.days_remaining}d left` : challenge.status}
            </span>
          </div>

          <!-- Title & Description -->
          <div class="card-main">
            <h3 class="challenge-title">{challenge.title}</h3>
            {#if challenge.description}
              <p class="challenge-desc">{challenge.description}</p>
            {/if}

            <div class="target-chip-row">
              <span class="badge badge-emerald">
                🎯 {challenge.exercise_name || 'All Workouts'}
              </span>
              <span class="badge badge-cyan">
                {#if isVolume}
                  {challenge.target_value.toLocaleString()} {isDur ? 'Total Minutes' : 'Total Reps'}
                {:else}
                  {challenge.target_value} {isDur ? 'Mins/Day Streak' : 'Reps/Day Streak'}
                {/if}
              </span>
              <span class="badge badge-subtle">
                📅 {formatDate(challenge.start_date)} - {formatDate(challenge.end_date)}
              </span>
            </div>
          </div>

          <!-- User Progress Section in this Challenge -->
          {#if userProg}
            <div class="user-progress-box">
              <div class="progress-info-row">
                <span class="prog-label">
                  Your Progress
                  {#if userProg.rank === 1}
                    <span class="rank-tag rank-1">🥇 #1 Leader</span>
                  {:else if userProg.rank === 2}
                    <span class="rank-tag rank-2">🥈 #2</span>
                  {:else if userProg.rank === 3}
                    <span class="rank-tag rank-3">🥉 #3</span>
                  {:else}
                    <span class="rank-tag">Rank #{userProg.rank}</span>
                  {/if}
                </span>
                <span class="prog-pct">{userProg.progress_percentage}%</span>
              </div>

              <!-- Progress bar -->
              <div class="progress-track">
                <div
                  class="progress-fill"
                  class:fill-complete={userProg.is_completed}
                  style="width: {userProg.progress_percentage}%"
                ></div>
              </div>

              <div class="progress-detail-row">
                {#if isVolume}
                  <span>{userProg.completed_reps.toLocaleString()} / {challenge.target_value.toLocaleString()} {isDurationChallenge(challenge) ? 'mins' : 'reps'}</span>
                {:else}
                  <span>{userProg.days_completed} / {userProg.target_days} days achieved ({userProg.current_streak}d streak)</span>
                {/if}
                {#if userProg.is_completed}
                  <span class="finished-tag">🎉 Target Reached!</span>
                {/if}
              </div>
            </div>
          {/if}

          <!-- Footer: Participants & Actions -->
          <div class="card-footer">
            <div class="participants-summary">
              <div class="avatar-stack">
                {#each challenge.leaderboard.slice(0, 4) as p, i}
                  <div class="stacked-avatar" title="{p.name} (#{p.rank})">
                    {p.name.charAt(0).toUpperCase()}
                  </div>
                {/each}
              </div>
              <span class="participants-count">
                {challenge.participants_count} {challenge.participants_count === 1 ? 'member' : 'members'}
              </span>
            </div>

            <div class="footer-actions">
              <button
                class="btn-code-copy"
                onclick={(e) => { e.stopPropagation(); handleCopyInviteCode(challenge.invite_code); }}
                title="Copy Invite Code: {challenge.invite_code}"
              >
                <span>🔑 {challenge.invite_code}</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>

              <button
                class="btn btn-secondary btn-sm"
                onclick={() => selectedChallenge = challenge}
              >
                <span>View Leaderboard</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Challenge Detail & Live Leaderboard Modal -->
{#if selectedChallenge}
  <div class="modal-backdrop" role="presentation" onclick={() => selectedChallenge = null}>
    <div class="modal-content modal-leaderboard animate-pop-in" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()}>
      <div class="modal-header">
        <div class="modal-header-content">
          <div class="header-tag-row">
            <span class="type-pill" class:pill-volume={selectedChallenge.challenge_type === 'total_volume'}>
              {selectedChallenge.challenge_type === 'total_volume' ? '⚡ Total Volume' : '🔥 Daily Streak'}
            </span>
            <span class="status-badge status-active">
              {selectedChallenge.status === 'active' ? `${selectedChallenge.days_remaining} Days Remaining` : selectedChallenge.status}
            </span>
          </div>
          <h2 class="modal-title">{selectedChallenge.title}</h2>
          {#if selectedChallenge.description}
            <p class="modal-subtitle">{selectedChallenge.description}</p>
          {/if}
        </div>
        <button class="close-btn" onclick={() => selectedChallenge = null} aria-label="Close modal">✕</button>
      </div>

      <!-- Challenge Specs & Invite Bar -->
      <div class="challenge-detail-banner">
        <div class="detail-stat">
          <span class="stat-lbl">{isDurationChallenge(selectedChallenge) ? 'Total Target Time' : 'Target Goal'}</span>
          <span class="stat-val highlight">
            {#if selectedChallenge.challenge_type === 'total_volume'}
              {selectedChallenge.target_value.toLocaleString()} {selectedChallenge.exercise_name || 'Total'} {isDurationChallenge(selectedChallenge) ? 'Minutes' : 'Reps'}
            {:else}
              {selectedChallenge.target_value} {selectedChallenge.exercise_name || (isDurationChallenge(selectedChallenge) ? 'Mins' : 'Reps')} / Day
            {/if}
          </span>
        </div>
        <div class="detail-stat">
          <span class="stat-lbl">Timeframe</span>
          <span class="stat-val">
            {formatDate(selectedChallenge.start_date)} - {formatDate(selectedChallenge.end_date)}
          </span>
        </div>
        <div class="detail-stat invite-stat">
          <span class="stat-lbl">Invite Code</span>
          <button
            class="invite-copy-pill"
            onclick={() => handleCopyInviteCode(selectedChallenge!.invite_code)}
          >
            <span class="code-text">{selectedChallenge.invite_code}</span>
            <span class="copy-hint">📋 Click to Copy</span>
          </button>
        </div>
      </div>

      <!-- Live Group Leaderboard -->
      <div class="leaderboard-section">
        <div class="section-title-row">
          <h3>🏆 Live Group Leaderboard</h3>
          <button class="btn-refresh" onclick={refreshSelectedChallenge} title="Refresh Live Data">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            <span>Live Sync</span>
          </button>
        </div>

        <div class="leaderboard-table">
          {#each selectedChallenge.leaderboard as participant (participant.user_id)}
            {@const isMe = participant.user_id === $userStore?._id}
            {@const isFinished = participant.is_completed}
            <div
              class="leaderboard-row"
              class:row-me={isMe}
              class:row-podium={participant.rank <= 3}
            >
              <!-- Rank Medal / Number -->
              <div class="rank-column">
                {#if participant.rank === 1}
                  <span class="medal-icon medal-gold">🥇</span>
                {:else if participant.rank === 2}
                  <span class="medal-icon medal-silver">🥈</span>
                {:else if participant.rank === 3}
                  <span class="medal-icon medal-bronze">🥉</span>
                {:else}
                  <span class="rank-num">#{participant.rank}</span>
                {/if}
              </div>

              <!-- Athlete Avatar & Name -->
              <div class="athlete-column">
                <div class="athlete-avatar">
                  {participant.name.charAt(0).toUpperCase()}
                </div>
                <div class="athlete-name-group">
                  <span class="athlete-name">
                    {participant.name}
                    {#if isMe}
                      <span class="badge badge-emerald-sm">You</span>
                    {/if}
                  </span>
                  {#if isFinished}
                    <span class="athlete-status-badge">🎉 Target Reached</span>
                  {/if}
                </div>
              </div>

              <!-- Progress Bar & Rep Stats -->
              <div class="progress-column">
                <div class="prog-bar-wrapper">
                  <div class="progress-track">
                    <div
                      class="progress-fill"
                      class:fill-gold={participant.rank === 1}
                      class:fill-complete={isFinished}
                      style="width: {participant.progress_percentage}%"
                    ></div>
                  </div>
                  <span class="pct-label">{participant.progress_percentage}%</span>
                </div>

                <div class="reps-metric-label">
                  {#if selectedChallenge.challenge_type === 'total_volume'}
                    <strong>{participant.completed_reps.toLocaleString()}</strong> / {selectedChallenge.target_value.toLocaleString()} {isDurationChallenge(selectedChallenge) ? 'mins' : 'reps'}
                  {:else}
                    <strong>{participant.days_completed}</strong> / {participant.target_days} days ({participant.current_streak}d streak)
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer leaderboard-footer">
        <div class="footer-left">
          {#if selectedChallenge.creator_id === $userStore?._id}
            <button
              class="btn btn-danger btn-sm"
              onclick={() => handleDeleteChallenge(selectedChallenge!._id)}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete Challenge'}
            </button>
          {:else}
            <button
              class="btn btn-outline btn-sm"
              onclick={() => handleLeaveChallenge(selectedChallenge!._id)}
              disabled={isLeaving}
            >
              {isLeaving ? 'Leaving...' : 'Leave Challenge'}
            </button>
          {/if}
        </div>
        <button class="btn btn-secondary" onclick={() => selectedChallenge = null}>
          Close
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Create Challenge Modal -->
{#if isCreateModalOpen}
  <div class="modal-backdrop" role="presentation" onclick={() => isCreateModalOpen = false}>
    <div class="modal-content animate-pop-in" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()}>
      <div class="modal-header">
        <div class="modal-header-content">
          <h2 class="modal-title">Create Group Challenge</h2>
          <p class="modal-subtitle">Start a private challenge and invite workout partners with a code.</p>
        </div>
        <button class="close-btn" onclick={() => isCreateModalOpen = false} aria-label="Close modal">✕</button>
      </div>

      <form class="modal-form" onsubmit={handleCreateChallenge}>
        <div class="form-group">
          <label for="ch-title" class="form-label">Challenge Title</label>
          <input
            id="ch-title"
            type="text"
            class="input-field"
            bind:value={newTitle}
            placeholder="e.g. October Century Push-ups"
            required
          />
        </div>

        <div class="form-group">
          <label for="ch-desc" class="form-label">Description (Optional)</label>
          <textarea
            id="ch-desc"
            class="input-field textarea-field"
            bind:value={newDescription}
            placeholder="Rules, goals, and motivation for participants..."
            rows="2"
          ></textarea>
        </div>

        <!-- Challenge Style Switcher (Hybrid) -->
        <div class="form-group">
          <span class="form-label">Challenge Style</span>
          <div class="style-selector-grid">
            <button
              type="button"
              class="style-card"
              class:active={newType === 'total_volume'}
              onclick={() => setType('total_volume')}
            >
              <span class="style-icon">⚡</span>
              <div class="style-text">
                <span class="style-title">Total Volume Goal</span>
                <span class="style-desc">
                  {#if isDurationExercise}
                    Race to complete cumulative time (e.g. 60 Minutes total)
                  {:else}
                    Race to complete cumulative reps (e.g. 1,000 Push-ups total)
                  {/if}
                </span>
              </div>
            </button>

            <button
              type="button"
              class="style-card"
              class:active={newType === 'daily_streak'}
              onclick={() => setType('daily_streak')}
            >
              <span class="style-icon">🔥</span>
              <div class="style-text">
                <span class="style-title">Daily Consistency Streak</span>
                <span class="style-desc">
                  {#if isDurationExercise}
                    Hit a target every day (e.g. 5 minutes/day streak)
                  {:else}
                    Hit a target every day (e.g. 50 pushups/day streak)
                  {/if}
                </span>
              </div>
            </button>
          </div>
        </div>

        <!-- Exercise & Target Value -->
        <div class="form-row">
          <div class="form-group">
            <label for="ch-ex" class="form-label">Exercise Target</label>
            <select id="ch-ex" class="input-field" bind:value={newExercise} onchange={handleExerciseChange}>
              <option value="Push-ups">Push-ups</option>
              <option value="Sit-ups">Sit-ups</option>
              <option value="Pull-ups">Pull-ups</option>
              <option value="Squats">Squats</option>
              <option value="Dips">Dips</option>
              <option value="Plank">Plank (Duration)</option>
              <option value="All">All Exercises (Total Volume)</option>
              {#each exercises.filter(e => !['Push-ups', 'Sit-ups', 'Pull-ups', 'Squats', 'Dips', 'Plank'].includes(e.name)) as ex}
                <option value={ex.name}>{ex.name}{ex.type === 'duration' ? ' (Duration)' : ''}</option>
              {/each}
            </select>
          </div>

          <div class="form-group">
            <label for="ch-target" class="form-label">
              {#if isDurationExercise}
                {newType === 'total_volume' ? 'Total Target Time (Minutes)' : 'Daily Target Time (Minutes/Day)'}
              {:else}
                {newType === 'total_volume' ? 'Total Target Reps' : 'Daily Target Reps/Day'}
              {/if}
            </label>
            <input
              id="ch-target"
              type="number"
              class="input-field"
              bind:value={newTargetValue}
              placeholder={isDurationExercise ? 'Minutes (e.g. 60)' : 'Reps (e.g. 1000)'}
              min="1"
              required
            />
            <!-- Quick Target Presets directly inside the target form-group -->
            <div class="target-presets-row">
              <span class="preset-label">Presets:</span>
              {#if isDurationExercise}
                {#if newType === 'total_volume'}
                  <button type="button" class="preset-btn" class:active={newTargetValue === 15} onclick={() => newTargetValue = 15}>15 min</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 30} onclick={() => newTargetValue = 30}>30 min</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 60} onclick={() => newTargetValue = 60}>60 min</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 120} onclick={() => newTargetValue = 120}>120 min</button>
                {:else}
                  <button type="button" class="preset-btn" class:active={newTargetValue === 2} onclick={() => newTargetValue = 2}>2 min/day</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 5} onclick={() => newTargetValue = 5}>5 min/day</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 10} onclick={() => newTargetValue = 10}>10 min/day</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 15} onclick={() => newTargetValue = 15}>15 min/day</button>
                {/if}
              {:else}
                {#if newType === 'total_volume'}
                  <button type="button" class="preset-btn" class:active={newTargetValue === 250} onclick={() => newTargetValue = 250}>250</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 500} onclick={() => newTargetValue = 500}>500</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 1000} onclick={() => newTargetValue = 1000}>1,000</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 2500} onclick={() => newTargetValue = 2500}>2,500</button>
                {:else}
                  <button type="button" class="preset-btn" class:active={newTargetValue === 25} onclick={() => newTargetValue = 25}>25/day</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 50} onclick={() => newTargetValue = 50}>50/day</button>
                  <button type="button" class="preset-btn" class:active={newTargetValue === 100} onclick={() => newTargetValue = 100}>100/day</button>
                {/if}
              {/if}
            </div>
          </div>
        </div>

        <!-- Duration Presets & Dates -->
        <div class="form-group">
          <div class="dates-header-row">
            <span class="form-label">Duration Period</span>
            <div class="duration-quick-pills">
              <button type="button" class="pill-preset" class:active={durationDaysDiff === 7} onclick={() => setDurationDays(7)}>7 Days</button>
              <button type="button" class="pill-preset" class:active={durationDaysDiff === 14} onclick={() => setDurationDays(14)}>14 Days</button>
              <button type="button" class="pill-preset" class:active={durationDaysDiff === 30} onclick={() => setDurationDays(30)}>30 Days</button>
            </div>
          </div>
          <div class="form-row">
            <div class="date-field-col">
              <span class="input-sub-label">Start Date</span>
              <input type="date" class="input-field" bind:value={newStartDate} required />
            </div>
            <div class="date-field-col">
              <span class="input-sub-label">End Date</span>
              <input type="date" class="input-field" bind:value={newEndDate} required />
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick={() => isCreateModalOpen = false}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={isSubmittingCreate}>
            {#if isSubmittingCreate}
              <div class="spinner-small"></div>
              <span>Creating...</span>
            {:else}
              <span>Create Challenge & Generate Code</span>
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Join Challenge Modal -->
{#if isJoinModalOpen}
  <div class="modal-backdrop" role="presentation" onclick={() => isJoinModalOpen = false}>
    <div class="modal-content modal-join animate-pop-in" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()}>
      <div class="modal-header">
        <div class="modal-header-content">
          <h2 class="modal-title">Join Group Challenge</h2>
          <p class="modal-subtitle">Enter the invite code shared with you by a group creator.</p>
        </div>
        <button class="close-btn" onclick={() => isJoinModalOpen = false} aria-label="Close modal">✕</button>
      </div>

      <form class="modal-form" onsubmit={handleJoinChallenge}>
        <div class="form-group">
          <label for="join-code-input" class="form-label">Invite Code</label>
          <div class="code-input-wrapper">
            <input
              id="join-code-input"
              type="text"
              class="input-field code-input"
              bind:value={joinCode}
              placeholder="e.g. FIT-8X2M"
              maxlength="12"
              required
            />
          </div>
          <p class="field-hint">Format: <code>FIT-XXXXXX</code> (case-insensitive)</p>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick={() => isJoinModalOpen = false}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={isSubmittingJoin}>
            {#if isSubmittingJoin}
              <div class="spinner-small"></div>
              <span>Verifying...</span>
            {:else}
              <span>Join Challenge</span>
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .challenges-container {
    padding-top: 1.5rem;
    padding-bottom: 4rem;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.75rem;
    flex-wrap: wrap;
    gap: 1.25rem;
  }

  .page-title {
    font-size: 2rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .page-sub {
    color: var(--text-muted);
    font-size: 0.95rem;
    margin-top: 0.25rem;
  }

  .header-actions {
    display: flex;
    gap: 0.75rem;
  }

  /* Stats Overview Grid */
  .stats-overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .summary-metric-card {
    padding: 1.15rem 1.35rem;
    display: flex;
    align-items: center;
    gap: 1.15rem;
  }

  .metric-icon {
    font-size: 2rem;
  }

  .metric-info {
    display: flex;
    flex-direction: column;
  }

  .metric-val {
    font-size: 1.65rem;
    font-weight: 800;
    color: var(--text-main);
    line-height: 1.1;
  }

  .metric-lbl {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-weight: 600;
    margin-top: 0.15rem;
  }

  /* Empty State */
  .empty-state {
    padding: 4rem 2rem;
    text-align: center;
    max-width: 580px;
    margin: 3rem auto;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .empty-icon {
    font-size: 3.5rem;
    margin-bottom: 1rem;
  }

  .empty-state h2 {
    font-size: 1.6rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
  }

  .empty-state p {
    color: var(--text-muted);
    font-size: 0.95rem;
    line-height: 1.5;
    margin-bottom: 1.75rem;
  }

  .empty-actions {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  /* Challenges Grid */
  .challenges-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 1.5rem;
  }

  .challenge-card {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .challenge-card:hover {
    transform: translateY(-2px);
    border-color: var(--border-hover);
    box-shadow: var(--shadow-glow);
  }

  .card-badges-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .type-pill {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: var(--radius-full);
  }

  .pill-volume {
    background: rgba(16, 185, 129, 0.12);
    color: var(--accent-emerald-light);
    border: 1px solid rgba(16, 185, 129, 0.25);
  }

  .pill-streak {
    background: rgba(6, 182, 212, 0.12);
    color: var(--accent-cyan-light);
    border: 1px solid rgba(6, 182, 212, 0.25);
  }

  .status-badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    background: var(--border-subtle);
    color: var(--text-muted);
  }

  .status-active {
    color: var(--accent-emerald-light);
    background: rgba(16, 185, 129, 0.08);
  }

  .challenge-title {
    font-size: 1.25rem;
    font-weight: 800;
    margin-bottom: 0.35rem;
  }

  .challenge-desc {
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.45;
    margin-bottom: 0.85rem;
  }

  .target-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .badge-subtle {
    background: var(--border-subtle);
    color: var(--text-dim);
    font-size: 0.75rem;
    padding: 0.2rem 0.5rem;
    border-radius: var(--radius-sm);
  }

  /* User Progress Box */
  .user-progress-box {
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  :global([data-theme="light"]) .user-progress-box {
    background: rgba(15, 23, 42, 0.03);
  }

  .progress-info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .prog-label {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .rank-tag {
    font-size: 0.7rem;
    font-weight: 800;
    padding: 0.15rem 0.4rem;
    border-radius: var(--radius-sm);
    background: var(--border-subtle);
    color: var(--text-muted);
  }

  .rank-1 { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
  .rank-2 { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; }
  .rank-3 { background: rgba(180, 83, 9, 0.2); color: #f59e0b; }

  .prog-pct {
    font-size: 0.85rem;
    font-weight: 800;
    color: var(--accent-emerald-light);
  }

  .progress-track {
    height: 8px;
    background: var(--border-subtle);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--gradient-emerald-cyan);
    border-radius: var(--radius-full);
    transition: width 0.4s ease;
  }

  .fill-complete {
    background: linear-gradient(135deg, #fbbf24 0%, #10b981 100%);
  }

  .fill-gold {
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  }

  .progress-detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .finished-tag {
    color: #fbbf24;
    font-weight: 700;
  }

  /* Card Footer */
  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 0.85rem;
    border-top: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .participants-summary {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .avatar-stack {
    display: flex;
  }

  .stacked-avatar {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--border-subtle);
    border: 2px solid var(--bg-card);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 800;
    color: var(--text-main);
    margin-left: -6px;
  }
  .stacked-avatar:first-child { margin-left: 0; }

  .participants-count {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
  }

  .footer-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .btn-code-copy {
    background: var(--border-subtle);
    color: var(--text-main);
    border: 1px solid var(--border-subtle);
    padding: 0.35rem 0.6rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .btn-code-copy:hover {
    border-color: var(--accent-emerald);
    color: var(--accent-emerald-light);
  }

  /* Shared Modal & Form Styles */
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.5rem;
    gap: 1rem;
  }

  .modal-header-content {
    flex: 1;
    min-width: 0;
  }

  .modal-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--text-main);
    letter-spacing: -0.02em;
    margin: 0;
  }

  .modal-subtitle {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin-top: 0.35rem;
    line-height: 1.4;
  }

  .close-btn {
    background: transparent;
    border: none;
    color: var(--text-dim);
    font-size: 1.25rem;
    line-height: 1;
    padding: 0.35rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .close-btn:hover {
    color: var(--text-main);
    background: var(--border-subtle);
  }

  .modal-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .form-label {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--text-main);
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    align-items: flex-start;
  }

  .date-field-col {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.85rem;
    margin-top: 1.5rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border-subtle);
  }

  /* Leaderboard Modal */
  .modal-leaderboard {
    max-width: 680px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
  }

  .header-tag-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .challenge-detail-banner {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.85rem;
    padding: 1rem;
    background: rgba(0, 0, 0, 0.15);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    margin-bottom: 1.5rem;
  }

  :global([data-theme="light"]) .challenge-detail-banner {
    background: rgba(15, 23, 42, 0.03);
  }

  .detail-stat {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .detail-stat .stat-lbl {
    font-size: 0.72rem;
    color: var(--text-dim);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .detail-stat .stat-val {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-main);
  }

  .invite-copy-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: var(--bg-card);
    border: 1px solid var(--border-hover);
    padding: 0.25rem 0.65rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.2s;
  }
  .invite-copy-pill:hover {
    border-color: var(--accent-emerald);
  }
  .invite-copy-pill .code-text {
    font-size: 0.85rem;
    font-weight: 800;
    color: var(--accent-emerald-light);
    letter-spacing: 0.05em;
  }
  .invite-copy-pill .copy-hint {
    font-size: 0.7rem;
    color: var(--text-dim);
  }

  /* Leaderboard Table */
  .leaderboard-section {
    flex: 1;
    overflow-y: auto;
    padding-right: 0.25rem;
  }

  .section-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.85rem;
  }

  .section-title-row h3 {
    font-size: 1.1rem;
    font-weight: 800;
  }

  .btn-refresh {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: transparent;
    border: none;
    color: var(--text-dim);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: color 0.15s;
  }
  .btn-refresh:hover { color: var(--text-main); }

  .leaderboard-table {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .leaderboard-row {
    display: grid;
    grid-template-columns: 44px 1.4fr 1.6fr;
    align-items: center;
    padding: 0.85rem 1rem;
    background: rgba(0, 0, 0, 0.1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    transition: all 0.15s ease;
  }

  :global([data-theme="light"]) .leaderboard-row {
    background: rgba(15, 23, 42, 0.02);
  }

  .row-me {
    border-color: var(--accent-emerald);
    background: rgba(16, 185, 129, 0.05);
  }

  .rank-column {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .medal-icon {
    font-size: 1.35rem;
  }

  .rank-num {
    font-size: 0.85rem;
    font-weight: 800;
    color: var(--text-dim);
  }

  .athlete-column {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .athlete-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 800;
    color: var(--text-main);
  }

  .athlete-name-group {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .athlete-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .badge-emerald-sm {
    font-size: 0.65rem;
    padding: 0.1rem 0.35rem;
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-emerald-light);
    border-radius: var(--radius-sm);
    font-weight: 700;
  }

  .athlete-status-badge {
    font-size: 0.7rem;
    font-weight: 700;
    color: #fbbf24;
  }

  .progress-column {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .prog-bar-wrapper {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .prog-bar-wrapper .progress-track {
    flex: 1;
    height: 9px;
  }

  .pct-label {
    font-size: 0.8rem;
    font-weight: 800;
    color: var(--text-main);
    min-width: 35px;
    text-align: right;
  }

  .reps-metric-label {
    font-size: 0.75rem;
    color: var(--text-dim);
    text-align: right;
  }

  /* Style Selector in Create Modal */
  .style-selector-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }

  .style-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.85rem;
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .style-card:hover {
    border-color: var(--border-hover);
  }

  .style-card.active {
    border-color: var(--accent-emerald);
    background: rgba(16, 185, 129, 0.08);
  }

  .style-icon {
    font-size: 1.35rem;
    line-height: 1;
  }

  .style-title {
    display: block;
    font-size: 0.85rem;
    font-weight: 800;
    color: var(--text-main);
    margin-bottom: 0.15rem;
  }

  .style-desc {
    display: block;
    font-size: 0.72rem;
    color: var(--text-muted);
    line-height: 1.35;
  }

  .target-presets-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.45rem;
    flex-wrap: wrap;
  }

  .preset-label {
    font-size: 0.75rem;
    color: var(--text-dim);
    font-weight: 600;
  }

  .preset-btn {
    background: var(--border-subtle);
    border: 1px solid transparent;
    color: var(--text-muted);
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s;
  }
  .preset-btn:hover {
    border-color: var(--border-hover);
    color: var(--text-main);
  }
  .preset-btn.active {
    background: rgba(16, 185, 129, 0.15);
    border-color: var(--accent-emerald);
    color: var(--accent-emerald-light);
  }

  .dates-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.4rem;
  }

  .duration-quick-pills {
    display: flex;
    gap: 0.35rem;
  }

  .pill-preset {
    background: var(--border-subtle);
    border: 1px solid transparent;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text-dim);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s;
  }
  .pill-preset:hover {
    color: var(--text-main);
    border-color: var(--border-hover);
  }
  .pill-preset.active {
    background: rgba(16, 185, 129, 0.15);
    border-color: var(--accent-emerald);
    color: var(--accent-emerald-light);
  }

  .input-sub-label {
    display: block;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
    font-weight: 600;
  }

  /* Join Modal */
  .modal-join {
    max-width: 440px;
  }

  .code-input-wrapper {
    margin-top: 0.25rem;
  }

  .code-input {
    font-family: var(--font-mono, monospace);
    font-size: 1.35rem;
    font-weight: 800;
    text-align: center;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }

  .field-hint {
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-top: 0.35rem;
    text-align: center;
  }

  .field-hint code {
    background: var(--border-subtle);
    padding: 0.1rem 0.3rem;
    border-radius: 4px;
    font-weight: 700;
  }

  .leaderboard-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1.25rem;
  }

  .btn-outline {
    background: transparent;
    border: 1px solid var(--border-hover);
    color: var(--text-muted);
  }
  .btn-outline:hover {
    border-color: var(--accent-rose);
    color: var(--accent-rose);
  }

  .btn-danger {
    background: rgba(225, 29, 72, 0.15);
    border: 1px solid rgba(225, 29, 72, 0.3);
    color: var(--accent-rose);
    border-radius: var(--radius-sm);
    padding: 0.4rem 0.85rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-danger:hover {
    background: var(--accent-rose);
    color: #ffffff;
  }

  .spinner-small {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 640px) {
    .style-selector-grid {
      grid-template-columns: 1fr;
    }
    .form-row {
      grid-template-columns: 1fr;
    }
    .modal-footer {
      flex-direction: column-reverse;
      gap: 0.6rem;
    }
    .modal-footer .btn {
      width: 100%;
      justify-content: center;
    }
    .leaderboard-row {
      grid-template-columns: 32px 1fr;
      row-gap: 0.75rem;
    }
    .progress-column {
      grid-column: 1 / -1;
    }
  }
</style>
