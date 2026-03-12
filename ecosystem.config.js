module.exports = {
  apps: [{
    name: "COI-Management-Matching-Engine",
    script: "venv/Scripts/uvicorn.exe",
    args: "app.main:app --host 0.0.0.0 --port 8001",
    cwd: "./backend",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: "production",
    }
  }]
};
