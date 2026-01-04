#!/usr/bin/env python3
import secrets
import string

def generate_secure_token(length=48):
    alphabet = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(alphabet) for i in range(length))

def main():
    print("# Generated Secure Keys for Production")
    print(f"VECTOR_API_KEY={generate_secure_token(64)}")
    print(f"QDRANT_API_KEY={generate_secure_token(64)}")
    print(f"LOG_KEY={generate_secure_token(64)}")
    # Add other secrets if needed, e.g. JWT_SECRET
    # print(f"JWT_SECRET={generate_secure_token(64)}")

if __name__ == "__main__":
    main()
