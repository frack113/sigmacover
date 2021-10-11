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
import sqlite3

class Rule:
    """ for the rule information"""
    def __init__(self, sql_cursor):
        self.sql_cursor = sql_cursor
        self.sql_cursor.execute('DROP TABLE IF EXISTS rules;')
        self.sql_cursor.execute('CREATE TABLE rules(id,name);')

    def insert_rule(self,data):
        self.sql_cursor.execute(f'INSERT INTO rules VALUES ("{data[0]}","{data[1]}");')

    def get_all_rule_name(self):
        self.sql_cursor.execute('SELECT name FROM rules;')
        return self.sql_cursor.fetchall()
    
    def load_all_rules(self,path):
        yaml_files = pathlib.Path(f"{path}rules").glob("**/*.yml")
        for yaml_file in yaml_files:
            with yaml_file.open('r',encoding="UTF-8") as file:
                yaml = ruyaml.load(file,Loader=ruyaml.Loader)
                uuid = yaml["id"]
                name = yaml_file.name
                self.insert_rule([uuid,name])
                
    def create_test_table(self,data):
        str_field = ','.join(data)
        str_field = str_field.replace("-","_")
        self.sql_cursor.execute('DROP TABLE IF EXISTS test;')
        self.sql_cursor.execute(f'CREATE TABLE test(name,{str_field});')
        empty = ',"NO TEST"'*len(data)
        for name in self.get_all_rule_name():
            self.sql_cursor.execute(f'INSERT INTO test VALUES("{name}"{empty});')

    def update_test_table(self,data):
        str_rule_name = data[0]
        str_field_name = data[1].replace("-","_")
        status = data[2]
        self.sql_cursor.execute(f'UPDATE test SET {str_field_name}="{status}" WHERE name="{str_rule_name}";')

    def get_all_test(self):
        self.sql_cursor.execute('SELECT * FROM test;')
        return self.sql_cursor.fetchall()
        
class Backend:
    """ for the backend information"""
    def __init__(self, sql_cursor):
        self.sql_cursor = sql_cursor
        self.sql_cursor.execute('DROP TABLE IF EXISTS backends;')
        self.sql_cursor.execute('CREATE TABLE backends(name,config);')

    def insert_backend(self,data):
        self.sql_cursor.execute(f'INSERT INTO backends VALUES ("{data[0]}","{data[1]}");')
        
    def select_backend(self,data):
        pass
    
class Sigmac:
    """ for interact with sigmac """
    def __init__(self, path_sigmac):
        self.path_sigmac = path_sigmac
        self.os = platform.system()

    def get_all_backend(self):
        options = ["python", f"{self.path_sigmac}tools/sigmac", "-h"]

        info = self.run_sigmac("stdout", options)

        FIRST_APPARITION = 0
        string_list = re.findall(r"--target {(\S+)}", info.decode())[FIRST_APPARITION]

        backends_list = string_list.split(",")
        backends_list.sort()
        return backends_list

    def get_all_config(self):
        configs_list = pathlib.Path(f"{self.path_sigmac}tools/config").glob("*.yml")
        config_dictionary = {}
        for config in configs_list:
            with config.open("r", encoding="UTF-8") as file:
                data = ruyaml.safe_load(file)

                if "backends" in data:
                    for name in data["backends"]:
                        config_dictionary[name] = config.name
        return config_dictionary

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


def yml_saving_strategy(rules_list, file):
    ruyaml.dump(rules_list, file, Dumper=ruyaml.RoundTripDumper)


def json_saving_strategy(rules_list, file):
    file.write(json.dumps(rules_list, indent=4))


def no_saving_strategy(rules_list, file):
    pass


def save_results(rules_list,file_extension, saving_strategy):
    cover = pathlib.Path(f"sigmacover.{file_extension}")

    with cover.open("w") as file:
        saving_strategy(rules_list,file)


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

    con = sqlite3.connect('example.db')
    cur = con.cursor()
    
    rules = Rule(sql_cursor=cur)
    backends = Backend(sql_cursor=cur)
    sigma_cmd = Sigmac(path_sigmac=args.sigma)

    #get all rule
    rules.load_all_rules(args.sigma)

    #get the correct config name
    config_dict = sigma_cmd.get_all_config()

    
    #get all backends name
    all_backend = sigma_cmd.get_all_backend()

    #create result test table
    rules.create_test_table(all_backend)
    
    for name in all_backend:
        print(f"Checking backend: {name}")
        config_name = config_dict[name] if name in config_dict else "elk-winlogbeat.yml"
        backends.insert_backend([name,config_name])
        # test backend
        results = sigma_cmd.get_sigmac(name, config_name)
        for rule_name,status in results:
            rules.update_test_table([rule_name,name,status])

    #save result  
    con.commit()


    TARGET_FORMAT = args.target.lower()

    saving_strategy = no_saving_strategy
    file_extension = ""

    if TARGET_FORMAT == "yaml":
        saving_strategy = yml_saving_strategy
        file_extension = "yml"
    elif TARGET_FORMAT == "json":
        saving_strategy = json_saving_strategy
        file_extension = "json"

    save_results(rules.get_all_test(),file_extension, saving_strategy)

    con.close()

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
