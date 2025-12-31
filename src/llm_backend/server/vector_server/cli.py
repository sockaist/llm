import argparse
import yaml
import sys
import os
from datetime import datetime
from llm_backend.server.vector_server.config.security_profiles import SecurityProfiles
from llm_backend.server.vector_server.config.security_config import VectorDBConfig
from llm_backend.server.vector_server.config.security_validator import SecurityValidator

CONFIG_FILE = "vectordb.yaml"

def cmd_init(args):
    print("Welcome to VectorDB Security Setup (Secure by Default)")
    print("Available Profiles:")
    profiles = SecurityProfiles.list_profiles()
    for i, p in enumerate(profiles):
        print(f"{i+1}. {p['name']} (Tier {p['tier']})")
        print(f"   {p['description']}")
    
    choice = input("\nSelect profile (1-4) [Default: 2 - production_basic]: ").strip()
    if not choice:
        choice = "2"
    
    try:
        idx = int(choice) - 1
        selected = profiles[idx]
        profile_name = selected["name"]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    profile_data = SecurityProfiles.get_profile(profile_name)
    
    # Save to yaml
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(profile_data["config"], f, sort_keys=False)
    
    print(f"\n✅ Initialized {CONFIG_FILE} with profile '{profile_name}'")
    print("Next: Review file and run 'vectordb security check'")

def cmd_check(args):
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run 'init' first.")
        return

    print(f"Loading {CONFIG_FILE}...")
    try:
        with open(CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
        
        # Parse into Pydantic Model
        config = VectorDBConfig(**data)
        
        print(f"Environment: {config.environment}")
        print(f"Security Tier: {config.security.tier}")
        
        # Validate
        warnings = SecurityValidator.validate_config(config)
        
        if not warnings:
            print("\n✅ Security Check Passed! No warnings.")
            return

        print("\n⚠️  Security Warnings Found:")
        critical_count = 0
        for w in warnings:
            icon = "🔴" if w.severity == "critical" else "🟠" if w.severity == "high" else "🟡"
            print(f"{icon} [{w.severity.upper()}] {w.message}")
            print(f"   Recommendation: {w.recommendation}")
            if w.blocking:
                critical_count += 1
        
        if critical_count > 0:
            print(f"\n❌ FAILED: {critical_count} blocking issues found. Deployment prevented.")
            sys.exit(1)
        else:
            print("\n⚠️  Passed with warnings (Non-blocking).")

    except Exception as e:
        print(f"❌ Error parsing config: {e}")
        sys.exit(1)

def cmd_upgrade(args):
    print("Upgrade wizard not implemented yet. Please modify vectordb.yaml manually to change tiers.")

def main():
    parser = argparse.ArgumentParser(description="VectorDB Security CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("init", help="Initialize configuration")
    subparsers.add_parser("check", help="Validate configuration")
    subparsers.add_parser("upgrade", help="Upgrade security tier")
    
    args = parser.parse_args()
    
    if args.command == "init":
        cmd_init(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "upgrade":
        cmd_upgrade(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
