import click
import sys
import json
import uvicorn
from vectordb.core.config import Config
from vectordb.core.logger import logger

@click.group()
def cli():
    """VectorDB CLI v2.0"""
    pass

@cli.group()
def config():
    """Configuration management"""
    pass

@config.command()
@click.option('--env', default=None, help='Environment (development/production)')
def show(env):
    """Show current configuration."""
    cfg = Config.load(env=env)
    click.echo(json.dumps(cfg.dict(), indent=2, default=str))

@cli.group()
def server():
    """Server management"""
    pass

@server.command()
@click.option('--port', default=None, help='Override port')
@click.option('--env', default=None, help='Environment')
def start(port, env):
    """Start VortexDB Server."""
    from vectordb.core.branding import print_vortex_banner
    print_vortex_banner()
    cfg = Config.load(env=env)
    
    final_port = int(port) if port else cfg.server.port
    final_host = cfg.server.host
    workers = cfg.server.workers
    
    logger.info(f"Starting VortexDB v{cfg.app.version}")
    logger.info(f"Env: {cfg.app.env}")
    logger.info(f"{final_host}:{final_port} (Workers: {workers})")
    
    # In a real migration, this would import the FastAPI app factory
    # from vectordb.server.app import create_app
    # uvicorn.run(create_app(cfg), ...)
    
    # For now, we launch the existing legacy app with the NEW config settings applied via env vars?
    # Or just prove the CLI works.
    # Let's just run a dummy uvicorn for demonstration if validation is all we need, 
    # OR point to the actual legacy app: "llm_backend.server.vector_server.main:app"
    
    
    # Run Uvicorn
    # We point to the string reference of the app for workers > 1 support (but logic here is programmatic)
    # For workers support with programmatic uvicorn, it's better to use subprocess or uvicorn.run("path:app")
    
    
    # Ensure 'src' is in python path for legacy llm_backend imports
    import os
    import sys
    
    current_dir = os.getcwd()
    src_dir = os.path.join(current_dir, "src")
    if os.path.exists(src_dir) and src_dir not in sys.path:
        sys.path.append(src_dir)
        print(f"[INFO] Added {src_dir} to sys.path")

    app_str = "llm_backend.server.vector_server.main:app"
    
    from vectordb.core.logger import get_uvicorn_log_config
    log_cfg = get_uvicorn_log_config()
    
    if workers > 1:
        # Multiprocessing requires string import, so sys.path must be set in subprocesses too?
        os.environ["PYTHONPATH"] = f"{src_dir}:{os.environ.get('PYTHONPATH', '')}"
        uvicorn.run(app_str, host=final_host, port=final_port, workers=workers, log_config=log_cfg)
    else:
        # Development mode usually
        uvicorn.run(app_str, host=final_host, port=final_port, log_config=log_cfg)

@cli.command()
@click.option('--url', default=None, help='VortexDB Server URL (e.g. http://localhost:8000)')
@click.option('--collection', default="demo_collection", help='Target collection name')
@click.option('--top-k', default=3, type=int, help='Number of results to show')
@click.option('--name', default="VortexDB", help='Product name to display')
@click.option('--login', is_flag=True, help='Force login prompt before starting')
@click.option('--username', default=None, help='Username for auto-login')
@click.option('--password', default=None, help='Password for auto-login')
def search(url, collection, top_k, name, login, username, password):
    """Launch interactive search interface."""
    from vectordb.client.sync_client import VectorDBClient
    import os
    
    # Handle Login Logic
    creds_path = os.path.expanduser("~/.vortex/credentials")
    has_creds = os.path.exists(creds_path)
    ctx = click.get_current_context()
    
    if username and password:
        # Inline Login
        click.echo("Attempting inline login...")
        ctx.invoke(login_command, username=username, password=password, url=url or "http://localhost:8000")
        has_creds = True # Assume success or the command would have errored/printed
        
    elif login or not has_creds:
        if not has_creds:
            click.echo("Warning: No credentials found. You are entering as GUEST.")
        
        # If force login is requested OR user confirms they want to login when no creds exist
        if login or click.confirm("Do you want to login now?", default=True):
            ctx.invoke(login_command, url=url or "http://localhost:8000")

    try:
        # Initialize client with optional base_url override
        client = VectorDBClient(base_url=url)
        client.interactive_search(collection=collection, top_k=top_k, product_name=name)
    except Exception as e:
        click.echo(f"[ERROR] Could not connect to VortexDB: {e}")

