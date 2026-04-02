#!/usr/bin/env python3
"""
CDJ File Compatibility Checker
Checks audio file compatibility across various Pioneer CDJ models
Analyzes sample rate, bit depth, bitrate, and other technical specifications
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set, Optional

# CDJ Model Specifications
CDJ_MODELS = {
    "CDJ-3000": {
        "formats": {"mp3", "aac", "wav", "aiff", "flac", "alac"},
        "sample_rates": {44100, 48000, 88200, 96000, 176400, 192000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,  # kbps for MP3
        "rekordbox": True,
        "usb": True,
        "sd_card": True,
    },
    "CDJ-2000NXS2": {
        "formats": {"mp3", "aac", "wav", "aiff", "flac", "alac"},
        "sample_rates": {44100, 48000, 88200, 96000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": True,
    },
    "CDJ-2000NXS": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": True,
    },
    "CDJ-2000": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": True,
    },
    "CDJ-900NXS": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": False,
    },
    "CDJ-900": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": False,
    },
    "CDJ-850": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16, 24},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": False,
    },
    "CDJ-400": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16},
        "max_bitrate": 320,
        "rekordbox": False,
        "usb": True,
        "sd_card": False,
    },
    "CDJ-350": {
        "formats": {"mp3", "aac", "wav", "aiff"},
        "sample_rates": {44100, 48000},
        "bit_depths": {16},
        "max_bitrate": 320,
        "rekordbox": True,
        "usb": True,
        "sd_card": False,
    },
}


def get_file_extension(filepath: str) -> str:
    """Extract file extension from filepath."""
    return Path(filepath).suffix.lower().lstrip('.')


def get_audio_metadata(filepath: str) -> Optional[Dict]:
    """
    Extract audio metadata using ffprobe (if available).
    
    Args:
        filepath: Path to the audio file
    
    Returns:
        Dictionary with audio metadata or None if extraction fails
    """
    try:
        # Check if ffprobe is available
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
             '-show_format', '-show_streams', filepath],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        
        # Find audio stream
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        if not audio_stream:
            return None
        
        metadata = {
            'sample_rate': int(audio_stream.get('sample_rate', 0)),
            'bit_depth': audio_stream.get('bits_per_raw_sample') or audio_stream.get('bits_per_sample'),
            'channels': audio_stream.get('channels'),
            'codec': audio_stream.get('codec_name'),
            'duration': float(data.get('format', {}).get('duration', 0)),
            'bit_rate': int(data.get('format', {}).get('bit_rate', 0)),
            'file_size': int(data.get('format', {}).get('size', 0)),
        }
        
        # Convert bit depth to int if present
        if metadata['bit_depth']:
            try:
                metadata['bit_depth'] = int(metadata['bit_depth'])
            except (ValueError, TypeError):
                metadata['bit_depth'] = None
        
        return metadata
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
            json.JSONDecodeError, FileNotFoundError):
        return None


def check_file_compatibility(filepath: str, cdj_model: str) -> Dict:
    """
    Check if a file is compatible with a specific CDJ model.
    
    Args:
        filepath: Path to the audio file
        cdj_model: CDJ model name (e.g., 'CDJ-3000')
    
    Returns:
        Dictionary with compatibility information
    """
    if cdj_model not in CDJ_MODELS:
        return {
            "compatible": False,
            "error": f"Unknown CDJ model: {cdj_model}"
        }
    
    if not os.path.exists(filepath):
        return {
            "compatible": False,
            "error": f"File not found: {filepath}"
        }
    
    specs = CDJ_MODELS[cdj_model]
    file_ext = get_file_extension(filepath)
    
    result = {
        "file": filepath,
        "model": cdj_model,
        "format": file_ext,
        "compatible": True,
        "warnings": [],
        "errors": [],
        "notes": [],
        "metadata": None
    }
    
    # Check format compatibility
    if file_ext not in specs["formats"]:
        result["compatible"] = False
        result["errors"].append(f"Format {file_ext.upper()} is NOT supported by {cdj_model}")
        result["notes"].append(f"Supported formats: {', '.join(sorted(specs['formats'])).upper()}")
        return result
    
    result["notes"].append(f"✓ Format {file_ext.upper()} is supported")
    
    # Get audio metadata
    metadata = get_audio_metadata(filepath)
    result["metadata"] = metadata
    
    if metadata:
        # Check sample rate
        sample_rate = metadata.get('sample_rate')
        if sample_rate:
            if sample_rate in specs["sample_rates"]:
                result["notes"].append(f"✓ Sample rate: {sample_rate} Hz (supported)")
            else:
                result["compatible"] = False
                result["errors"].append(f"Sample rate {sample_rate} Hz is NOT supported")
                supported_rates = ', '.join(map(str, sorted(specs['sample_rates'])))
                result["notes"].append(f"  Supported sample rates: {supported_rates} Hz")
        
        # Check bit depth
        bit_depth = metadata.get('bit_depth')
        if bit_depth:
            if bit_depth in specs["bit_depths"]:
                result["notes"].append(f"✓ Bit depth: {bit_depth}-bit (supported)")
            else:
                if file_ext in ['wav', 'aiff']:  # Only strict for uncompressed formats
                    result["compatible"] = False
                    result["errors"].append(f"Bit depth {bit_depth}-bit is NOT supported")
                    supported_depths = ', '.join(map(str, sorted(specs['bit_depths'])))
                    result["notes"].append(f"  Supported bit depths: {supported_depths}-bit")
                else:
                    result["warnings"].append(f"Bit depth {bit_depth}-bit may not be optimal")
        
        # Check bitrate for MP3
        if file_ext == "mp3":
            bit_rate = metadata.get('bit_rate', 0)
            if bit_rate > 0:
                bitrate_kbps = bit_rate // 1000
                if bitrate_kbps > specs["max_bitrate"]:
                    result["warnings"].append(f"Bitrate {bitrate_kbps} kbps exceeds maximum {specs['max_bitrate']} kbps")
                else:
                    result["notes"].append(f"✓ Bitrate: {bitrate_kbps} kbps (max: {specs['max_bitrate']} kbps)")
        
        # Check channels
        channels = metadata.get('channels')
        if channels:
            if channels <= 2:
                result["notes"].append(f"✓ Channels: {channels} ({'Stereo' if channels == 2 else 'Mono'})")
            else:
                result["warnings"].append(f"File has {channels} channels; CDJs typically support stereo (2 channels)")
        
        # Check duration
        duration = metadata.get('duration', 0)
        if duration > 0:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            result["notes"].append(f"  Duration: {minutes}:{seconds:02d}")
        
        # Check file size
        file_size = metadata.get('file_size', 0)
        if file_size > 0:
            size_mb = file_size / (1024 * 1024)
            result["notes"].append(f"  File size: {size_mb:.1f} MB")
            
            # Warn about FAT32 4GB limit
            if file_size > 4 * 1024 * 1024 * 1024:
                result["warnings"].append("File exceeds 4GB FAT32 limit - use exFAT formatted drive")
    else:
        result["warnings"].append("Could not read audio metadata (ffprobe not available)")
        result["notes"].append("  Install ffmpeg/ffprobe for detailed analysis")
    
    # Storage notes
    storage_options = []
    if specs["usb"]:
        storage_options.append("USB")
    if specs["sd_card"]:
        storage_options.append("SD Card")
    result["notes"].append(f"  Storage options: {', '.join(storage_options)}")
    
    if specs["rekordbox"]:
        result["notes"].append("  ✓ Rekordbox compatible")
    
    return result


def check_all_models(filepath: str) -> Dict[str, Dict]:
    """
    Check file compatibility across all CDJ models.
    
    Args:
        filepath: Path to the audio file
    
    Returns:
        Dictionary mapping model names to compatibility results
    """
    results = {}
    for model in CDJ_MODELS.keys():
        results[model] = check_file_compatibility(filepath, model)
    return results


def scan_directory(directory: str, recursive: bool = False) -> List[str]:
    """
    Scan directory for audio files.
    
    Args:
        directory: Directory path to scan
        recursive: Whether to scan subdirectories
    
    Returns:
        List of audio file paths
    """
    audio_extensions = {'mp3', 'aac', 'wav', 'aiff', 'flac', 'alac', 'm4a', 'ogg', 'wma'}
    audio_files = []
    
    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if get_file_extension(file) in audio_extensions:
                    audio_files.append(os.path.join(root, file))
    else:
        for item in os.listdir(directory):
            filepath = os.path.join(directory, item)
            if os.path.isfile(filepath) and get_file_extension(item) in audio_extensions:
                audio_files.append(filepath)
    
    return sorted(audio_files)


def print_compatibility_matrix(results: Dict[str, Dict]):
    """Print a compatibility matrix showing which models support the file."""
    print("\n" + "="*80)
    print("COMPATIBILITY MATRIX")
    print("="*80)
    
    for model, result in results.items():
        if result.get("error"):
            print(f"\n{model}: ERROR - {result['error']}")
            continue
            
        status = "✓ COMPATIBLE" if result.get("compatible") else "✗ INCOMPATIBLE"
        print(f"\n{model}: {status}")
        
        # Print errors first
        for error in result.get("errors", []):
            print(f"  ✗ {error}")
        
        # Print warnings
        for warning in result.get("warnings", []):
            print(f"  ⚠ {warning}")
        
        # Print notes
        for note in result.get("notes", []):
            print(f"  {note}")


def print_summary(all_results: List[Dict]):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_files = len(all_results)
    if total_files == 0:
        print("No files checked.")
        return
    
    # Count compatible models per file
    for file_results in all_results:
        filepath = next(iter(file_results.values()))["file"]
        compatible_count = sum(1 for r in file_results.values() if r.get("compatible"))
        print(f"\n{os.path.basename(filepath)}:")
        print(f"  Compatible with {compatible_count}/{len(CDJ_MODELS)} models")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check audio file compatibility with Pioneer CDJ models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a single file against all CDJ models
  %(prog)s track.mp3
  
  # Check a file against a specific CDJ model
  %(prog)s track.flac --model CDJ-3000
  
  # Scan a directory for audio files
  %(prog)s /path/to/music --scan
  
  # Scan directory recursively
  %(prog)s /path/to/music --scan --recursive
  
  # List all supported CDJ models
  %(prog)s --list-models
        """
    )
    
    parser.add_argument("path", nargs="?", help="File or directory path to check")
    parser.add_argument("--model", "-m", help="Check against specific CDJ model")
    parser.add_argument("--scan", "-s", action="store_true", help="Scan directory for audio files")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan directories recursively")
    parser.add_argument("--list-models", "-l", action="store_true", help="List all CDJ models and their specs")
    
    args = parser.parse_args()
    
    # List models
    if args.list_models:
        print("\n" + "="*80)
        print("SUPPORTED CDJ MODELS AND SPECIFICATIONS")
        print("="*80)
        for model, specs in CDJ_MODELS.items():
            print(f"\n{model}:")
            print(f"  Formats: {', '.join(sorted(specs['formats'])).upper()}")
            print(f"  Sample rates: {', '.join(map(str, sorted(specs['sample_rates'])))} Hz")
            print(f"  Bit depths: {', '.join(map(str, sorted(specs['bit_depths'])))} bit")
            print(f"  Max MP3 bitrate: {specs['max_bitrate']} kbps")
            print(f"  Rekordbox: {'Yes' if specs['rekordbox'] else 'No'}")
            storage = []
            if specs["usb"]:
                storage.append("USB")
            if specs["sd_card"]:
                storage.append("SD Card")
            print(f"  Storage: {', '.join(storage)}")
        return
    
    if not args.path:
        parser.print_help()
        return
    
    # Scan directory
    if args.scan or os.path.isdir(args.path):
        audio_files = scan_directory(args.path, args.recursive)
        print(f"\nFound {len(audio_files)} audio file(s)")
        
        if not audio_files:
            print("No audio files found.")
            return
        
        all_results = []
        for filepath in audio_files:
            print(f"\n{'='*80}")
            print(f"Checking: {os.path.basename(filepath)}")
            print('='*80)
            
            if args.model:
                result = check_file_compatibility(filepath, args.model)
                print_compatibility_matrix({args.model: result})
            else:
                results = check_all_models(filepath)
                all_results.append(results)
                print_compatibility_matrix(results)
        
        if not args.model and all_results:
            print_summary(all_results)
    
    # Check single file
    elif os.path.isfile(args.path):
        if args.model:
            result = check_file_compatibility(args.path, args.model)
            print_compatibility_matrix({args.model: result})
        else:
            results = check_all_models(args.path)
            print_compatibility_matrix(results)
    else:
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
