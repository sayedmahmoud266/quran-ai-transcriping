#!/usr/bin/env python3
"""
Debug Chunk Extractor

A simple tool to extract audio chunks from debug data.
Takes a debug step folder, reads the audio and chunks data, and saves individual chunk files.

Usage:
    python debug_chunk_extractor.py <step_folder_path>
    
Example:
    python debug_chunk_extractor.py .debug/job-id/01_SilenceDetectionStep
"""

import json
import sys
from pathlib import Path
import numpy as np
import soundfile as sf


def extract_chunks(step_folder: str):
    """
    Extract audio chunks from a debug step folder.
    
    Args:
        step_folder: Path to the debug step folder
    """
    step_path = Path(step_folder)
    
    # Validate step folder exists
    if not step_path.exists():
        print(f"❌ Error: Step folder not found: {step_path}")
        return
    
    print(f"📁 Processing: {step_path.name}")
    print(f"   Location: {step_path}")
    
    # Load data.json
    data_file = step_path / "data.json"
    if not data_file.exists():
        print(f"❌ Error: data.json not found in {step_path}")
        return
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    print(f"✅ Loaded data.json")
    
    # Load audio file
    audio_folder = step_path / "audio"
    if not audio_folder.exists():
        print(f"❌ Error: audio folder not found in {step_path}")
        return
    
    # Find audio file (usually audio.wav)
    audio_files = list(audio_folder.glob("*.wav"))
    if not audio_files:
        print(f"❌ Error: No audio files found in {audio_folder}")
        return
    
    audio_file = audio_files[0]
    print(f"✅ Found audio file: {audio_file.name}")
    
    # Load audio
    audio_array, sample_rate = sf.read(str(audio_file))
    print(f"✅ Loaded audio: {sample_rate}Hz, {len(audio_array)} samples, {len(audio_array)/sample_rate:.2f}s")
    
    # Get sample rate from data if available
    if 'sample_rate' in data:
        sample_rate = data['sample_rate']
    
    # Check if chunks exist in data
    # Chunks might be in context data or in step_info
    chunks = None
    
    # Try to find chunks in various locations
    if 'step_info' in data and 'chunks' in data['step_info']:
        chunks = data['step_info']['chunks']
    elif 'chunks' in data:
        chunks = data['chunks']
    
    if not chunks:
        print(f"⚠️  No chunks found in data.json")
        print(f"   Available keys: {list(data.keys())}")
        if 'step_info' in data:
            print(f"   step_info keys: {list(data['step_info'].keys())}")
        return
    
    print(f"✅ Found {len(chunks)} chunks")
    
    # Create output folder for chunks
    chunks_output = step_path / "extracted_chunks"
    chunks_output.mkdir(exist_ok=True)
    print(f"📁 Output folder: {chunks_output}")
    
    # Extract and save each chunk
    print(f"\n🔪 Extracting chunks...")
    for i, chunk in enumerate(chunks):
        # Get chunk boundaries (handle different key names)
        start = chunk.get('start', chunk.get('start_time', 0))
        end = chunk.get('end', chunk.get('end_time', 0))
        
        # Convert time to samples
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        
        # Validate boundaries
        if start_sample < 0:
            start_sample = 0
        if end_sample > len(audio_array):
            end_sample = len(audio_array)
        
        # Extract chunk
        chunk_audio = audio_array[start_sample:end_sample]
        
        # Save chunk
        chunk_filename = chunks_output / f"chunk_{i:03d}_{start:.2f}s-{end:.2f}s.wav"
        sf.write(str(chunk_filename), chunk_audio, sample_rate)
        
        duration = end - start
        print(f"   ✓ Chunk {i:3d}: {start:7.2f}s - {end:7.2f}s ({duration:6.2f}s) → {chunk_filename.name}")
    
    print(f"\n✅ Done! Extracted {len(chunks)} chunks to {chunks_output}")
    
    # Create summary file
    summary_file = chunks_output / "chunks_summary.txt"
    with open(summary_file, 'w') as f:
        f.write(f"Chunks Summary\n")
        f.write(f"=" * 60 + "\n\n")
        f.write(f"Step: {step_path.name}\n")
        f.write(f"Audio: {audio_file.name}\n")
        f.write(f"Sample Rate: {sample_rate}Hz\n")
        f.write(f"Total Audio Duration: {len(audio_array)/sample_rate:.2f}s\n")
        f.write(f"Number of Chunks: {len(chunks)}\n\n")
        f.write(f"Chunks:\n")
        f.write(f"-" * 60 + "\n")
        
        for i, chunk in enumerate(chunks):
            start = chunk.get('start', chunk.get('start_time', 0))
            end = chunk.get('end', chunk.get('end_time', 0))
            duration = end - start
            f.write(f"Chunk {i:3d}: {start:7.2f}s - {end:7.2f}s ({duration:6.2f}s)\n")
    
    print(f"✅ Summary saved to {summary_file.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python debug_chunk_extractor.py <step_folder_path>")
        print("\nExample:")
        print("  python debug_chunk_extractor.py .debug/job-id/01_SilenceDetectionStep")
        sys.exit(1)
    
    step_folder = sys.argv[1]
    
    print("=" * 60)
    print("Debug Chunk Extractor")
    print("=" * 60)
    print()
    
    try:
        extract_chunks(step_folder)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
