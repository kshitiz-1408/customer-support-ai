This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## ⚙️ Production Configuration & Environment Variables

The frontend service requires the following environment variables:

- `NEXT_PUBLIC_API_URL`: The absolute base URL of the FastAPI backend service (e.g. `http://localhost:8000`).
  - **Development Mode**: Defaults to `http://localhost:8000` if not set.
  - **Production Mode**: **Must be explicitly configured**. Outgoing requests will throw an error at request-time if this variable is missing in production.

To set local variables, create a `.env` or `.env.local` file under this directory:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🛠️ Build and Compilation Hardening

### 1. Code Linting
Enforce style bounds and typescript imports rules:
```bash
npm run lint
```

### 2. Optimized Production Compile
Build optimized static and dynamic server-rendered assets:
```bash
npm run build
```

### 3. Local Node Verification Suite
Run mock-based client normalizer and cancellation unit tests:
```bash
node tests/test_suite.js
```

---

## 🐳 Docker Deployment

The frontend container is configured for multi-stage optimized builds:

- **Build Injections**: Since Next.js embeds `NEXT_PUBLIC_` environment variables into client-side JS bundles during compile-time, the backend API URL must be supplied as a `--build-arg`:
  ```bash
  docker compose build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000
  ```
- **Runner Boundaries**: The final image runs under a restricted non-root user (`nextjs`) inside an Alpine Node container.
- **Compose Orchestration**: Binds port `3000` on the host and communicates with the backend container using standard docker networks.

