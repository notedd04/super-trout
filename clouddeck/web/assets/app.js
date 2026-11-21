(() => {
  'use strict';

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const state = {
    bootstrap: null,
    authenticated: false,
    activeScreen: 'home',
    viewerOpen: false,
    streamLoaded: false,
    inputQueue: Promise.resolve(),
    touchKeys: new Set(),
    gamepadKeys: new Set(),
    lastSentKeys: '',
    inputHeartbeatTimer: null,
    gamepadTimer: null,
    metricsTimer: null,
    toastTimer: null,
    installPrompt: null,
    controlsVisible: true,
    touchpad: { pointerId: null, lastX: 0, lastY: 0, dx: 0, dy: 0, timer: null },
    settings: {
      theme: localStorage.getItem('clouddeck-theme') || 'dark',
      controls: localStorage.getItem('clouddeck-controls') !== 'false',
      haptics: localStorage.getItem('clouddeck-haptics') === 'true'
    }
  };

  function cookie(name) {
    const prefix = `${name}=`;
    const item = document.cookie.split(';').map(value => value.trim()).find(value => value.startsWith(prefix));
    return item ? decodeURIComponent(item.slice(prefix.length)) : '';
  }

  function showToast(message) {
    const node = $('#toast');
    if (!node) return;
    node.textContent = message;
    node.classList.add('show');
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => node.classList.remove('show'), 2500);
  }

  async function request(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = Object.assign({ 'Accept': 'application/json' }, options.headers || {});
    if (options.body && typeof options.body !== 'string') {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }
    if (method !== 'GET' && method !== 'HEAD') {
      const csrf = cookie('clouddeck_csrf');
      if (csrf) headers['X-CSRF-Token'] = csrf;
    }
    const response = await fetch(path, Object.assign({}, options, {
      method,
      headers,
      credentials: 'same-origin',
      cache: 'no-store'
    }));
    let payload = {};
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      payload = await response.json().catch(() => ({}));
    }
    if (response.status === 401 && path !== '/api/v1/auth/login' && path !== '/api/v1/auth/status') {
      lockApp();
      throw new Error('Your CloudDeck session expired. Sign in again.');
    }
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed (${response.status}).`);
    }
    return payload;
  }

  function applyTheme(theme) {
    const normalized = theme === 'light' ? 'light' : 'dark';
    state.settings.theme = normalized;
    document.documentElement.dataset.theme = normalized;
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.content = normalized === 'dark' ? '#101112' : '#f2f2f0';
    localStorage.setItem('clouddeck-theme', normalized);
    $$('[data-theme-choice]').forEach(button => button.classList.toggle('active', button.dataset.themeChoice === normalized));
  }

  function lockApp() {
    state.authenticated = false;
    state.bootstrap = null;
    closeViewer(false);
    $('#app').hidden = true;
    $('#login').hidden = false;
    $('#boot').hidden = true;
    $('#access-key').value = '';
    $('#access-key').focus({ preventScroll: true });
    stopPolling();
  }

  function unlockApp() {
    $('#login').hidden = true;
    $('#app').hidden = false;
    $('#boot').hidden = true;
    state.authenticated = true;
    applyTheme(state.settings.theme);
    renderSettings();
  }

  function renderSettings() {
    $('#haptics-setting').checked = state.settings.haptics;
    $('#controls-setting').checked = state.settings.controls;
    $('#gamepad-support').textContent = navigator.getGamepads ? 'Compatible physical Bluetooth or USB controllers can be mapped to keyboard input.' : 'This browser does not expose the Gamepad API.';
    applyTheme(state.settings.theme);
    $('#gamepad-status').textContent = navigator.getGamepads ? 'READY TO DETECT' : 'UNAVAILABLE';
  }

  function renderBootstrap(data) {
    state.bootstrap = data;
    const session = data.session;
    const running = Boolean(session.running);
    const profile = session.profile || { name: 'Balanced', resolution: '1024x576' };
    const statusText = running ? 'ONLINE' : 'OFFLINE';

    $('#workspace-name').textContent = data.workspace.name || 'CODESPACE';
    $('#workspace-name-full').textContent = data.workspace.name || 'Codespace';
    $('#workspace-eyebrow').textContent = data.workspace.repository || 'YOUR CLOUD ENVIRONMENT';
    $('#connection-label').textContent = 'CONTROL PLANE ONLINE';
    $('#connection-pill').classList.add('online');
    $('#desktop-state').classList.toggle('online', running);
    $('#desktop-state').innerHTML = `<span class="status-dot"></span> ${statusText}`;
    $('#hero-description').textContent = running
      ? 'Your private Linux desktop is active. Open the stream to take control.'
      : 'Start a private Linux session and bring your workspace onto this device.';
    $('#start-session').disabled = running;
    $('#start-session').innerHTML = running ? '<span>Session running</span><span>✓</span>' : '<span class="button-icon">▶</span><span>Start session</span>';
    $('#open-viewer').disabled = !running;
    $('#workspace-start').disabled = running;
    $('#workspace-stop').disabled = !running;
    $('#workspace-panel-state').textContent = statusText;
    $('#workspace-panel-state').classList.toggle('online', running);
    $('#workspace-status').textContent = running ? 'RUNNING' : 'READY';
    $('#workspace-status').classList.toggle('online', running);
    $('#profile-name').textContent = `${profile.name || 'Balanced'} profile`;
    $('#desktop-resolution').textContent = (profile.resolution || '1024x576').replace('x', ' × ');
    $('#workspace-display').textContent = running ? session.display || ':1' : 'Stopped';
    $('#viewer-profile').textContent = `${(profile.name || 'BALANCED').toUpperCase()} · ${(profile.resolution || '1024x576').replace('x', ' × ')}`;
    $('#history-current').textContent = running ? 'Desktop session active' : 'No active desktop';
    $('#history-caption').textContent = running
      ? 'Your remote Linux desktop is running in this Codespace.'
      : 'The control plane can stay online while the desktop is stopped.';
    $('#history-ring').classList.toggle('online', running);
    $('#history-ring-dot').style.background = running ? 'var(--positive)' : '';

    $$('.profile-option').forEach(button => button.classList.toggle('selected', button.dataset.profile === profile.id));
    if (data.metrics) renderMetrics(data.metrics);
    renderEvents(data.events || []);
    $('#stream-placeholder').hidden = running && state.streamLoaded;
    $('#viewer-connection').innerHTML = running ? '<i></i> LIVE SESSION' : '<i></i> SESSION OFFLINE';
    if (running && state.viewerOpen && !state.streamLoaded) loadStream();
  }

  function renderMetrics(metrics) {
    const memory = metrics.memory || {};
    if (typeof memory.used_percent === 'number') {
      $('#memory-value').textContent = `${memory.used_percent}%`;
      $('#memory-bar').style.width = `${Math.max(0, Math.min(100, memory.used_percent))}%`;
      $('#memory-caption').textContent = `${memory.used_mb} MB used of ${memory.total_mb} MB`;
    } else {
      $('#memory-value').textContent = '—';
      $('#memory-caption').textContent = 'Host data unavailable';
    }
    if (typeof metrics.load_1m === 'number') {
      $('#cpu-value').textContent = metrics.load_1m.toFixed(2);
      $('#cpu-bar').style.width = `${Math.max(0, Math.min(100, metrics.load_1m * 30))}%`;
    } else {
      $('#cpu-value').textContent = '—';
      $('#cpu-bar').style.width = '0%';
    }
  }

  function humanEvent(event) {
    const labels = {
      'session.started': ['Session started', '◉'],
      'session.stopped': ['Session stopped', 'Ⅱ'],
      'session.start.failed': ['Session start failed', '!'],
      'profile.changed': ['Performance profile changed', '⌁'],
      'profile.apply.failed': ['Profile update failed', '!'],
      'app.launched': ['Desktop application launched', '↗']
    };
    const match = labels[event.type] || ['CloudDeck event', '·'];
    let detail = '';
    if (event.detail && event.detail.profile) detail = `Profile: ${event.detail.profile.replace('_', ' ')}${event.detail.restarted ? ' · desktop restarted' : ''}`;
    if (event.detail && event.detail.app) detail = `Application: ${event.detail.app}`;
    if (event.detail && event.detail.reason) detail = event.detail.reason;
    if (!detail) detail = event.type.replaceAll('.', ' ');
    const date = new Date(event.created_at);
    const timeText = Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return { title: match[0], symbol: match[1], detail, time: timeText };
  }

  function renderEvents(events) {
    const list = $('#event-list');
    if (!events.length) {
      list.innerHTML = '<div class="empty-state"><span>◷</span><b>No activity yet</b><small>Your session events will appear here.</small></div>';
      return;
    }
    list.innerHTML = events.map(event => {
      const item = humanEvent(event);
      const safe = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
      return `<article class="event-item"><span class="event-marker">${safe(item.symbol)}</span><div class="event-copy"><b>${safe(item.title)}</b><small>${safe(item.detail)}</small></div><span class="event-time">${safe(item.time)}</span></article>`;
    }).join('');
  }

  async function refreshBootstrap() {
    const data = await request('/api/v1/bootstrap');
    renderBootstrap(data);
    return data;
  }

  async function refreshMetrics() {
    const metrics = await request('/api/v1/metrics');
    renderMetrics(metrics);
  }

  async function refreshEvents() {
    const events = await request('/api/v1/events');
    renderEvents(events);
  }

  function startPolling() {
    stopPolling();
    state.metricsTimer = window.setInterval(() => {
      if (document.hidden || !state.authenticated) return;
      refreshMetrics().catch(() => {});
    }, 15000);
  }

  function stopPolling() {
    if (state.metricsTimer) window.clearInterval(state.metricsTimer);
    state.metricsTimer = null;
    stopGamepadPolling();
  }

  function navigate(screen) {
    const target = $(`#screen-${screen}`);
    if (!target) return;
    state.activeScreen = screen;
    $$('.screen-view').forEach(node => node.classList.toggle('active', node === target));
    $$('.nav-item').forEach(node => node.classList.toggle('active', node.dataset.nav === screen));
    if (screen === 'workspace') refreshMetrics().catch(() => {});
    if (screen === 'build') refreshBuild().catch(() => {});
    if (screen === 'sessions') refreshEvents().catch(() => {});
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function vibrate() {
    if (state.settings.haptics && navigator.vibrate) navigator.vibrate(12);
  }

  async function startSession() {
    const buttons = [$('#start-session'), $('#workspace-start')];
    buttons.forEach(button => button.disabled = true);
    buttons.forEach(button => button.dataset.previousText = button.textContent);
    $('#start-session').textContent = 'Starting desktop…';
    try {
      const result = await request('/api/v1/session/start', { method: 'POST' });
      renderBootstrap(result.bootstrap);
      showToast(result.session.already_running ? 'Desktop session is already running.' : 'Your Linux desktop is ready.');
      vibrate();
    } catch (error) {
      showToast(error.message);
      await refreshBootstrap().catch(() => {});
    } finally {
      buttons.forEach(button => { delete button.dataset.previousText; });
    }
  }

  async function stopSession() {
    if (!window.confirm('Stop the remote desktop? Any running desktop apps will close.')) return;
    try {
      await releaseAllInput();
      await request('/api/v1/session/stop', { method: 'POST' });
      closeViewer(false);
      await refreshBootstrap();
      showToast('Desktop session stopped.');
    } catch (error) {
      showToast(error.message);
    }
  }

  async function changeProfile(profileId) {
    const selected = state.bootstrap && state.bootstrap.session.profile.id;
    if (profileId === selected) return;
    const running = Boolean(state.bootstrap && state.bootstrap.session.running);
    if (running && !window.confirm('Applying a new display profile will restart the desktop session and close its open apps. Continue?')) return;
    try {
      const result = await request('/api/v1/profile', { method: 'POST', body: { profile_id: profileId } });
      await refreshBootstrap();
      if (running) {
        state.streamLoaded = false;
        if (state.viewerOpen) loadStream();
      }
      showToast(`Profile changed to ${result.profile.name}.`);
    } catch (error) {
      showToast(error.message);
    }
  }

  async function launchApp(appId) {
    try {
      await request('/api/v1/apps/launch', { method: 'POST', body: { app_id: appId } });
      showToast(`${appId} opened in the remote desktop.`);
      vibrate();
    } catch (error) {
      showToast(error.message);
    }
  }

  function loadStream() {
    if (!state.bootstrap || !state.bootstrap.session.running) return;
    const frame = $('#desktop-frame');
    const streamPath = state.bootstrap.session.stream_path;
    $('#stream-placeholder').hidden = false;
    state.streamLoaded = false;
    frame.onload = () => {
      state.streamLoaded = true;
      $('#stream-placeholder').hidden = true;
    };
    frame.src = `${streamPath}&t=${Date.now()}`;
    // A loaded vnc.html may still show its own authentication or connection panel.
    window.setTimeout(() => {
      if (state.viewerOpen && frame.src) {
        state.streamLoaded = true;
        $('#stream-placeholder').hidden = true;
      }
    }, 3200);
  }

  async function openViewer() {
    if (!state.bootstrap || !state.bootstrap.session.running) {
      showToast('Start the desktop session first.');
      return;
    }
    state.viewerOpen = true;
    $('#viewer').hidden = false;
    document.body.style.overflow = 'hidden';
    const profileId = state.bootstrap.session.profile && state.bootstrap.session.profile.id;
    if (profileId !== 'portrait' && screen.orientation && screen.orientation.lock) {
      screen.orientation.lock('landscape').catch(() => {});
    }
    try {
      if (document.documentElement.requestFullscreen && !document.fullscreenElement) {
        await document.documentElement.requestFullscreen().catch(() => {});
      }
    } catch (_) {}
    loadStream();
    if (state.settings.controls) $('#game-controls').classList.remove('hidden-controls');
    else $('#game-controls').classList.add('hidden-controls');
    startGamepadPolling();
  }

  async function closeViewer(restore = true) {
    if (!state.viewerOpen) return;
    state.viewerOpen = false;
    await releaseAllInput().catch(() => {});
    stopGamepadPolling();
    $('#desktop-frame').src = 'about:blank';
    $('#viewer').hidden = true;
    document.body.style.overflow = '';
    state.streamLoaded = false;
    try {
      if (screen.orientation && screen.orientation.unlock) screen.orientation.unlock();
      if (document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen();
    } catch (_) {}
    if (restore) navigate(state.activeScreen || 'home');
  }

  function mergedKeys() {
    return Array.from(new Set([...state.touchKeys, ...state.gamepadKeys])).sort();
  }

  function syncInputHeartbeat(keys) {
    const needsLease = state.viewerOpen && keys.length > 0;
    if (needsLease && !state.inputHeartbeatTimer) {
      state.inputHeartbeatTimer = window.setInterval(() => {
        if (!state.viewerOpen || mergedKeys().length === 0) {
          syncInputHeartbeat([]);
          return;
        }
        request('/api/v1/input/heartbeat', { method: 'POST' }).then(result => {
          if (!result.active && mergedKeys().length > 0) {
            state.lastSentKeys = '';
            sendInputState();
          }
        }).catch(() => {});
      }, 300);
    } else if (!needsLease && state.inputHeartbeatTimer) {
      window.clearInterval(state.inputHeartbeatTimer);
      state.inputHeartbeatTimer = null;
    }
  }

  function sendInputState() {
    const keys = mergedKeys();
    syncInputHeartbeat(keys);
    const fingerprint = keys.join(',');
    if (fingerprint === state.lastSentKeys) return;
    state.lastSentKeys = fingerprint;
    state.inputQueue = state.inputQueue.then(() => request('/api/v1/input/state', {
      method: 'POST',
      body: { keys }
    })).catch(error => {
      if (state.viewerOpen) showToast(error.message);
    });
  }

  async function releaseAllInput() {
    state.touchKeys.clear();
    state.gamepadKeys.clear();
    syncInputHeartbeat([]);
    state.lastSentKeys = '';
    $$('.game-controls [data-key]').forEach(button => button.classList.remove('pressed'));
    if (state.authenticated) {
      state.inputQueue = state.inputQueue.then(() => request('/api/v1/input/state', {
        method: 'POST', body: { keys: [] }
      })).catch(() => {});
      await state.inputQueue;
    }
  }

  function activateTouchKey(button, pressed) {
    const key = button.dataset.key;
    if (!key) return;
    if (pressed) state.touchKeys.add(key);
    else state.touchKeys.delete(key);
    button.classList.toggle('pressed', pressed);
    sendInputState();
    if (pressed) vibrate();
  }

  function gamepadSnapshot() {
    if (!navigator.getGamepads) return new Set();
    const pads = navigator.getGamepads();
    let pad = null;
    for (let index = 0; index < pads.length; index += 1) {
      if (pads[index] && pads[index].connected) { pad = pads[index]; break; }
    }
    if (!pad) {
      $('#gamepad-status').textContent = 'NOT CONNECTED';
      return new Set();
    }
    $('#gamepad-status').textContent = 'CONNECTED';
    const keys = new Set();
    const x = pad.axes && typeof pad.axes[0] === 'number' ? pad.axes[0] : 0;
    const y = pad.axes && typeof pad.axes[1] === 'number' ? pad.axes[1] : 0;
    if (x < -0.35) keys.add('a');
    if (x > 0.35) keys.add('d');
    if (y < -0.35) keys.add('w');
    if (y > 0.35) keys.add('s');
    const pressed = (index) => Boolean(pad.buttons && pad.buttons[index] && pad.buttons[index].pressed);
    if (pressed(0)) keys.add('space');
    if (pressed(1)) keys.add('e');
    if (pressed(2)) keys.add('q');
    if (pressed(3)) keys.add('shift');
    if (pressed(4)) keys.add('ctrl');
    if (pressed(5)) keys.add('alt');
    if (pressed(8)) keys.add('escape');
    if (pressed(9)) keys.add('enter');
    if (pressed(12)) keys.add('up');
    if (pressed(13)) keys.add('down');
    if (pressed(14)) keys.add('left');
    if (pressed(15)) keys.add('right');
    return keys;
  }

  function pollGamepad() {
    if (!state.viewerOpen) return;
    const next = gamepadSnapshot();
    const fingerprint = Array.from(next).sort().join(',');
    const current = Array.from(state.gamepadKeys).sort().join(',');
    if (fingerprint !== current) {
      state.gamepadKeys = next;
      sendInputState();
    }
  }

  function startGamepadPolling() {
    stopGamepadPolling();
    if (!navigator.getGamepads) return;
    state.gamepadTimer = window.setInterval(pollGamepad, 50);
    pollGamepad();
  }

  function stopGamepadPolling() {
    if (state.gamepadTimer) window.clearInterval(state.gamepadTimer);
    state.gamepadTimer = null;
    state.gamepadKeys.clear();
  }

  async function initialize() {
    applyTheme(state.settings.theme);
    try {
      const status = await request('/api/v1/auth/status');
      if (!status.authenticated) {
        lockApp();
        return;
      }
      unlockApp();
      await refreshBootstrap();
      startPolling();
    } catch (error) {
      lockApp();
      showToast(error.message);
    }
  }

  async function refreshBuild() {
    const [files, ai] = await Promise.all([
      request('/api/v1/developer/files'),
      request('/api/v1/ai/status'),
    ]);
    $('#ai-base-url').value = ai.base_url || 'https://openrouter.ai/api/v1';
    $('#ai-model').value = ai.model || '';
    $('#ai-output').textContent = ai.configured
      ? `Configured model: ${ai.model}`
      : 'AI provider not configured.';
    if (files.files && files.files.length && !$('#developer-name').dataset.loaded) {
      const latest = files.files[0].name;
      $('#developer-name').value = latest;
      const file = await request(`/api/v1/developer/files/${encodeURIComponent(latest)}`);
      $('#developer-code').value = file.code;
      $('#developer-name').dataset.loaded = 'true';
    }
  }

  async function saveDeveloperFile() {
    const name = $('#developer-name').value.trim();
    const code = $('#developer-code').value;
    await request('/api/v1/developer/files', { method: 'POST', body: { name, code } });
    showToast('Python file saved.');
  }

  async function runDeveloperFile() {
    await saveDeveloperFile();
    const name = $('#developer-name').value.trim();
    const result = await request('/api/v1/developer/run', { method: 'POST', body: { name, timeout_seconds: 10 } });
    const output = result.timed_out
      ? `Execution timed out.\n${result.stderr}`
      : `Exit code: ${result.exit_code}\n${result.stdout}${result.stderr}`;
    $('#developer-output').textContent = output || '(No output)';
  }

  // Login
  $('#login-form').addEventListener('submit', async event => {
    event.preventDefault();
    const input = $('#access-key');
    const errorNode = $('#login-error');
    const button = $('button[type="submit"]', event.currentTarget);
    button.disabled = true;
    errorNode.textContent = '';
    try {
      await request('/api/v1/auth/login', { method: 'POST', body: { password: input.value } });
      input.value = '';
      unlockApp();
      await refreshBootstrap();
      startPolling();
      showToast('CloudDeck unlocked.');
    } catch (error) {
      errorNode.textContent = error.message;
      input.select();
    } finally {
      button.disabled = false;
    }
  });

  $('#reveal-key').addEventListener('click', () => {
    const input = $('#access-key');
    input.type = input.type === 'password' ? 'text' : 'password';
    $('#reveal-key').setAttribute('aria-label', input.type === 'password' ? 'Show access key' : 'Hide access key');
  });

  $('#developer-save').addEventListener('click', () => saveDeveloperFile().catch(error => showToast(error.message)));
  $('#developer-run').addEventListener('click', () => runDeveloperFile().catch(error => {
    $('#developer-output').textContent = error.message;
  }));
  $('#ai-save-config').addEventListener('click', async () => {
    try {
      await request('/api/v1/ai/configure', { method: 'POST', body: { base_url: $('#ai-base-url').value.trim(), model: $('#ai-model').value.trim() } });
      $('#ai-output').textContent = 'AI provider configuration saved.';
      showToast('AI provider saved.');
    } catch (error) { $('#ai-output').textContent = error.message; }
  });
  $('#ai-save-key').addEventListener('click', async () => {
    try {
      await request('/api/v1/ai/key', { method: 'POST', body: { api_key: $('#ai-key').value } });
      $('#ai-key').value = '';
      $('#ai-output').textContent = 'AI API key stored privately.';
      showToast('AI key saved privately.');
    } catch (error) { $('#ai-output').textContent = error.message; }
  });
  $$('[data-automation]').forEach(button => button.addEventListener('click', async () => {
    const recipe = button.dataset.automation;
    $('#automation-output').textContent = `Running ${recipe}...`;
    try {
      const result = await request('/api/v1/automation/run', { method: 'POST', body: { recipe } });
      $('#automation-output').textContent = JSON.stringify(result, null, 2);
      await refreshBootstrap();
      showToast('Automation recipe completed.');
    } catch (error) { $('#automation-output').textContent = error.message; }
  }));

  $('#ai-send').addEventListener('click', async () => {
    const prompt = $('#ai-chat').value.trim();
    if (!prompt) return;
    $('#ai-output').textContent = 'Waiting for model...';
    try {
      const result = await request('/api/v1/ai/chat', { method: 'POST', body: { messages: [{ role: 'user', content: prompt }], max_tokens: 1024 } });
      $('#ai-output').textContent = result.content || '(No response)';
    } catch (error) { $('#ai-output').textContent = error.message; }
  });

  // Primary navigation and actions
  $$('[data-nav]').forEach(button => button.addEventListener('click', () => navigate(button.dataset.nav)));
  $('#profile-button').addEventListener('click', () => navigate('settings'));
  $('#start-session').addEventListener('click', startSession);
  $('#workspace-start').addEventListener('click', startSession);
  $('#workspace-stop').addEventListener('click', stopSession);
  $('#open-viewer').addEventListener('click', openViewer);
  $$('[data-launch]').forEach(button => button.addEventListener('click', () => launchApp(button.dataset.launch)));
  $$('.profile-option').forEach(button => button.addEventListener('click', () => changeProfile(button.dataset.profile)));
  $('#refresh-metrics').addEventListener('click', () => refreshMetrics().then(() => showToast('Host metrics refreshed.')).catch(error => showToast(error.message)));
  $('#refresh-events').addEventListener('click', () => refreshEvents().then(() => showToast('Activity refreshed.')).catch(error => showToast(error.message)));
  $('#logout-button').addEventListener('click', async () => {
    try { await request('/api/v1/auth/logout', { method: 'POST' }); } catch (_) {}
    lockApp();
    showToast('Signed out of CloudDeck.');
  });

  // Viewer controls
  $('#viewer-back').addEventListener('click', () => closeViewer());
  $('#viewer-controls-toggle').addEventListener('click', () => {
    state.controlsVisible = !state.controlsVisible;
    $('#game-controls').classList.toggle('hidden-controls', !state.controlsVisible);
    $('#game-controls').classList.toggle('visible-controls', state.controlsVisible);
  });
  $('#viewer-fullscreen').addEventListener('click', async () => {
    try {
      if (document.documentElement.requestFullscreen && !document.fullscreenElement) await document.documentElement.requestFullscreen();
      else if (document.exitFullscreen && document.fullscreenElement) await document.exitFullscreen();
    } catch (_) { showToast('Fullscreen is not available in this browser.'); }
  });
  $('#release-input').addEventListener('click', releaseAllInput);
  $('#viewer-keyboard').addEventListener('click', () => {
    // Focusing a hidden text field is unreliable on Android; the noVNC toolbar owns keyboard entry.
    const frameWindow = $('#desktop-frame').contentWindow;
    if (frameWindow) frameWindow.focus();
    showToast('Use the noVNC toolbar keyboard inside the desktop.');
  });
  function flushTouchpad() {
    const pad = state.touchpad;
    if (!pad.dx && !pad.dy) return;
    const body = { dx: Math.round(pad.dx), dy: Math.round(pad.dy) };
    pad.dx = 0;
    pad.dy = 0;
    request('/api/v1/input/pointer', { method: 'POST', body }).catch(() => {});
  }

  const touchpad = $('#touchpad');
  touchpad.addEventListener('pointerdown', event => {
    event.preventDefault();
    touchpad.setPointerCapture(event.pointerId);
    state.touchpad.pointerId = event.pointerId;
    state.touchpad.lastX = event.clientX;
    state.touchpad.lastY = event.clientY;
  });
  touchpad.addEventListener('pointermove', event => {
    if (state.touchpad.pointerId !== event.pointerId) return;
    event.preventEvent = true;
    event.preventDefault();
    const pad = state.touchpad;
    pad.dx += (event.clientX - pad.lastX) * 2;
    pad.dy += (event.clientY - pad.lastY) * 2;
    pad.lastX = event.clientX;
    pad.lastY = event.clientY;
    if (!pad.timer) pad.timer = window.setTimeout(() => { pad.timer = null; flushTouchpad(); }, 24);
  });
  const stopTouchpad = event => {
    if (state.touchpad.pointerId !== event.pointerId) return;
    event.preventDefault();
    flushTouchpad();
    state.touchpad.pointerId = null;
  };
  touchpad.addEventListener('pointerup', stopTouchpad);
  touchpad.addEventListener('pointercancel', stopTouchpad);
  touchpad.addEventListener('wheel', event => {
    event.preventDefault();
    const scroll = Math.max(-20, Math.min(20, Math.round(event.deltaY / 20)));
    request('/api/v1/input/pointer', { method: 'POST', body: { dx: 0, dy: 0, scroll_y: scroll } }).catch(() => {});
  }, { passive: false });
  $$('[data-pointer-button]').forEach(button => button.addEventListener('pointerdown', event => {
    event.preventDefault();
    request('/api/v1/input/pointer', { method: 'POST', body: { dx: 0, dy: 0, button: button.dataset.pointerButton } }).catch(() => {});
  }));

  $$('.game-controls [data-key]').forEach(button => {
    button.addEventListener('pointerdown', event => {
      event.preventDefault();
      button.setPointerCapture(event.pointerId);
      activateTouchKey(button, true);
    });
    const release = event => {
      event.preventDefault();
      activateTouchKey(button, false);
    };
    button.addEventListener('pointerup', release);
    button.addEventListener('pointercancel', release);
    button.addEventListener('lostpointercapture', () => activateTouchKey(button, false));
    button.addEventListener('contextmenu', event => event.preventDefault());
  });

  // Local preferences
  $$('[data-theme-choice]').forEach(button => button.addEventListener('click', () => applyTheme(button.dataset.themeChoice)));
  $('#haptics-setting').addEventListener('change', event => {
    state.settings.haptics = event.target.checked;
    localStorage.setItem('clouddeck-haptics', String(state.settings.haptics));
  });
  $('#controls-setting').addEventListener('change', event => {
    state.settings.controls = event.target.checked;
    localStorage.setItem('clouddeck-controls', String(state.settings.controls));
    $('#game-controls').classList.toggle('hidden-controls', !state.settings.controls);
    if (!state.settings.controls) releaseAllInput();
  });

  window.addEventListener('gamepadconnected', () => {
    $('#gamepad-status').textContent = 'CONNECTED';
    showToast('Controller detected. Open a desktop session to use it.');
  });
  window.addEventListener('gamepaddisconnected', () => {
    state.gamepadKeys.clear();
    sendInputState();
    $('#gamepad-status').textContent = 'NOT CONNECTED';
  });
  window.addEventListener('blur', () => {
    if (state.viewerOpen) releaseAllInput();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && state.viewerOpen) releaseAllInput();
    else if (!document.hidden && state.authenticated) refreshBootstrap().catch(() => {});
  });
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    state.installPrompt = event;
  });
  window.addEventListener('pagehide', () => {
    if (state.viewerOpen) {
      const body = JSON.stringify({ keys: [] });
      try { navigator.sendBeacon('/api/v1/input/state', new Blob([body], { type: 'application/json' })); } catch (_) {}
    }
  });

  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {}));
  }

  initialize();
})();
