import os
import argparse
from huggingface_hub import HfApi, login

def upload_model(model_path, repo_id, token=None):
    """
    Uploads a local model directory to Hugging Face Hub.
    """
    if not os.path.exists(model_path):
        print(f"❌ Error: Model path '{model_path}' does not exist.")
        return

    print(f"[INFO] Preparing to upload '{model_path}' to '{repo_id}'...")

    if token:
        login(token=token)
    
    api = HfApi()
    
    # Create repo if not exists
    try:
        api.create_repo(repo_id=repo_id, exist_ok=True)
        print(f"[OK] Repository '{repo_id}' ready.")
    except Exception as e:
        print(f"[ERROR] Failed to create repo: {e}")
        return

    # Upload folder
    try:
        api.upload_folder(
            folder_path=model_path,
            repo_id=repo_id,
            repo_type="model",
            ignore_patterns=[".ds_store", "*.bin.index", "optimizer.pt"] # Ignore huge transient files if any
        )
        print(f"\n[OK] Success! Model uploaded to: https://huggingface.co/{repo_id}")
        print("   You can now use this Model ID in your docker-compose.yml or config.")
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Fine-tuned Model to Hugging Face Hub")
    parser.add_argument("--path", type=str, default="./bge-m3-finetuned-academic", help="Local path to model directory")
    parser.add_argument("--repo", type=str, required=True, help="Target Repo ID (e.g., your-username/bge-m3-kaist)")
    parser.add_argument("--token", type=str, default=None, help="Hugging Face Write Token (Optional if already logged in)")
    
    args = parser.parse_args()
    
    upload_model(args.path, args.repo, args.token)
