// Start the existing React app and FastAPI chatbot from one terminal.
// No additional npm dependencies are required.
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const root = path.resolve(__dirname, '..');
const backendOnly = process.argv.includes('--backend-only');
const windows = process.platform === 'win32';

// Backend-only local secrets. Never pass these to the React development server.
// An existing file is read on each "npm start", so no terminal exports are needed.
function loadLocalBackendSecrets() {
  const file = path.join(root, 'config', 'secrets.local.json');
  if (!fs.existsSync(file)) return {};

  let parsed;
  try {
    // PowerShell on some Windows versions writes a UTF-8 BOM.
    parsed = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  } catch (_) {
    console.error('[Local secrets] config/secrets.local.json is not valid JSON.');
    process.exit(1);
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    console.error('[Local secrets] Expected a JSON object of environment variable names and strings.');
    process.exit(1);
  }

  const secrets = {};
  for (const [name, rawValue] of Object.entries(parsed)) {
    if (!/^[A-Z_][A-Z0-9_]*$/.test(name) || typeof rawValue !== 'string') {
      console.error('[Local secrets] All names must be environment variable names, with string values.');
      process.exit(1);
    }
    // Empty values should not mask genuine server environment variables.
    if (rawValue.trim()) secrets[name] = rawValue.trim();
  }
  console.log('[Local secrets] Backend configuration loaded from config/secrets.local.json.');
  return secrets;
}

const localBackendSecrets = loadLocalBackendSecrets();
const python = process.env.PORTFOLIO_PYTHON || path.join(
  root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python'
);

if (!fs.existsSync(python)) {
  console.error('\n[Setup required] Python virtual environment not found:');
  console.error(python);
  console.error('From the portfolio folder run:');
  console.error('  python -m venv .venv');
  console.error(windows
    ? '  .\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt'
    : '  ./.venv/bin/python -m pip install -r backend/requirements.txt');
  process.exit(1);
}

let reactScript;
if (!backendOnly) {
  try {
    reactScript = require.resolve('react-scripts/bin/react-scripts.js', { paths: [root] });
  } catch (_) {
    console.error('[Setup required] React dependencies are missing. Run npm install.');
    process.exit(1);
  }
}

const processes = [];
let stopping = false;

function stopAll(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of processes) {
    if (!child.pid || child.exitCode !== null) continue;
    if (windows) {
      // Terminate uvicorn's reload child as well as the parent process.
      const killer = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
      killer.on('error', () => {});
    } else {
      try { process.kill(-child.pid, 'SIGTERM'); }
      catch (_) { try { child.kill('SIGTERM'); } catch (_) {} }
    }
  }
  // Give child processes a moment to release their ports before exiting.
  setTimeout(() => process.exit(code), 900).unref();
}

function start(name, command, args, extraEnv = {}) {
  console.log(`[${name}] Starting...`);
  const child = spawn(command, args, {
    cwd: root,
    stdio: 'inherit',
    detached: !windows,
    env: { ...process.env, ...extraEnv },
  });
  processes.push(child);
  child.on('error', (error) => {
    console.error(`[${name}] Cannot start: ${error.message}`);
    stopAll(1);
  });
  child.on('exit', (code, signal) => {
    if (!stopping) {
      console.error(`[${name}] Stopped (${signal || 'exit code ' + code}).`);
      stopAll(code || 1);
    }
  });
}

process.on('SIGINT', () => stopAll(0));
process.on('SIGTERM', () => stopAll(0));

if (!backendOnly) {
  start('React :3000', process.execPath, [reactScript, 'start']);
}
// Enable both knowledge features by default during local development.
// Setting either variable to '0' still disables it for troubleshooting.
const semanticEnabled = process.env.ENABLE_SEMANTIC ?? '1';
const githubSyncEnabled = process.env.GITHUB_AUTO_SYNC ?? '1';
start('FastAPI :8000', python, ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', '8000'], {
  GROQ_MODEL: process.env.GROQ_MODEL || 'openai/gpt-oss-20b',
  ENABLE_SEMANTIC: semanticEnabled,
  GITHUB_AUTO_SYNC: githubSyncEnabled,
  ...localBackendSecrets,
});

console.log('Knowledge features: semantic=' + semanticEnabled + ', GitHub auto sync=' + githubSyncEnabled + '.');
console.log('\nOpen http://localhost:3000 (FastAPI at http://localhost:8000).');
console.log('Press Ctrl+C to stop the local servers. Local backend secrets load from config/secrets.local.json when present.\n');
