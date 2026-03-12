module.exports = {
  apps: [{
    name: "coi-backend",
    script: "backend/venv/Scripts/uvicorn.exe",
    args: "backend.main:app --host 0.0.0.0 --port 8001",
    cwd: ".",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: "production",
    }
  }]
};
