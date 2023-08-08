import glob
import subprocess
import logging

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


def kill_players():
    command = "lsof /dev/snd/pcmC*D*p | grep -v COMMAND | awk '{print $2}' | xargs kill"
    run_blocking_command(command)

def kill_kill_players():
    command = "lsof /dev/snd/pcmC*D*p | grep -v COMMAND | awk '{print $2}' | xargs kill -KILL"
    run_blocking_command(command)


def is_alsa_playing():
    hw_params_files = glob.glob('/proc/asound/card*/pcm*/sub*/hw_params')
    
    for file_path in hw_params_files:
        hw_params = get_hw_params(file_path)
        if hw_params is not None:
            if hw_params.strip() != "closed":
                return True

    return False

