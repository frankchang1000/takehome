#!/usr/bin/env python3
"""
SDK to MCP Workflow - Orchestrates the complete process

Usage:
    python workflow.py --repo https://github.com/PyGithub/PyGithub
"""

import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path


def extract_package_name_from_analysis(analysis_path: str) -> str:
    """Extract package name from analysis file using simple regex"""
    if not os.path.exists(analysis_path):
        return "unknown-sdk"
    
    with open(analysis_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex approach - look for "pip install <package>"
    if analysis_path.endswith('.md'):
        install_match = re.search(r'pip install ([a-zA-Z0-9_-]+)', content)
        if install_match:
            package_name = install_match.group(1)
            # Clean up the result
            if 'Main' in package_name:
                package_name = package_name.split('Main')[0]
            if 'Entry' in package_name:
                package_name = package_name.split('Entry')[0]
            if 'Point' in package_name:
                package_name = package_name.split('Point')[0]
            if 'client' in package_name:
                package_name = package_name.split('client')[0]
            return package_name
    
    return "unknown-sdk"


def run_analysis(repo_url: str, verbose: bool = False) -> str:
    """Run the analysis phase and return the path to the summary file"""
    import time
    
    print("🔍 Phase 1: Analyzing SDK...")
    print(f"📦 Repository: {repo_url}")
    
    start_time = time.time()
    cmd = ["python", "main.py", "--repo", repo_url, "--markdown"]
    if verbose:
        cmd.append("--verbose")
        print(f"🚀 Running: {' '.join(cmd)}")
    
    print("⏳ This may take 30-90 seconds for OpenAI analysis...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    analysis_time = time.time() - start_time
    
    if result.returncode != 0:
        print(f"❌ Analysis failed after {analysis_time:.1f}s")
        print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        sys.exit(1)
    
    # Extract SDK name to find the analysis file
    from main import extract_sdk_name
    sdk_name = extract_sdk_name(repo_url)
    analysis_path = f"analysis/{sdk_name}/detailed.md"
    
    if not os.path.exists(analysis_path):
        print(f"❌ Analysis file not found: {analysis_path}")
        sys.exit(1)
    
    print(f"✅ Analysis complete in {analysis_time:.1f}s")
    print(f"📁 Saved to: {analysis_path}")
    return analysis_path


def run_environment_setup(analysis_path: str, verbose: bool = False) -> str:
    """Set up the conda environment and return the environment name"""
    import time
    
    print("🐍 Phase 2: Setting up conda environment...")
    
    # Extract package name from analysis file (supports both JSON and markdown)
    package_name = extract_package_name_from_analysis(analysis_path)
    
    # Clean package name for conda environment (remove special characters, spaces, etc.)
    clean_package_name = re.sub(r'[^a-zA-Z0-9_-]', '-', package_name.lower())
    clean_package_name = re.sub(r'-+', '-', clean_package_name)  # Replace multiple dashes with single dash
    clean_package_name = clean_package_name.strip('-')  # Remove leading/trailing dashes
    env_name = f"mcp-{clean_package_name}"
    print(f"🎯 Target environment: {env_name}")
    
    start_time = time.time()
    cmd = ["python", "agents/environment_agent.py", "--analysis", analysis_path]
    if verbose:
        cmd.append("--verbose")
        print(f"🚀 Running: {' '.join(cmd)}")
    
    print("⏳ Creating conda environment (may take 1-3 minutes)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    setup_time = time.time() - start_time
    
    if result.returncode != 0:
        print(f"❌ Environment setup failed after {setup_time:.1f}s")
        print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        sys.exit(1)
    
    print(f"✅ Environment ready in {setup_time:.1f}s: {env_name}")
    return env_name


def run_code_generation(analysis_path: str, env_name: str, output_dir: str = None, verbose: bool = False) -> str:
    """Generate the MCP server code and return the output directory"""
    import time
    
    print("⚡ Phase 3: Generating FastMCP server...")
    print(f"🎯 Environment: {env_name}")
    
    # Determine output directory
    if output_dir is None:
        # Extract package name from analysis file (supports both JSON and markdown)
        package_name = extract_package_name_from_analysis(analysis_path)
        # Clean package name for directory (remove special characters, spaces, etc.)
        clean_package_name = re.sub(r'[^a-zA-Z0-9_-]', '-', package_name.lower())
        clean_package_name = re.sub(r'-+', '-', clean_package_name)  # Replace multiple dashes with single dash
        clean_package_name = clean_package_name.strip('-')  # Remove leading/trailing dashes
        output_dir = f"output/{clean_package_name}"
    
    print(f"📁 Output directory: {output_dir}")
    
    start_time = time.time()
    cmd = ["python", "agents/developer_agent.py", 
           "--analysis", analysis_path, 
           "--env-name", env_name,
           "--output-dir", output_dir]
    if verbose:
        cmd.append("--verbose")
        print(f"🚀 Running: {' '.join(cmd)}")
    
    print("⏳ Generating server code and configuration files...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    gen_time = time.time() - start_time
    
    if result.returncode != 0:
        print(f"❌ Code generation failed after {gen_time:.1f}s")
        print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        sys.exit(1)
    
    print(f"✅ MCP server generated in {gen_time:.1f}s")
    print(f"📁 Saved to: {output_dir}")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="SDK to MCP Workflow - Complete orchestration")
    parser.add_argument("--repo", required=True, help="Repository URL")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip analysis phase (use existing)")
    parser.add_argument("--skip-environment", action="store_true", help="Skip environment setup")
    parser.add_argument("--output-dir", help="Custom output directory (default: output/{package-name}/)")

    
    args = parser.parse_args()
    
    print("🚀 Starting SDK to MCP conversion workflow...")
    print(f"Repository: {args.repo}")
    print()
    
    # Phase 1: Analysis
    if args.skip_analysis:
        from main import extract_sdk_name
        sdk_name = extract_sdk_name(args.repo)
        # Look for markdown analysis file
        analysis_path = f"analysis/{sdk_name}/detailed.md"
        if not os.path.exists(analysis_path):
            print(f"❌ Analysis file not found: {analysis_path}")
            print(f"💡 Run analysis first: python main.py --repo {args.repo}")
            sys.exit(1)
        print(f"⏭️  Skipping analysis, using: {analysis_path}")
    else:
        analysis_path = run_analysis(args.repo, args.verbose)
    
    # Phase 2: Environment Setup
    if args.skip_environment:
        # Extract package name from analysis file (supports both JSON and markdown)
        package_name = extract_package_name_from_analysis(analysis_path)
        # Clean package name for conda environment (remove special characters, spaces, etc.)
        clean_package_name = re.sub(r'[^a-zA-Z0-9_-]', '-', package_name.lower())
        clean_package_name = re.sub(r'-+', '-', clean_package_name)  # Replace multiple dashes with single dash
        clean_package_name = clean_package_name.strip('-')  # Remove leading/trailing dashes
        env_name = f"mcp-{clean_package_name}"
        print(f"⏭️  Skipping environment setup, using: {env_name}")
    else:
        env_name = run_environment_setup(analysis_path, args.verbose)
    
    # Phase 3: Code Generation
    output_dir = run_code_generation(analysis_path, env_name, args.output_dir, args.verbose)
    
    print()
    print("🎉 Workflow completed successfully!")
    print(f"📁 Analysis: {analysis_path}")
    print(f"🐍 Environment: {env_name}")
    print(f"⚡ MCP Server: {output_dir}")
    print()
    print("Next steps:")
    print(f"1. conda activate {env_name}")
    print(f"2. cd {output_dir}")
    print("3. fastmcp dev server.py")
    

if __name__ == "__main__":
    main()
