import requests
import uuid
import time
import logging
from typing import List, Dict, Any, Optional

from vectordb.core.config import Config, ConfigObject
from vectordb.core.handler import JSONHandler

# Simple Retry Decorator
def retry(times=3, delay=1, backoff=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            tries = 0
            current_delay = delay
            while tries < times:
                try:
                    return func(*args, **kwargs)
                except (requests.ConnectionError, requests.Timeout) as e:
                    tries += 1
                    if tries == times:
                        raise e
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

class _SDKColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class VectorDBClient:
    """
    Synchronous Python Client for VectorDB.
    """
    
    def __init__(self, config: Optional[ConfigObject] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.config = config or Config.load()
        if base_url:
            self.base_url = base_url.rstrip('/')
            self.host = self.base_url.split("//")[-1].split(":")[0]
            try:
                self.port = int(self.base_url.split(":")[-1])
            except:
                self.port = 80
        else:
            self.host = self.config.server.host
            # If host is 0.0.0.0, client should use localhost or specific IP. 
            # Standard fix for local dev:
            if self.host == "0.0.0.0":
                self.host = "127.0.0.1"
                
            self.port = self.config.server.port
            self.base_url = f"http://{self.host}:{self.port}"
        
        # Auth priority:
        # 1. Explicit Argument
        # 2. Saved Credentials (CLI Login)
        # 3. Config (Environment/Defaults)
        
        self.api_key = api_key
        
        if not self.api_key:
            import os
            creds_path = os.path.join(os.path.expanduser("~"), ".vortex", "credentials")
            if os.path.exists(creds_path):
                try:
                    with open(creds_path, "r") as f:
                        token_candidate = f.read().strip()
                        if token_candidate:
                            self.api_key = token_candidate
                except Exception:
                    pass
        
        # Fallback to config if still None
        if not self.api_key:
            self.api_key = self.config.vectordb.api_key
        
        self.handler = JSONHandler(strategy='auto')
        self.session = requests.Session()
        if self.api_key:
             self.session.headers.update({
                 "Authorization": f"Bearer {self.api_key}",
                 "x-api-key": self.api_key
             })
             
        self.logger = logging.getLogger("vectordb.client")

    @retry(times=3)
    def search(self, text: str, top_k: int = 10, collection: Optional[str] = None, alpha: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute Hybrid Search.
        """
        request_id = str(uuid.uuid4())[:8]
        headers = {"X-Correlation-ID": request_id}
        
        payload = {
            "query_text": text,
            "top_k": top_k,
            "collections": [collection] if collection else None
        }
        if alpha is not None:
             payload["alpha"] = alpha
             
        self.logger.info(f"[{request_id}] Search: {text}")
        
        resp = self.session.post(
            f"{self.base_url}/query/hybrid",
            json=payload,
            headers=headers,
            timeout=60.0
        )
        resp.raise_for_status()
        return resp.json()

    def get_document(self, collection: str, db_id: str) -> Dict[str, Any]:
        """Fetch a single document by its DB ID."""
        resp = self.session.get(f"{self.base_url}/crud/document/{collection}/{db_id}", timeout=5)
        resp.raise_for_status()
        return resp.json()

    def list_collections(self) -> List[str]:
        """List all available collections."""
        # Using the health status endpoint which returns collection info
        resp = self.session.get(f"{self.base_url}/health/status", timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # The structure from endpoints_health.py seems to be { "collections": { "name": {...} } }
        return list(data.get("collections", {}).keys())

    def get_collection_info(self, collection: str) -> Dict[str, Any]:
        """Get stats for a specific collection."""
        resp = self.session.get(f"{self.base_url}/health/status", timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("collections", {}).get(collection, {})

    @retry(times=3)
    def upsert(self, collection: str, documents: List[Dict[str, Any]], batch_size: int = 100, wait: bool = False) -> Dict[str, Any]:
        """
        Upsert documents (Auto-batching, Auto-flattening).
        If wait=True, it uses the async queue and polls until completion (prevents HTTP timeouts).
        """
        if wait:
            # For wait=True, we still batch on the client to avoid huge HTTP payloads
            # but we track all jobs and wait for them.
            results = []
            try:
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i+batch_size]
                    self.logger.info(f"Enqueuing batch {i//batch_size + 1}/{(len(documents)//batch_size)+1}...")
                    results.append(self.enqueue_upsert(collection, batch, wait=True))
                
                total_count = sum(res.get("count", 0) for res in results)
                return {"status": "success", "count": total_count, "batches": len(results)}
            except KeyboardInterrupt:
                self.logger.info("Ingestion interrupted by user.")
                raise
            
        request_id = str(uuid.uuid4())[:8]
        headers = {"X-Correlation-ID": request_id}
        total_upserted = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            processed_batch = [self.handler.process(doc) for doc in batch]
            
            payload = {"collection": collection, "documents": processed_batch}
            
            try:
                self.logger.info(f"[{request_id}] Upserting batch {i//batch_size + 1} ({len(batch)} docs)")
                resp = self.session.post(
                    f"{self.base_url}/crud/upsert_batch",
                    json=payload,
                    headers=headers,
                    timeout=30 
                )
                resp.raise_for_status()
                total_upserted += len(batch)
            except Exception as e:
                self.logger.error(f"[{request_id}] Batch failed: {e}")
                raise e

        return {"status": "success", "count": total_upserted}

    def enqueue_upsert(self, collection: str, documents: List[Dict[str, Any]], wait: bool = True) -> Dict[str, Any]:
        """
        Queue documents for async ingestion. Returns job_id immediately if wait=False.
        """
        request_id = str(uuid.uuid4())[:8]
        headers = {"X-Correlation-ID": request_id}
        
        # Process docs before sending
        processed_docs = [self.handler.process(doc) for doc in documents]
        
        payload = {
            "collection": collection,
            "documents": processed_docs
        }
        
        resp = self.session.post(
            f"{self.base_url}/batch/upsert_batch",
            json=payload,
            headers=headers,
            timeout=60
        )
        resp.raise_for_status()
        job_data = resp.json()
        job_id = job_data.get("job_id")
        
        if not wait:
            return job_data
            
        # Polling logic
        self.logger.info(f"[{request_id}] Job {job_id[:8]} queued. Polling for completion (Max 30 min)...")
        start_time = time.time()
        last_log_time = start_time
        
        while True:
            status_resp = self.session.get(f"{self.base_url}/batch/jobs/status/{job_id}", timeout=5)
            status_resp.raise_for_status()
            data = status_resp.json().get("job", {})
            status = data.get("status")
            progress = data.get("progress", 0.0)
            
            if status == "completed":
                self.logger.info(f"[{request_id}] Job {job_id[:8]} completed successfully.")
                return {"status": "success", "job_id": job_id, "count": len(documents)}
            elif status == "failed":
                msg = data.get("message", "Unknown error")
                self.logger.error(f"[{request_id}] Job {job_id[:8]} failed: {msg}")
                raise Exception(f"Async ingestion failed: {msg}")
            
            # Progress logging every 10 seconds with ETC calculation
            current_time = time.time()
            if current_time - last_log_time > 10:
                elapsed = current_time - start_time
                etc_str = "Calculating..."
                if progress > 0:
                    total_est = elapsed / (progress / 100.0)
                    etc_seconds = max(0, total_est - elapsed)
                    if etc_seconds > 60:
                        etc_str = f"{int(etc_seconds // 60)}m {int(etc_seconds % 60)}s"
                    else:
                        etc_str = f"{int(etc_seconds)}s"
                
                self.logger.info(f"[{request_id}] Progress: {progress:.1f}% | Elapsed: {int(elapsed)}s | ETC: {etc_str} ({status})")
                last_log_time = current_time

            if current_time - start_time > 1800: # 30 min timeout
                raise TimeoutError(f"Job {job_id} timed out after 30 minutes")
                
            try:
                time.sleep(2)
            except KeyboardInterrupt:
                self.logger.info(f"Polling for job {job_id[:8]} interrupted.")
                raise

    def interactive_search(self, collection: str, top_k: int = 3, product_name: str = "VortexDB"):
        """
        Launch an interactive REPL search interface in the terminal.
        """
        c = _SDKColors
        import os
        
        # Internal state
        current_collection = collection
        current_top_k = top_k

        def print_help():
            print(f"\n{c.BOLD}Available Commands:{c.ENDC}")
            print(f"  {c.GREEN}SEARCH \"<query>\"{c.ENDC} : Execute hybrid search (or just type the query)")
            print(f"  {c.GREEN}OPEN <db_id>{c.ENDC}    : Pretty-print full JSON of a document")
            print(f"  {c.GREEN}INFO{c.ENDC}            : Show stats for the current collection")
            print(f"  {c.GREEN}COLLECTIONS{c.ENDC}     : List all available collections")
            print(f"  {c.GREEN}TOPK <n>{c.ENDC}        : Set number of results to display")
            print(f"  {c.GREEN}CLEAR{c.ENDC}           : Clear the terminal screen")
            print(f"  {c.GREEN}LOGIN{c.ENDC}           : Switch user / Login")
            print(f"  {c.GREEN}HELP{c.ENDC}            : Show this help message")
            print(f"  {c.GREEN}EXIT/QUIT{c.ENDC}       : Close the REPL")

        from vectordb.core.branding import print_vortex_banner
        print_vortex_banner()

        print(c.CYAN + "="*50)
        print(f"   {product_name} - Interactive Command Shell")
        print("="*50 + c.ENDC)
        print(f"Connected to: {self.base_url}")
        print("Type 'HELP' for commands list.\n")

        while True:
            try:
                line = input(c.BOLD + f"{product_name} [{current_collection}] >> " + c.ENDC).strip()
                if not line:
                    continue
                
                cmd_parts = line.split(maxsplit=1)
                cmd = cmd_parts[0].upper()
                arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

                if cmd == "LOGIN":
                    import getpass
                    import requests
                    
                    print(f"\n{c.BOLD}Login to {self.base_url}{c.ENDC}")
                    u = input("Username: ").strip()
                    p = getpass.getpass("Password: ")
                    
                    try:
                         resp = requests.post(f"{self.base_url}/auth/login", json={"username": u, "password": p})
                         if resp.status_code == 200:
                             token = resp.json().get("access_token")
                             creds_path = os.path.expanduser("~/.vortex/credentials")
                             os.makedirs(os.path.dirname(creds_path), exist_ok=True)
                             with open(creds_path, "w") as f:
                                 f.write(token)
                             
                             # Update current client state
                             self.api_key = token
                             print(c.GREEN + "Login Successful! Client credentials updated." + c.ENDC)
                         else:
                             print(c.FAIL + f"Login Failed: {resp.text}" + c.ENDC)
                    except Exception as e:
                        print(c.FAIL + f"Connection Error: {e}" + c.ENDC)

                elif cmd in ("EXIT", "QUIT", "Q"):
                    break
                elif cmd == "HELP":
                    print_help()
                elif cmd == "CLEAR":
                    os.system('cls' if os.name == 'nt' else 'clear')
                elif cmd == "COLLECTIONS":
                    colls = self.list_collections()
                    print(f"\nAvailable Collections: {', '.join(colls)}")
                elif cmd == "INFO":
                    info = self.get_collection_info(current_collection)
                    print(f"\n{c.BOLD}Collection Info [{current_collection}]:{c.ENDC}")
                    print(json.dumps(info, indent=2))
                elif cmd == "TOPK":
                    try:
                        current_top_k = int(arg)
                        print(f"Set TOPK to {current_top_k}")
                    except ValueError:
                        print(c.FAIL + "Invalid number for TOPK" + c.ENDC)
                elif cmd == "OPEN":
                    if not arg:
                        print(c.FAIL + "Usage: OPEN <db_id>" + c.ENDC)
                        continue
                    try:
                        doc_resp = self.get_document(current_collection, arg)
                        if doc_resp.get("status") == "success" and doc_resp.get("results"):
                             print(f"\n{c.BOLD}Document [{arg}]:{c.ENDC}")
                             print(json.dumps(doc_resp["results"][0], indent=2, ensure_ascii=False))
                        else:
                             print(c.WARNING + f"Document not found: {arg}" + c.ENDC)
                    except Exception as e:
                        print(c.FAIL + f"Error opening document: {e}" + c.ENDC)
                else:
                    # Default to SEARCH
                    query_text = line
                    if cmd == "SEARCH" and arg:
                        # Handle SEARCH "query" or SEARCH query
                        query_text = arg.strip('"').strip("'")
                    
                    print(f"Searching for: '{query_text}'...")
                    results = self.search(text=query_text, collection=current_collection, top_k=current_top_k)
                    
                    if "results" in results and results["results"]:
                        for idx, res in enumerate(results["results"]):
                            score = res.get("score", 0.0)
                            payload = res.get("payload", {})
                            db_id = res.get("id")
                            
                            text = payload.get("content") or payload.get("text") or payload.get("_text", "")
                            text = str(text)[:200]
                            
                            print(c.BLUE + f"\n[{idx+1}] Score: {score:.4f} | DB ID: {db_id}" + c.ENDC)
                            print(f"Snippet: {text}...")
                    else:
                        print(c.WARNING + "No results found." + c.ENDC)
                    
            except EOFError:
                print("\nInput closed. Exiting...")
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(c.FAIL + f"Error: {e}" + c.ENDC)
