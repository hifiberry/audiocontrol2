import glob
import subprocess
import logging
import os


def run_blocking_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing the command: {e}")


def get_hw_params(file_path):
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def kill_player(processname):
    command = "pkill " + processname
    run_blocking_command(command)


def kill_kill_player(processname):
    command = "pkill -KILL " + processname
    run_blocking_command(command)


def is_alsa_playing():
    hw_params_files = glob.glob('/proc/asound/card*/pcm*/sub*/hw_params')

    for file_path in hw_params_files:
        hw_params = get_hw_params(file_path)
        if hw_params is not None:
            if hw_params.strip() != "closed":
                return True

    return False


def active_player():
    # Check if the "active-alsa-processes" script exists, use lsof otherwise
    script_path = "/opt/hifiberry/bin/active-alsa-processes"
    if os.path.exists(script_path):
        command = f"{script_path}"
    else:
        command = "lsof /dev/snd/pcmC*D*p | grep -v COMMAND | awk '{print $1}'"

    procs = []
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        procs = output.splitlines()
    except subprocess.CalledProcessError as e:
        # Handle if the command returns a non-zero exit status
        logging.exception(e)

    procs = [os.path.basename(p) for p in procs]

    return procs[0] if procs else None
