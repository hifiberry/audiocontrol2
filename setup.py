from setuptools import setup, find_packages, Command
from pathlib import Path
import os
import shutil
from ac2.version import VERSION

# Disable pybuild tests via environment variables
os.environ["PYBUILD_DISABLE_python3"] = "unittest"  # Disable unittest in pybuild
os.environ["DEB_BUILD_OPTIONS"] = "nocheck"  # Pass nocheck to disable testing globally

# Systemd service file content
systemd_service_content = """[Unit]
Description=Audio Control 2 Service
After=network.target pipewire-system.service

[Service]
ExecStart=/usr/bin/audiocontrol2
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
"""

class NoTestCommand(Command):
    """A no-op test command."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print("Skipping tests.")


class PostInstallCommand(Command):
    """Post-installation setup for systemd service and configuration files."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Systemd service setup
        systemd_path = "/etc/systemd/system/audiocontrol2.service"
        try:
            with open(systemd_path, "w") as f:
                f.write(systemd_service_content)
            print(f"Systemd service file written to {systemd_path}")
            os.system("systemctl daemon-reload")
            os.system("systemctl enable audiocontrol2.service")
        except PermissionError:
            print("Permission denied: Run as root to install the systemd service.")

        # Configuration file setup
        conf_default_src = "audiocontrol2.conf.default"  # Ensure this file exists in your source distribution
        conf_default_dest = "/etc/audiocontrol2.conf.default"
        conf_dest = "/etc/audiocontrol2.conf"

        try:
            # Copy the default configuration file
            if os.path.exists(conf_default_src):
                shutil.copyfile(conf_default_src, conf_default_dest)
                print(f"Copied default configuration to {conf_default_dest}")

            # Copy to /etc/audiocontrol2.conf if it doesn't already exist
            if not os.path.exists(conf_dest):
                shutil.copyfile(conf_default_src, conf_dest)
                print(f"Copied default configuration to {conf_dest} (as the main configuration).")
            else:
                print(f"Configuration file {conf_dest} already exists; skipping.")
        except PermissionError:
            print("Permission denied: Run as root to copy configuration files.")
        except FileNotFoundError as e:
            print(f"Error: {e}")


description = "Tool to handle multiple audio players"
long_description = Path("README.md").read_text() if Path("README.md").exists() else description

setup(
    name="audiocontrol2",
    version=VERSION,
    description=description,
    long_description=long_description,
    author="HiFiBerry",
    author_email="support@hifiberry.com",
    url="https://github.com/hifiberry/audiocontrol2",
    packages=find_packages(),
    install_requires=[
        "gevent",
        "gevent-websocket",
        "socketio",
        "bottle",
        "expiringdict",
        "musicbrainzngs",
        "mpd",
        "dbus",
        "pylast",
        "usagecollector",
        "netifaces",
        "requests",
        "evdev"
    ],
    entry_points={
        "console_scripts": [
            "audiocontrol2=ac2.audiocontrol2:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    include_package_data=True,
    package_data={
        "ac2": ["data/*"],  # Include additional package data here.
    },
    cmdclass={
        "test": NoTestCommand,  # Disable tests
        "post_install": PostInstallCommand,  # Enable post-install commands
    },
)

