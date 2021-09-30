# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Project: sigmacover.py
Date: 30/09/2021
Author: frack113
Version: 1.2b1
Description: 
    get cover of the rules vs backend
Requirements:
    python 3.7 min
    $ pip install ruyaml
Todo:
    - clean code and bug
    - better use of subprocess.run
    - have idea
"""

import re
import subprocess
import pathlib
import ruyaml
import json
import copy
import platform
import argparse

class sigma_class:
    
    def __init__(self):
        self.path_sigmac = "c:/sigma/"
        self.os = platform.system()
        self.backends_lst = []
        self.config_dict = {}

    def get_all_rules(self):
        pass

    def get_all_backend(self):
        options = ["python",self.path_sigmac+"tools/sigmac","-h"]
        info = self.run_sigmac("stdout",options)
        str_list = re.findall("--target {(\S+)}",info.decode())[0]
        self.backends_lst = str_list.split(",")
        self.backends_lst.sort()

    def get_all_config(self):
        configs = pathlib.Path(backends.path_sigmac+"tools/config").glob("*.yml")
        for config in configs:
            with config.open("r",encoding="UTF-8") as file:
                data=ruyaml.safe_load(file)
                if "backends" in data:
                    for name in data["backends"]:
                        self.config_dict[name] = config.name
    
    def run_sigmac (self,info,options):
        if self.os == "Windows":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            ret = subprocess.run(options,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 startupinfo=si
                                 )
        else:
            ret = subprocess.run(options,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 ) 
        if info == "code":
            return ret.returncode
        else:
            return ret.stdout


    def get_sigmac(self,name,config_name):
        infos = []
        options = ["python",
                   self.path_sigmac+"tools/sigmac",
                   "-t",name,
                   "-c",self.path_sigmac+"tools/config/"+config_name,
                   "--debug",
                   "-rI",
                   "-o","dump.txt",
                   self.path_sigmac+"rules"
                   ]
        if self.os == "Windows":
            my_regex = "Convertion Sigma input \S+\\\\(\w+\.yml) (\w+)"
        else:
            my_regex = "Convertion Sigma input \S+/(\w+\.yml) (\w+)"   
        sigmac_code = self.run_sigmac("code",options)
        if not sigmac_code == 0:
            print (f"error {sigmac_code} in sigmac")

        log = pathlib.Path("sigmac.log")
        with log.open() as f:
            lines = f.readlines()
            for line in lines:
                if "Convertion Sigma input" in line:
                    info = re.findall(my_regex,line)[0]
                    infos.append(info)
        log.unlink()
        dump = pathlib.Path("dump.txt")
        if dump.exists():
            dump.unlink()
        return infos     

def update_dict(my_dict,my_data,backend):
    for file,state in my_data:
        my_dict[file][backend] = state

def create_md(data):

    valid = ":heavy_check_mark:"
    not_valid = ":x:"
    dont = ":eight_pointed_black_star:"

    with open ("sigmacover.md","w",encoding="UTF-8") as file:
        first_key = next(iter(data))
        ligne = f"|Rule name|{'|'.join(data[first_key].keys())}\n"
        file.write(ligne)
        nb_backend = len(data[first_key].keys()) + 1 # name rule
        ligne = f"{'|---'*nb_backend}\n"
        file.write(ligne)
        for rule,result in data.items():
            ligne = f"|{rule}|{'|'.join(result.values())}\n"
            ligne = ligne.replace("SUCCESS",valid)
            ligne = ligne.replace("FAILURE",not_valid)
            ligne = ligne.replace("NO TEST",dont)
            file.write(ligne)


print("""
███ ███ ████ █▄┼▄█ ███ ┼┼ ███ ███ █▄█ ███ ███
█▄▄ ┼█┼ █┼▄▄ █┼█┼█ █▄█ ┼┼ █┼┼ █┼█ ███ █▄┼ █▄┼
▄▄█ ▄█▄ █▄▄█ █┼┼┼█ █┼█ ┼┼ ███ █▄█ ┼█┼ █▄▄ █┼█
                  v1.x beta
please wait during the tests
""")
argparser = argparse.ArgumentParser(description="Check Sigma rules with all backend.")
argparser.add_argument("--target", "-t", choices=["yaml","json"], help="Output target format")
cmdargs = argparser.parse_args()

if cmdargs.target == None:
    print("No outpout use -h to see help")
    exit()

backends = sigma_class()
print ("get backend list")
backends.get_all_backend()
print ("get config list")
backends.get_all_config()

#init dict of all rules
default_key_test = {key : "NO TEST" for key in backends.backends_lst}
the_dico ={}
rules = pathlib.Path(backends.path_sigmac+"rules").glob("**/*.yml")
for rule in rules:
    the_dico[rule.name] = copy.deepcopy(default_key_test)

#Check all the backend
for name in backends.backends_lst:
    print (f"check backend : {name}")
    if name in backends.config_dict:
        result = backends.get_sigmac(name,backends.config_dict[name])
    else:
        result = backends.get_sigmac(name,"elk-winlogbeat.yml")
    update_dict(the_dico,result,name)

#Save
if cmdargs.target.lower() == "yaml":
    cover = pathlib.Path("sigmacover.yml")
    with cover.open("w") as file:
        ruyaml.dump(the_dico, file, Dumper=ruyaml.RoundTripDumper)
elif cmdargs.target.lower() == "json" :
    cover = pathlib.Path("sigmacover.json")
    with cover.open("w") as file:
        json_dumps_str = json.dumps(the_dico, indent=4)
        file.write(json_dumps_str)

