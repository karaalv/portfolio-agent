"""
This module defines server configuration
code for testing, this is used to run and 
close the server during tests.
"""
import os
import signal
import pytest
import subprocess
import time
import requests
from common.utils import TerminalColors

SERVER_PID_FILE = "./server.pid"

def start_server():
    """
    Start the server
    in test mode.
    """
    try:
        print(
            f"{TerminalColors.cyan}"
            f"Starting Portfolio-Agent "
            f"server in test mode...\n"
            f"{TerminalColors.reset}"
        )

        process = subprocess.Popen(
            ["python", "-m", "api.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
            env={**os.environ, "ENVIRONMENT": "test"},
        )

        with open(SERVER_PID_FILE, "w") as f:
            f.write(str(process.pid))

        wait_for_server()
        print(
            f"\n\n"
            f"{TerminalColors.green}"
            f"Portfolio-Agent server started "
            f"successfully in test mode."
            f"{TerminalColors.reset}"
            f"\n"
        )
    except Exception as e:
        print(
            f"{TerminalColors.red}"
            f"Error running testing setup script: "
            f"{TerminalColors.reset}"
            f"{e}"
        )
        pytest.exit("Error running testing setup script")

def stop_server():
    """
    Stop the server.
    """
    try:
        with open(SERVER_PID_FILE, "r") as f:
            pid = int(f.read())
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        os.remove(SERVER_PID_FILE)
    except Exception as e:
        print(
            f"{TerminalColors.red}"
            f"Error stopping testing server: "
            f"{TerminalColors.reset}"
            f"{e}"
        )
        pytest.exit("Error stopping testing server")

def wait_for_server():
    """
    Wait for the server to start
    and be ready to accept requests.
    """
    start_time = time.time()
    while True:
        try:
            url = f"http://127.0.0.1:9001/api/health"
            res = requests.get(url)

            if res.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
    
        if time.time() - start_time > 30:
            print(
                f"{TerminalColors.red}"
                f"Server did not start in 30 seconds"
                f"{TerminalColors.reset}"
            )
            pytest.exit("Server did not start in 30 seconds")

        print(".", end="", flush=True)
        time.sleep(0.3)