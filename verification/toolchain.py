"""Pinned TLC dependency; Java can come from JAVA, PATH, or the local cache."""
import hashlib
import os
from pathlib import Path
import shutil
import urllib.request

CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "bend-window-capture-verification"
TLC_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
TLC_URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"


def resolve():
    CACHE.mkdir(parents=True, exist_ok=True)
    jar = Path(os.environ.get("TLA2TOOLS", CACHE / "tla2tools-1.7.4.jar"))
    if not jar.exists():
        data = urllib.request.urlopen(TLC_URL, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != TLC_SHA256:
            raise RuntimeError("TLC download checksum mismatch")
        jar.write_bytes(data)
    if hashlib.sha256(jar.read_bytes()).hexdigest() != TLC_SHA256:
        raise RuntimeError("TLA2TOOLS must be the pinned TLC 1.7.4 jar")
    java = os.environ.get("JAVA") or shutil.which("java")
    if not java and (CACHE / "java/bin/java").is_file():
        java = str(CACHE / "java/bin/java")
    if not java:
        raise RuntimeError("Install Java 11 or newer (validated with Temurin 21.0.8+9), or set JAVA to its binary")
    return java, jar
