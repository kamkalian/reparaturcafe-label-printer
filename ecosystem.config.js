module.exports = {
  apps: [
    {
      name: "label-printer",
      script: "print_qrcode.py",
      interpreter: "python3",
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true,
      watch: false,
      env_file: ".env",
    },
  ],
};