@cli.command()
def init():
    """Initialize VortexDB Security System."""
    from vectordb.core.security.db import UserManager, UserRole
    try:
        click.echo("Initializing Security Database...")
        manager = UserManager()
        
        # Check if admin exists
        if manager.get_user("admin"):
            click.echo("Admin user already exists.")
            return

        password = click.prompt("Set password for 'admin'", hide_input=True)
        confirm = click.prompt("Confirm password", hide_input=True)
        
        if password != confirm:
            click.echo("Passwords do not match.")
            return
            
        manager.create_user("admin", password, UserRole.ADMIN)
        click.echo("Security System Initialized. Use 'vortex login' to authenticate.")
        
    except Exception as e:
        click.echo(f"[ERROR] Init failed: {e}")

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--collection', default="csweb", help='Target collection name')
@click.option('--url', default=None, help='VortexDB Server URL')
@click.option('--batch-size', default=20, type=int, help='Batch size for ingestion')
def ingest(path, collection, url, batch_size):
    """Ingest JSON files from a folder into VortexDB."""
    import os
    import glob
    import json
    from vectordb.client.sync_client import VectorDBClient
    
    # 1. Collect Files
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "**", "*.json"), recursive=True)
    else:
        files = [path]
    
    if not files:
        click.echo("No JSON files found in the specified path.")
        return
    
    click.echo(f"Found {len(files)} files. Connecting to {url or 'default server'}...")
    
    try:
        client = VectorDBClient(base_url=url)
        
        # 2. Load and Process
        all_docs = []
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_docs.extend(data)
                    else:
                        all_docs.append(data)
            except Exception as e:
                click.echo(f"  [Skip] Failed to load {os.path.basename(fpath)}: {e}")
        
        if not all_docs:
            click.echo("No valid JSON data extracted.")
            return

        click.echo(f"Ingesting {len(all_docs)} documents into '{collection}'...")
        
        # 3. Batch Upsert
        # We use wait=True to see progress in terminal
        client.upsert(collection=collection, documents=all_docs, batch_size=batch_size, wait=True)
        
        click.echo("\nIngestion Complete!")
        
    except KeyboardInterrupt:
        click.echo("\n[INFO] Ingestion cancelled by user.")
    except Exception as e:
        click.echo(f"[ERROR] Ingestion failed: {e}")

@cli.command(name="login")
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
@click.option('--url', default="http://localhost:8000", help='Server URL')
def login_command(username, password, url):
    """Login and save credentials."""
    import requests
    import os
    
    try:
        # For now, hit the API endpoint we ARE GOING TO BUILD
        # But if server is not up, or we are running local, maybe direct DB check?
        # NO, login should use the API to get the token.
        
        click.echo(f"Logging in to {url}...")
        
        payload = {"username": username, "password": password}
        # We need to implement this endpoint in Phase 3
        # For Phase 2 dev, we can fallback to direct persistence mocking or wait.
        # Let's implement full API flow.
        
        resp = requests.post(f"{url}/auth/login", json=payload)
        
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            home = os.path.expanduser("~")
            creds_dir = os.path.join(home, ".vortex")
            os.makedirs(creds_dir, exist_ok=True)
            
            with open(os.path.join(creds_dir, "credentials"), "w") as f:
                f.write(token)
                
            click.echo("Login Successful. Token saved.")
        else:
            click.echo(f"Login Failed: {resp.text}")
            
    except Exception as e:
        click.echo(f"[ERROR] Connection failed: {e}")

@cli.group()
def user():
    """User management commands."""
    pass

@user.command(name="create")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True)
@click.option("--role", default="guest", help="User role (admin, viewer, guest)")
def user_create(username, password, role):
    """Create a new user (Direct DB Access)."""
    from vectordb.core.security.db import UserManager, UserRole
    # In production, this should call API. For "vortex user" admin tool, DB access is okay?
    # Ideally CLI talks to API. But "vortex init" implies local access.
    # Let's support local DB access for admin tool for now.
    
    try:
        manager = UserManager()
        manager.create_user(username, password, UserRole(role))
    except Exception as e:
        click.echo(f"Error: {e}")

