# Remy Web Interface Setup Guide

This guide explains how to set up, build, and run the Remy web interface locally, including Docker configuration, development workflow, and production builds.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Initial Docker Build](#initial-docker-build)
  - [Understanding the Build Time](#understanding-the-build-time)
  - [The Snapshot Mechanism](#the-snapshot-mechanism)
  - [Creating a Snapshot](#creating-a-snapshot)
- [Development Workflow](#development-workflow)
  - [Starting the Development Environment](#starting-the-development-environment)
  - [Running the Flask API Server](#running-the-flask-api-server)
  - [Running the Vite Development Server](#running-the-vite-development-server)
  - [Accessing the Interface](#accessing-the-interface)
  - [API Proxying](#api-proxying)
- [Production Build](#production-build)
- [Troubleshooting](#troubleshooting)
  - [Port Conflicts](#port-conflicts)
  - [Mount Issues](#mount-issues)
  - [Node Module Caching Problems](#node-module-caching-problems)
  - [Common Errors](#common-errors)

---

## Quick Start

For developers who want to get started immediately:

```bash
# 1. Navigate to the vite directory
cd vite

# 2. Start the development environment (uses pre-built snapshot)
docker-compose -f dev-docker-compose.yml up -d

# 3. In a separate terminal, start the Flask API server
cd ..
python -m remy.www --cache /path/to/your/notecards

# 4. Access the web interface
# Open http://localhost:3000 in your browser
```

**Note**: The first build will take approximately 85 minutes if no snapshot exists. See [Initial Docker Build](#initial-docker-build) for details.

---

## Prerequisites

Before setting up the Remy web interface, ensure you have:

- **Docker** (version 20.10 or later)
  - Docker Compose (version 1.29 or later)
- **Git** (for cloning the repository)
- **Python 3.12+** (for running the Flask backend locally)
- At least **10 GB of free disk space** (for Docker images and builds)
- **85+ minutes** for the initial Docker build (can be avoided with snapshot)

### System Requirements

- **Memory**: 4 GB minimum, 8 GB recommended for building
- **CPU**: Multi-core processor recommended (build uses parallel compilation)
- **OS**: Linux, macOS, or Windows with WSL2

---

## Architecture Overview

The Remy web interface consists of three main components:

1. **Flask Backend** (`src/remy/www/app.py`)
   - Serves the API endpoints for notecard data
   - Handles notecard parsing and rendering
   - Runs on port 5000 by default

2. **Vue.js Frontend** (`vite/vite/src/`)
   - Modern web interface built with Vue 3 and TypeScript
   - Uses Vite for development and building
   - Runs on port 3000 in development mode

3. **Docker Environment** (`vite/Dockerfile`)
   - Alpine Linux-based container
   - Builds Python 3.12.2 and Node.js 21.6.2 from source using asdf
   - Provides a consistent development and build environment

### Communication Flow

```
Browser → Vite Dev Server (port 3000) → Proxy → Flask API (port 5000)
                                              ↓
                                      Notecard Cache
```

In development, Vite proxies API requests from `/api/*` to the Flask backend running on port 5000.

---

## Initial Docker Build

### Understanding the Build Time

The Docker container builds Python 3.12.2 and Node.js 21.6.2 from source using [asdf](https://asdf-vm.com/) version manager. This approach provides:

- **Full control** over the build process and optimization flags
- **Consistency** across different environments
- **Reproducibility** of the build environment

However, compiling Node.js from source takes approximately **85 minutes** on a typical development machine. This is a one-time cost for each version change.

### The Snapshot Mechanism

To avoid rebuilding the environment every time, Remy uses a **snapshot mechanism** that caches the compiled Python and Node.js interpreters.

The snapshot is a compressed tarball (`root_asdf.tbz2`) that contains:
- Compiled Python 3.12.2 interpreter and packages
- Compiled Node.js 21.6.2 interpreter and npm
- asdf configuration and tool versions

**How it works:**

1. **Without snapshot**: The Dockerfile builds Python and Node.js from scratch (see the commented-out RUN command in the Dockerfile around lines 24-28)
2. **With snapshot**: The Dockerfile extracts the pre-built interpreters from `root_asdf.tbz2` (see the RUN command with bind mount around lines 30-31)

**Note**: Line numbers are approximate and may vary if the Dockerfile is modified.

The snapshot file should be placed in the `vite/` directory and will be bind-mounted during the Docker build.

### Creating a Snapshot

If you need to create a new snapshot (e.g., after updating Python or Node.js versions):

1. **Build the container from scratch** by editing `vite/Dockerfile`:

   Find and uncomment the RUN command that installs Python and Node.js (around lines 24-28):
   ```dockerfile
   RUN . /asdf/asdf.sh \
       && asdf install python 3.12.2 \
       && asdf global python 3.12.2 \
       && ASDF_NODEJS_FORCE_COMPILE=1 asdf install nodejs 21.6.2 \
       && asdf global nodejs 21.6.2
   ```

   Find and comment out the RUN command that extracts the snapshot (around lines 30-31):
   ```dockerfile
   # RUN --mount=type=bind,target=/mnt/build \
   #     cd / && tar -xjvf /mnt/build/root_asdf.tbz2
   ```

2. **Start the container**:

   ```bash
   cd vite
   docker-compose up -d
   ```

   This will take approximately 85 minutes.

3. **Create the snapshot** using the `tar_snapshot.sh` script:

   ```bash
   # Get the container ID
   docker ps | grep remy-vite

   # Run the snapshot script
   ./tar_snapshot.sh <container-id>
   ```

   This creates `root_asdf.tbz2` in the current directory.

4. **Restore the Dockerfile** to use the snapshot (revert your changes from step 1)

5. **Rebuild** to verify the snapshot works:

   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

   This should complete in a few minutes instead of 85 minutes.

---

## Development Workflow

### Starting the Development Environment

The development environment uses `dev-docker-compose.yml`, which provides:
- **Live reload**: Changes to Vue.js files are immediately reflected
- **Bind mounts**: Your local `vite/vite/` directory is mounted into the container
- **Separate node_modules**: Uses a bind-mounted volume to avoid permission issues

**Start the Vite development server:**

```bash
cd vite
docker-compose -f dev-docker-compose.yml up -d
```

Or use the convenience script:

```bash
cd vite
./vite_serve.sh
```

**Check the logs:**

```bash
docker-compose -f dev-docker-compose.yml logs -f remy-vite
```

You should see output indicating that Vite is running on port 3000.

### Running the Flask API Server

The Flask backend serves the API endpoints that the frontend calls to fetch notecard data.

**Start the Flask server:**

```bash
# From the repository root
python -m remy.www --cache /path/to/your/notecards --host 0.0.0.0
```

**Options:**
- `--cache`: (Required) Path to your notecard directory
- `--host`: (Optional) Host to bind to (default: 127.0.0.1, use 0.0.0.0 for Docker access)

**Example:**

```bash
# Using a local notecard directory
python -m remy.www --cache ~/Documents/my_notes --host 0.0.0.0

# Using environment variable
export REMY_CACHE=~/Documents/my_notes
python -m remy.www --host 0.0.0.0
```

The Flask server will start on **port 5000** by default.

**Verify it's running:**

```bash
curl http://localhost:5000/api
```

You should receive a 204 No Content response, indicating the API is running.

### Running the Vite Development Server

If you started the development environment using `dev-docker-compose.yml`, the Vite server is already running inside the Docker container.

**Check the container status:**

```bash
cd vite
docker ps | grep remy-vite
```

**View the Vite logs:**

```bash
docker-compose -f dev-docker-compose.yml logs -f remy-vite
```

Look for output like:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:3000/
➜  Network: http://0.0.0.0:3000/
```

### Accessing the Interface

Once both servers are running:

1. **Open your browser** to http://localhost:3000
2. The Vite dev server will load the Vue.js frontend
3. API calls to `/api/*` will be proxied to Flask on port 5000
4. You can browse and interact with your notecards

**Development features:**
- **Hot Module Replacement (HMR)**: Changes to `.vue`, `.ts`, and `.css` files are instantly reflected
- **Error overlay**: Compilation errors are displayed in the browser
- **Fast refresh**: Component state is preserved across most edits

### API Proxying

The Vite development server is configured to proxy API requests to the Flask backend.

**Configuration** (`vite/vite/vite.config.ts`):

```typescript
server: {
    proxy: {
        '/api': {
            target: 'http://host.docker.internal:5000/api',
            rewrite: (path) => path.replace(/^\/api/, ''),
        },
    },
}
```

**How it works:**

1. Frontend makes request to `http://localhost:3000/api/notecard/my_label`
2. Vite proxy intercepts and forwards to `http://host.docker.internal:5000/api/notecard/my_label`
3. Flask processes the request and returns notecard data
4. Vite forwards the response back to the frontend

**Note**: `host.docker.internal` is a special DNS name that resolves to the host machine from inside a Docker container. This allows the containerized Vite server to access the Flask server running on the host.

**For local development (outside Docker):**

If running Vite outside Docker, update the proxy target to:
```typescript
target: 'http://localhost:5000/api'
```

---

## Production Build

For production deployment, use the standard `docker-compose.yml` which builds the static assets.

### Building the Production Assets

**Option 1: Using Docker Compose**

```bash
cd vite
docker-compose run --rm remy-vite
```

This runs the build inside the container and outputs the compiled assets.

**Option 2: Using the build script**

```bash
cd vite
./vite_build.sh
```

This script:
1. Runs the Docker Compose build
2. Mounts the output directory to `src/remy/www/static/vite`
3. Creates the production build using `vite build`

**Build output:**

The compiled assets are placed in:
- `vite/vite/dist/` (inside container)
- `src/remy/www/static/vite/` (on host, if using vite_build.sh)

### Production Deployment

For production, the Flask app serves the static files directly (no Vite dev server needed).

**Start the Flask app in production mode:**

```bash
# Do not set REMY_VITE_URL in production
unset REMY_VITE_URL

# Start Flask
python -m remy.www --cache /path/to/notecards --host 0.0.0.0
```

The Flask app will serve the Vite-built static files from `src/remy/www/static/vite/`.

**Access the production app:**

Open http://localhost:5000 in your browser (note: port 5000, not 3000).

---

## Troubleshooting

### Port Conflicts

**Problem**: `Error: Port 3000 is already in use` or `Port 5000 is already in use`

**Solutions:**

1. **Check what's using the port:**
   ```bash
   # On Linux/macOS
   lsof -i :3000
   lsof -i :5000
   
   # On Windows
   netstat -ano | findstr :3000
   netstat -ano | findstr :5000
   ```

2. **Stop the conflicting process:**
   ```bash
   # Kill by PID
   kill -9 <PID>
   ```

3. **Use a different port:**
   
   For Vite, edit `dev-docker-compose.yml`:
   ```yaml
   ports:
     - "3001:3000"  # Host port 3001 → Container port 3000
   ```
   
   For Flask, Flask doesn't directly support port configuration via the CLI. You can set the port using the Flask environment:
   ```bash
   # The Flask dev server defaults to port 5000
   # For production, use a WSGI server like gunicorn:
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 'remy.www.app:create_app("/path/to/notecards")'
   ```

### Mount Issues

**Problem**: `Error: EACCES: permission denied` or files not updating in container

**Solutions:**

1. **Check Docker volume permissions:**
   ```bash
   docker exec -it <container-id> ls -la /app
   ```

2. **Fix ownership issues:**
   ```bash
   # On the host
   sudo chown -R $USER:$USER vite/vite
   ```

3. **Restart the container:**
   ```bash
   docker-compose -f dev-docker-compose.yml down
   docker-compose -f dev-docker-compose.yml up -d
   ```

4. **Check SELinux (Linux only):**
   ```bash
   # If using SELinux, add :z flag to volumes in docker-compose.yml
   volumes:
     - type: bind
       source: ./vite
       target: /app
       bind:
         selinux: z
   ```

### Node Module Caching Problems

**Problem**: `Error: Cannot find module` or dependency issues after updating packages

The development setup uses a bind-mounted volume for `node_modules` to avoid permission issues and improve performance on some systems.

**Solutions:**

1. **Clear the node_modules cache:**
   ```bash
   docker-compose -f dev-docker-compose.yml down
   docker volume rm vite_node_modules  # If using named volume
   docker-compose -f dev-docker-compose.yml up -d
   ```

2. **Reinstall packages inside the container:**
   ```bash
   docker exec -it <container-id> sh
   cd /app
   rm -rf node_modules
   npm install
   ```

3. **Rebuild the Docker image:**
   ```bash
   docker-compose build --no-cache remy-vite
   docker-compose -f dev-docker-compose.yml up -d
   ```

### Common Errors

#### `Error: Cannot connect to the Docker daemon`

**Cause**: Docker is not running or you don't have permission.

**Solution**:
```bash
# Start Docker daemon
sudo systemctl start docker

# Add your user to the docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

#### `Error: No such file or directory: root_asdf.tbz2`

**Cause**: The snapshot file is missing.

**Solution**: 

Either:
1. Obtain the `root_asdf.tbz2` snapshot file from another developer
2. Create a new snapshot following the [Creating a Snapshot](#creating-a-snapshot) steps
3. Or modify the Dockerfile to build from scratch (see [Initial Docker Build](#initial-docker-build))

#### `404 Not Found` when accessing API

**Cause**: Flask server is not running or the proxy is misconfigured.

**Solution**:
1. Verify Flask is running:
   ```bash
   curl http://localhost:5000/api
   ```
2. Check Flask logs for errors
3. Verify the Vite proxy configuration in `vite/vite/vite.config.ts`

#### `Module not found` or TypeScript errors in browser

**Cause**: Dependencies not installed or outdated.

**Solution**:
```bash
cd vite/vite
npm install
```

Or inside the container:
```bash
docker exec -it <container-id> sh
cd /app
npm install
```

#### Container keeps restarting

**Cause**: Usually an error in the entrypoint command or missing dependencies.

**Solution**:
1. Check container logs:
   ```bash
   docker logs <container-id>
   ```
2. Run container interactively:
   ```bash
   docker run -it --entrypoint /bin/sh <image-id>
   ```
3. Debug the startup command manually

#### `ENOSPC: System limit for number of file watchers reached`

**Cause**: Linux inotify watch limit is too low for Vite's file watching.

**Solution**:
```bash
# Temporarily increase the limit
sudo sysctl fs.inotify.max_user_watches=524288

# Permanently increase the limit
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## Additional Resources

- [Remy Configuration Documentation](remy_config.md)
- [Remy Design Overview](design/overview.md)
- [Vue.js Documentation](https://vuejs.org/)
- [Vite Documentation](https://vitejs.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Documentation](https://docs.docker.com/)
- [asdf Version Manager](https://asdf-vm.com/)

---

## Quick Reference

### Common Commands

```bash
# Development
cd vite && ./vite_serve.sh                    # Start Vite dev server
python -m remy.www --cache ~/notes --host 0.0.0.0  # Start Flask API

# Production
cd vite && ./vite_build.sh                    # Build static assets
python -m remy.www --cache ~/notes            # Serve production app

# Docker
docker-compose -f dev-docker-compose.yml up -d      # Start dev environment
docker-compose -f dev-docker-compose.yml down       # Stop dev environment
docker-compose -f dev-docker-compose.yml logs -f    # View logs
docker exec -it <container-id> sh                   # Access container shell

# Debugging
docker ps                                     # List running containers
docker logs <container-id>                   # View container logs
lsof -i :3000                                # Check port 3000 usage
lsof -i :5000                                # Check port 5000 usage
```

### Default Ports

- **Vite Dev Server**: 3000
- **Flask API Server**: 5000

### Key Files

- `vite/Dockerfile` - Container build configuration
- `vite/docker-compose.yml` - Production build configuration
- `vite/dev-docker-compose.yml` - Development environment configuration
- `vite/tar_snapshot.sh` - Snapshot creation script
- `vite/vite_build.sh` - Production build script
- `vite/vite_serve.sh` - Development server startup script
- `vite/vite/vite.config.ts` - Vite configuration (includes proxy setup)
- `src/remy/www/app.py` - Flask application and API routes
- `src/remy/www/__main__.py` - Flask CLI entry point
