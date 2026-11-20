// Start the existing React app and FastAPI chatbot from one terminal.
// No additional npm dependencies are required.
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const root = path.resolve(__dirname, '..');
const backendOnly = process.argv.includes('--backend-only');
const windows = process.platform === 'win32';
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
start('FastAPI :8000', python, ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', '8000'], {
  USE_OLLAMA: process.env.USE_OLLAMA || '1',
  OLLAMA_MODEL: process.env.OLLAMA_MODEL || 'llama3:latest',
  OLLAMA_TIMEOUT_SECONDS: process.env.OLLAMA_TIMEOUT_SECONDS || '8',
  OLLAMA_RETRY_COOLDOWN_SECONDS: process.env.OLLAMA_RETRY_COOLDOWN_SECONDS || '30',
  OLLAMA_FOR_SUMMARIES: process.env.OLLAMA_FOR_SUMMARIES || '0',
});

console.log('\nOpen http://localhost:3000 (FastAPI at http://localhost:8000).');
console.log('Press Ctrl+C to stop the local servers. Ollama must be installed and running separately.\n');
