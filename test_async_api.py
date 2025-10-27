"""
Test script for async API endpoints.
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_async_workflow(audio_file_path):
    """Test complete async workflow."""
    print(f"Testing async workflow with {audio_file_path}...")
    
    # 1. Submit job
    print("\n1. Submitting job...")
    with open(audio_file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/transcribe/async",
            files={'audio_file': f}
        )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    job_id = data['job_id']
    print(f"✓ Job submitted: {job_id}")
    print(f"  Status: {data['status']}")
    
    # 2. Poll for completion
    print("\n2. Polling for completion...")
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(5)
        attempt += 1
        
        response = requests.get(f"{BASE_URL}/jobs/{job_id}/status")
        status_data = response.json()
        status = status_data['status']
        
        print(f"  Attempt {attempt}: {status}")
        
        if status == 'completed':
            print(f"✓ Job completed!")
            print(f"  Started at: {status_data['started_at']}")
            print(f"  Completed at: {status_data['completed_at']}")
            break
        elif status == 'failed':
            print(f"✗ Job failed: {status_data.get('error', 'Unknown error')}")
            return
    
    if status != 'completed':
        print("✗ Timeout waiting for job completion")
        return
    
    # 3. Get metadata
    print("\n3. Getting metadata...")
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/metadata")
    metadata = response.json()
    print(f"✓ Metadata retrieved:")
    print(f"  Surah: {metadata.get('surah_number')}")
    print(f"  Total Ayahs: {metadata.get('total_ayahs')}")
    print(f"  Transcription length: {len(metadata.get('transcription', ''))} chars")
    
    # 4. Download result
    print("\n4. Downloading result...")
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/download")
    
    if response.status_code == 200:
        output_file = f"test_result_{job_id[:8]}.zip"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"✓ Result downloaded: {output_file}")
        print(f"  Size: {len(response.content)} bytes")
    else:
        print(f"✗ Download failed: {response.status_code}")
    
    print("\n✓ Async workflow test completed successfully!")

def test_list_jobs():
    """Test list jobs endpoint."""
    print("\nTesting /jobs endpoint...")
    response = requests.get(f"{BASE_URL}/jobs?limit=10")
    data = response.json()
    print(f"✓ Found {data['total']} jobs")
    for job in data['jobs'][:3]:
        print(f"  - {job['job_id'][:8]}... | {job['status']} | {job['original_filename']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_async_api.py <audio_file_path>")
        print("\nOr just test health:")
        print("  python test_async_api.py --health")
        sys.exit(1)
    
    if sys.argv[1] == "--health":
        test_health()
    else:
        audio_file = sys.argv[1]
        test_health()
        test_async_workflow(audio_file)
        test_list_jobs()