@user.command(name="list")
def user_list():
    """List all users."""
    from vectordb.core.security.db import UserManager
    manager = UserManager()
    users = manager.list_users()
    for u in users:
        click.echo(f"{u.id}: {u.username} [{u.role}] (Active: {u.is_active})")

@cli.group()
def system():
    """System-wide orchestration and maintenance."""
    pass

@system.command()
@click.option('--env', default=None, help='Environment')
@click.option('--force', is_flag=True, help='Force start even if dependencies seem running')
def stack(env, force):
    """Start the entire VortexDB stack (Redis, Celery, API)."""
    import os
    import subprocess
    import time
    from vectordb.core.branding import print_vortex_banner
    print_vortex_banner()
    
    cfg = Config.load(env=env)
    current_dir = os.getcwd()
    src_dir = os.path.join(current_dir, "src")
    
    # 1. Start Redis (if local)
    try:
        subprocess.run(["redis-cli", "ping"], capture_output=True, check=True)
        logger.info("Redis is already running.")
    except Exception:
        logger.info("Starting Redis...")
        subprocess.Popen(["redis-server", "--daemonize", "yes"])
        time.sleep(2)

    # 2. Start Celery
    logger.info("Starting Celery worker...")
    # Kill old ones if force
    if force:
        subprocess.run(["pkill", "-f", "celery worker"], capture_output=True)
        
    env_vars = os.environ.copy()
    env_vars["PYTHONPATH"] = f"{src_dir}:{env_vars.get('PYTHONPATH', '')}"
    
    # Assuming solo pool for macOS stability
    pool_args = ["--pool=solo"] if sys.platform == "darwin" else []
    
    subprocess.Popen(
        ["celery", "-A", "llm_backend.server.vector_server.worker.celery_app", "worker", "--loglevel=info"] + pool_args,
        env=env_vars,
        stdout=open("celery.log", "a"),
        stderr=subprocess.STDOUT
    )
    
    # 3. Start API (Foreground)
    logger.info("Starting API Server...")
    app_str = "llm_backend.server.vector_server.main:app"
    from vectordb.core.logger import get_uvicorn_log_config
    log_cfg = get_uvicorn_log_config()
    
    uvicorn.run(app_str, host=cfg.server.host, port=cfg.server.port, log_config=log_cfg)

@system.command()
@click.option('--hard', is_flag=True, help='Also delete security database, logs, and snapshots')
def reset(hard):
    """Reset system state (Flush Redis, Clear Qdrant collections)."""
    import redis
    import os
    from qdrant_client import QdrantClient
    
    cfg = Config.load()
    logger.info("Starting VortexDB System Reset...")

    # 1. Flush Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.flushall()
        logger.info("Redis cache flushed.")
    except Exception as e:
        logger.warning(f"Redis reset failed: {e}")

    # 2. Clear Qdrant
    try:
        # Suppress version warning
        client = QdrantClient(url=f"http://{cfg.vectordb.host}:{cfg.vectordb.port}", check_compatibility=False)
        # Identify collections (could be dynamic)
        collections = ["csweb", "semantic_cache", "demo_collection"]
        for col in collections:
            try:
                client.delete_collection(col)
                logger.info(f"Deleted Qdrant collection: {col}")
            except Exception as e:
                logger.warning(f"Failed to delete collection {col}: {e}")
    except Exception as e:
        logger.warning(f"Qdrant reset failed: {e}")

    # 3. Hard Cleanup
    if hard:
        db_path = "vortex_security.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("Security database deleted.")
        
        if os.path.exists("logs"):
            import shutil
            shutil.rmtree("logs")
            os.makedirs("logs")
            logger.info("Logs cleared.")
            
        if os.path.exists("snapshots"):
            import shutil
            shutil.rmtree("snapshots")
            os.makedirs("snapshots")
            logger.info("Snapshots cleared.")

    logger.info("System Reset Complete.")
