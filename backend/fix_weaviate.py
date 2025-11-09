#!/usr/bin/env python3
import os
import subprocess
from etl import config

def reset_weaviate_and_run_etl():
    """
    Reset Weaviate container and run the ETL pipeline again
    """
    print("=== Resetting Weaviate and running ETL pipeline ===")
    
    # Step 1: Stop and remove Weaviate container
    print("\n1. Stopping and removing Weaviate container with volumes...")
    weaviate_compose_file = "/home/marblemaster/Desktop/Cursor/weaviate-docker-compose.yml"
    
    try:
        print("Running: docker compose -f weaviate-docker-compose.yml down -v")
        subprocess.run(
            ["docker", "compose", "-f", weaviate_compose_file, "down", "-v"],
            cwd="/home/marblemaster/Desktop/Cursor",
            check=True
        )
        print("Successfully stopped and removed Weaviate")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping Weaviate: {e}")
        return
    
    # Step 2: Start Weaviate again
    print("\n2. Starting Weaviate again...")
    try:
        print("Running: docker compose -f weaviate-docker-compose.yml up -d")
        subprocess.run(
            ["docker", "compose", "-f", weaviate_compose_file, "up", "-d"],
            cwd="/home/marblemaster/Desktop/Cursor",
            check=True
        )
        print("Successfully started Weaviate")
    except subprocess.CalledProcessError as e:
        print(f"Error starting Weaviate: {e}")
        return
    
    # Step 3: Run the ETL pipeline
    print("\n3. Running the ETL pipeline...")
    try:
        print("Running: python -m etl.main")
        etl_result = subprocess.run(
            ["python", "-m", "etl.main"],
            cwd="/home/marblemaster/Desktop/Cursor/mvp1/backend",
            check=True
        )
        print("ETL pipeline completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running ETL pipeline: {e}")
        return
    
    # Step 4: Verify the database was populated correctly
    print("\n4. Verifying database population...")
    try:
        print("Checking database content:")
        subprocess.run(
            ["python", "list_weaviate_diagrams.py"],
            cwd="/home/marblemaster/Desktop/Cursor/mvp1/backend",
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error checking database content: {e}")
    
    print("\n5. Testing RAG Query...")
    try:
        print("Running debug query:")
        subprocess.run(
            ["python", "debug_rag.py"],
            cwd="/home/marblemaster/Desktop/Cursor/mvp1/backend",
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running debug query: {e}")
    
    print("\n=== Process completed ===")

if __name__ == "__main__":
    reset_weaviate_and_run_etl() 