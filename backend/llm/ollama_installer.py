"""
Ollama Auto-Installer for Windows
Downloads and installs Ollama + llama3.2:3b model automatically
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/OllamaSetup.exe"
DEFAULT_MODEL = "llama3.2:3b"
INSTALLER_PATH = Path(os.environ.get("TEMP", "C:/Windows/Temp")) / "OllamaSetup.exe"


def is_ollama_installed():
    """Check if Ollama is already installed."""
    try:
        result = subprocess.run(
            ["where", "ollama"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def is_model_available(model: str = DEFAULT_MODEL) -> bool:
    """Check if the specified model is downloaded."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return model in result.stdout
    except:
        return False


def download_ollama_installer(progress_callback=None) -> bool:
    """Download the Ollama installer."""
    try:
        if progress_callback:
            progress_callback("Downloading Ollama installer...", 10)
        
        # Download with progress
        urllib.request.urlretrieve(OLLAMA_DOWNLOAD_URL, INSTALLER_PATH)
        
        if progress_callback:
            progress_callback("Installer downloaded", 30)
        
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def install_ollama_silently(progress_callback=None) -> bool:
    """Install Ollama silently."""
    try:
        if not INSTALLER_PATH.exists():
            if not download_ollama_installer(progress_callback):
                return False
        
        if progress_callback:
            progress_callback("Installing Ollama (this may take a minute)...", 40)
        
        # Run installer silently
        result = subprocess.run(
            [str(INSTALLER_PATH), "/S"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Wait for installation to complete
        time.sleep(5)
        
        if progress_callback:
            progress_callback("Ollama installed", 60)
        
        return True
    except Exception as e:
        print(f"Installation failed: {e}")
        return False


def pull_model(model: str = DEFAULT_MODEL, progress_callback=None) -> bool:
    """Download the specified model."""
    try:
        if progress_callback:
            progress_callback(f"Downloading {model} model (~2GB)...", 70)
        
        # Start model pull
        process = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for completion (this can take several minutes)
        stdout, stderr = process.communicate(timeout=600)
        
        if process.returncode == 0:
            if progress_callback:
                progress_callback(f"Model {model} ready!", 100)
            return True
        else:
            print(f"Model pull failed: {stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Model download timed out (taking too long)")
        return False
    except Exception as e:
        print(f"Model pull failed: {e}")
        return False


def auto_install(progress_callback=None) -> dict:
    """
    Full auto-installation flow.
    Returns status dict with installation results.
    """
    status = {
        "ollama_installed": False,
        "model_ready": False,
        "error": None,
        "message": ""
    }
    
    try:
        # Check if already installed
        if is_ollama_installed():
            status["ollama_installed"] = True
            status["message"] = "Ollama already installed"
            
            # Check model
            if is_model_available():
                status["model_ready"] = True
                status["message"] += ", model ready"
                if progress_callback:
                    progress_callback("Ollama and model already installed!", 100)
                return status
            else:
                # Pull model
                if pull_model(DEFAULT_MODEL, progress_callback):
                    status["model_ready"] = True
                    status["message"] = "Model downloaded successfully"
                else:
                    status["error"] = "Failed to download model"
                return status
        
        # Need to install Ollama
        if progress_callback:
            progress_callback("Starting Ollama installation...", 0)
        
        # Download and install
        if not install_ollama_silently(progress_callback):
            status["error"] = "Failed to install Ollama"
            return status
        
        # Verify installation
        if not is_ollama_installed():
            status["error"] = "Ollama installation verification failed"
            return status
        
        status["ollama_installed"] = True
        
        # Pull model
        if pull_model(DEFAULT_MODEL, progress_callback):
            status["model_ready"] = True
            status["message"] = "Ollama and model installed successfully"
        else:
            status["error"] = "Ollama installed but model download failed"
        
        return status
        
    except Exception as e:
        status["error"] = str(e)
        return status


def get_ollama_status() -> dict:
    """Get current Ollama installation status."""
    return {
        "installed": is_ollama_installed(),
        "model_ready": is_model_available(),
        "model": DEFAULT_MODEL if is_model_available() else None
    }


if __name__ == "__main__":
    # Test the installer
    def print_progress(msg, pct):
        print(f"[{pct}%] {msg}")
    
    result = auto_install(print_progress)
    print(f"\nResult: {result}")
