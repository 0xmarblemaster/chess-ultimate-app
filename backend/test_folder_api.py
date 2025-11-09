#!/usr/bin/env python3
"""
Test script for folder monitoring API functionality.
"""

import requests
import json
import sys
import os

def test_folder_api():
    """Test the folder monitoring API endpoints."""
    
    base_url = "http://localhost:5000/api/folder"
    
    print("🧪 Testing Folder Monitoring API...")
    
    # Test 1: Get folder status
    print("\n📊 Testing /status endpoint...")
    try:
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Status endpoint working!")
            print(f"   Input files: {data['input_folder']['total_files']}")
            print(f"   Unprocessed: {data['input_folder']['unprocessed_files']}")
            print(f"   Processed files: {data['processed_folder']['total_files']}")
            print(f"   Total chunks: {data['processed_folder']['total_chunks']}")
            print(f"   Weaviate connected: {data['weaviate'].get('connected', False)}")
            print(f"   Weaviate chunks: {data['weaviate'].get('total_chunks', 0)}")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing status endpoint: {e}")
    
    # Test 2: Check if there are files to process
    print("\n📁 Checking for files to process...")
    try:
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            unprocessed = data['input_folder']['unprocessed_files']
            
            if unprocessed > 0:
                print(f"📤 Found {unprocessed} unprocessed files")
                
                # Test 3: Process all files
                print("\n🔄 Testing /process-all endpoint...")
                try:
                    response = requests.post(f"{base_url}/process-all", timeout=60)
                    if response.status_code == 200:
                        result = response.json()
                        print("✅ Process-all endpoint working!")
                        print(f"   Processed: {result.get('processed_count', 0)} files")
                        if 'results' in result:
                            for r in result['results']:
                                status = "✅" if r['status'] == 'success' else "❌"
                                print(f"   {status} {r['filename']}: {r.get('chunks_created', 0)} chunks")
                    else:
                        print(f"❌ Process-all failed: {response.status_code}")
                        print(f"   Response: {response.text}")
                except Exception as e:
                    print(f"❌ Error testing process-all: {e}")
            else:
                print("ℹ️  No unprocessed files found")
        
    except Exception as e:
        print(f"❌ Error checking for files: {e}")
    
    print("\n🏁 Folder API testing completed!")

if __name__ == "__main__":
    test_folder_api() 