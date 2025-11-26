## 部署指引（Nginx / 宝塔）

前端为单页应用，所有非真实文件的路径都需要回退到 `index.html`。请在 Nginx 站点配置或宝塔“伪静态”里添加：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

建议完整配置（含 HTTPS）示例：

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name example.com;
    root /www/wwwroot/hyperliquid-pinfen/frontend/dist;

    ssl_certificate    /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> **提示**：在宝塔前端项目中，可在“伪静态”直接填入 `try_files $uri $uri/ /index.html;`，这样刷新 `/wallets/xxx` 时不会出现 404。

## 后端服务

1. 创建虚拟环境并安装依赖：`pip install -r requirements.txt`
2. 运行：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. 启动 RQ worker：`rq worker wallet-processing`
4. 若启用 APScheduler，确保进程常驻（可使用 systemd/supervisor）。

## SMTP 与其他配置

- 通过 `.env` 或系统环境变量设置 `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD`，即可在后台配置模板和订阅后发送邮件。
- `VITE_API_BASE_URL` 应指向后端 `/api` 前缀，部署前记得修改 `frontend/.env.production`。
