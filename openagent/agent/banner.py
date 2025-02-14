import pyfiglet
import time


def print_banner():
    """Print the OpenAgent ASCII banner"""
    banner = pyfiglet.figlet_format("OpenAgent", font="slant")
    version = "v0.2.0"
    print(banner)
    print(f"{' ' * 45}version {version}", flush=True)
    time.sleep(0.1)
