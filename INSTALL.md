# Faster Ask Gulshan AI: local performance patch

This patch only modifies `backend/agent.py` and `scripts/start-dev.js`, and adds a regression test (`backend/tests/test_speed.py`). It does **not** edit your frontend, portfolio content, Git history, or GitHub. It assumes you installed the latest chatbot improvements and one-command launcher ZIPs.

## Apply (PowerShell in your portfolio root)

```powershell
Expand-Archive -LiteralPath "$HOME\Downloads\portfolio-ai-speed-fix.zip" -DestinationPath . -Force
```

Stop the existing `npm start` process with **Ctrl+C** and restart it:

```powershell
npm start
```

## What changed

- Common recruiter questions (work experience, education, general overview, skills, projects) now use immediate verified summaries without waiting for local Ollama. You can restore LLM summaries later by setting `OLLAMA_FOR_SUMMARIES=1`.
- For specific questions requiring LLM phrasing, default timeout is **8 seconds** instead of **45 seconds**. After a timeout, Ollama is skipped for **30 seconds**, so subsequent visitor requests are not repeatedly delayed.
- Requests include less source text and shorter conversation history, and request at most 160 new tokens, improving local inference speed. `keep_alive=10m` reduces repeated model cold loads when Ollama is healthy.
- The assistant **still uses Ollama** for targeted questions when it responds within the timeout. If it doesn't, it gives portfolio excerpts. Lower timeout improves responsiveness but makes model fallback more likely on slow CPUs.

## Optional: faster local model

If your current Llama 3 model is too slow on your hardware, try a smaller model:

```powershell
ollama pull llama3.2:3b
$env:OLLAMA_MODEL="llama3.2:3b"
npm start
```

Your previous `llama3:latest` model remains installed. To use it instead, unset the environment variable or set it explicitly.

Check your Ollama model and hardware placement:

```powershell
ollama list
ollama ps
```

When `ollama ps` reports inference primarily on CPU, generation can be slow. Smaller models may help but can produce lower-quality answers. If you only want immediate verified answers while testing the interface, run:

```powershell
$env:USE_OLLAMA="0"
npm start
```

This is a local development workaround, **not** a cloud-ready AI deployment.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Optional timing test while the backend is running:

```powershell
Measure-Command {
  Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat -Method Post -ContentType application/json -Body '{"question":"Tell me about his work experience"}' | Out-Null
}
```

If model requests still time out, send the output of `ollama ps` and the time taken by a targeted question. That will tell us whether the issue is hardware, model cold startup, or backend configuration.
