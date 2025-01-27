from setuptools import setup, find_packages
from setuptools.command.install_scripts import install_scripts as _install_scripts
from pathlib import Path
import os

# Custom command to modify the generated script
class CustomInstallScripts(_install_scripts):
    def run(self):
        super().run()  # Run the standard install_scripts command
        # Modify the installed scripts
        for script in self.get_outputs():
            if os.path.basename(script) == "audiocontrol2":
                self.modify_script(script)

    def modify_script(self, script_path):
        # Read the original script
        with open(script_path, "r") as f:
            original_content = f.read()

        # Replace the dynamic entry point resolution with direct import
        custom_content = (
            "#!/usr/bin/python3\n"
            "from ac2.audiocontrol2 import main\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )

        # Write the modified script
        with open(script_path, "w") as f:
            f.write(custom_content)
        print(f"Customized script: {script_path}")

# Your other setup configuration
description = "Tool to handle multiple audio players"
long_description = Path("README.md").read_text() if Path("README.md").exists() else description
from ac2.version import VERSION

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
        "evdev",
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
    cmdclass={"install_scripts": CustomInstallScripts},
)


