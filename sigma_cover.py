# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Project: sigmacover.py
Date: xx/10/2021
Author: frack113
Version: 1.2b1
Description:
    Get cover of the rules vs backend.
Requirements:
    python 3.7 min
    $ pip install ruyaml
Todo:
    - clean code and bug
    - better use of subprocess.run
    - have idea
"""

import argparse
import re
import subprocess
import pathlib
import ruyaml
import platform
import json


class Sigmac:
    def __init__(self, path_sigmac):
        self.path_sigmac = path_sigmac
        self.os = platform.system()
        self.backends_list = []
        self.config_dictionary = {}

    def get_all_rules(self):
        pass

    def get_all_backend(self):
        options = ["python", f"{self.path_sigmac}tools/sigmac", "-h"]

        info = self.run_sigmac("stdout", options)

        FIRST_APPARITION = 0
        string_list = re.findall(r"--target {(\S+)}", info.decode())[FIRST_APPARITION]

        self.backends_list = string_list.split(",")
        self.backends_list.sort()

    def get_all_config(self):
        configs_list = pathlib.Path(f"{self.path_sigmac}tools/config").glob("*.yml")

        for config in configs_list:
            with config.open("r", encoding="UTF-8") as file:
                data = ruyaml.safe_load(file)

                if "backends" in data:
                    for name in data["backends"]:
                        self.config_dictionary[name] = config.name

    def run_sigmac(self, info, options):
        # STARTUPINFO() is need only for windows
        if self.os == "Windows":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(options,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=si
                                   )
        else:
            result = subprocess.run(options,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                   )
        if info == "code":
            return result.returncode

        return result.stdout

    def get_sigmac(self, name, config_name):
        infos = []

        options = [
            "python",
            f"{self.path_sigmac}tools/sigmac",
            "-t", name,
            "-c", f"{self.path_sigmac}tools/config/{config_name}",
            "--debug",
            "-rI",
            "-o", "dump.txt",
            f"{self.path_sigmac}rules",
        ]

        regex_pattern = r"Convertion Sigma input \S+/(\w+\.yml) (\w+)"

        if self.os == "Windows":
            regex_pattern = r"Convertion Sigma input \S+\\(\w+\.yml) (\w+)"
        
        sigmac_code = self.run_sigmac("code", options)
        if sigmac_code != 0:
            print(f"Error {sigmac_code} in sigmac run with {options}")

        sigmac_logs = pathlib.Path("sigmac.log")

        with sigmac_logs.open() as file:
            lines = file.readlines()
            
            for line in lines:
                if "Convertion Sigma input" in line: 
                    FIRST_APPARITION = 0
                    info = re.findall(regex_pattern, line)[FIRST_APPARITION]

                    infos.append(info)

        sigmac_logs.unlink()

        dump = pathlib.Path("dump.txt")
        if dump.exists():
            dump.unlink()

        return infos


def initialise_rules(backends):
    rules = pathlib.Path(f"{backends.path_sigmac}rules").glob("**/*.yml")

    return {
        rule.name: {key: "NO TEST" for key in backends.backends_list} for rule in rules
    }


def check_backends(rules_dictionary, backends):
    def update_dictionary(dictionary, data, backend):
        for file, state in data:
            dictionary[file][backend] = state

    for name in backends.backends_list:
        print(f"Check backend: {name}")

        result = (
            backends.get_sigmac(name, backends.config_dictionary[name])
            if name in backends.config_dictionary
            else backends.get_sigmac(name, "elk-winlogbeat.yml")
        )

        update_dictionary(rules_dictionary, result, name)

    return rules_dictionary


def yml_saving_strategy(rules_dictionary, file):
    ruyaml.dump(rules_dictionary, file, Dumper=ruyaml.RoundTripDumper)


def json_saving_strategy(rules_dictionary, file):
    file.write(json.dumps(rules_dictionary, indent=4))


def no_saving_strategy(rules_dictionary, file):
    pass


def save_results(dictionary,file_extension, saving_strategy):
    cover = pathlib.Path(f"sigmacover.{file_extension}")

    with cover.open("w") as file:
        saving_strategy(dictionary,file)


def main():
    parser = argparse.ArgumentParser(description="Check Sigma rules with all backends.")
    parser.add_argument(
        "--target",
        "-t",
        choices=["yaml", "json"],
        help="This is the output target format.",
    )
    parser.add_argument(
        "--sigma",
        "-s",
        default=str(pathlib.Path().absolute()),
        help="Where is SigmaHQ clone",
    )
    args = parser.parse_args()

    if args.target == None:
        print("No outpout use -h to see help")
        exit()

    backends = Sigmac(path_sigmac=args.sigma)

    print("Get backend and config list")

    backends.get_all_backend()
    backends.get_all_config()

    rules_dictionary = initialise_rules(backends)
    rules_dictionary = check_backends(rules_dictionary, backends)

    TARGET_FORMAT = args.target.lower()

    saving_strategy = no_saving_strategy
    file_extension = ""

    if TARGET_FORMAT == "yaml":
        saving_strategy = yml_saving_strategy
        file_extension = "yml"
    elif TARGET_FORMAT == "json":
        saving_strategy = json_saving_strategy
        file_extension = "json"

    save_results(rules_dictionary,file_extension, saving_strategy)


if __name__ == "__main__":
    print(
        """
███ ███ ████ █▄┼▄█ ███ ┼┼ ███ ███ █▄█ ███ ███
█▄▄ ┼█┼ █┼▄▄ █┼█┼█ █▄█ ┼┼ █┼┼ █┼█ ███ █▄┼ █▄┼
▄▄█ ▄█▄ █▄▄█ █┼┼┼█ █┼█ ┼┼ ███ █▄█ ┼█┼ █▄▄ █┼█
                  v1.x beta
Please wait during the tests...
"""
    )

    main()
