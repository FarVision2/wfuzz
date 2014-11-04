import sys
import getopt
import time
import re
from collections import defaultdict

from framework.fuzzer.filter import PYPARSING
from framework.core.facade import Facade
from framework.core.myexception import FuzzException
from framework.ui.console.common import help_banner
from framework.ui.console.common import usage
from framework.ui.console.common import brief_usage
from framework.ui.console.common import version
from framework.ui.console.output import table_print

class CLParser:
    def __init__(self, argv):
	self.argv = argv

    def show_brief_usage(self):
	print help_banner
	print brief_usage

    def show_usage(self):
	print help_banner
	print usage

    def show_plugins_help(self, registrant, cols=3, category="$all$"):
	print "\nAvailable %s:\n" % registrant
	table_print(map(lambda x: x[cols:], Facade().proxy(registrant).get_plugins_ext(category)))
	sys.exit(0)

    def parse_cl(self):
	# Usage and command line help
	try:
	    opts, args = getopt.getopt(self.argv[1:], "hAZIXvcb:e:R:d:z:r:f:t:w:V:H:m:o:s:p:w:",['req-delay=','conn-delay=','sc=','sh=','sl=','sw=','ss=','hc=','hh=','hl=','hw=','hs=','ntlm=','basic=','digest=','follow','script-help=','script=','script-args=','filter=','interact','help','version'])
	    optsd = defaultdict(list)
	    for i,j in opts:
		optsd[i].append(j)

	    self._parse_help_opt(optsd)

	    if len(args) == 0:
		raise FuzzException(FuzzException.FATAL, "You must specify a payload and a URL")

	    url = args[0]

	    self._check_options(optsd)

	    options = dict(
		conn_options = self._parse_conn_options(optsd),
		filter_options = self._parse_filters(optsd),
		seed_options = self._parse_seed(url, optsd),
		payload_options = self._parse_payload(optsd),
		grl_options = self._parse_options(optsd),
		script_options = self._parse_scripts(optsd),
	    )

	    return options
	except FuzzException, e:
	    self.show_brief_usage()
	    #self.show_usage()
	    raise e
	except ValueError:
	    self.show_brief_usage()
	    raise FuzzException(FuzzException.FATAL, "Incorrect options, please check help.")
	except getopt.GetoptError, qw:
	    self.show_brief_usage()
	    #self.show_usage()
	    raise FuzzException(FuzzException.FATAL, "%s." % str(qw))

    def _parse_help_opt(self, optsd):
	if "--version" in optsd:
	    print version
	    sys.exit(0)

	if "--help" in optsd or "-h" in optsd:
	    self.show_usage()
	    sys.exit(0)

	# Extensions help
	if "--script-help" in optsd:
	    script_string = optsd["--script-help"][0]
	    if script_string == "":
		script_string = "$all$"

	    self.show_plugins_help("parsers", 2, script_string)

	if "-e" in optsd:
	    if "payloads" in optsd["-e"]:
		self.show_plugins_help("payloads")
	    elif "encoders" in optsd["-e"]:
		self.show_plugins_help("encoders", 2)
	    elif "iterators" in optsd["-e"]:
		self.show_plugins_help("iterators")
	    elif "printers" in optsd["-e"]:
		self.show_plugins_help("printers")
	    elif "scripts" in optsd["-e"]:
		self.show_plugins_help("parsers", 2)
	    else:
		raise FuzzException(FuzzException.FATAL, "Unknown category. Valid values are: payloads, encoders, iterators, printers or scripts.")

	if "-o" in optsd:
	    if "help" in optsd["-o"]:
		self.show_plugins_help("printers")
	if "-m" in optsd:
	    if "help" in optsd["-m"]:
		self.show_plugins_help("iterators")
	if "-z" in optsd:
	    if "help" in optsd["-z"]:
		self.show_plugins_help("payloads")


    def _check_options(self, optsd):
	if not "-z" in optsd.keys() and not "-w" in optsd.keys():
	    raise FuzzException(FuzzException.FATAL, "Bad usage: You must specify a payload.")

	if "--filter" in optsd.keys() and filter(lambda x: x in optsd.keys(), ["--sc","--ss","--sh","--sl","--sw","--hc","--hs","--hh","--hl","--hw"]):
	    raise FuzzException(FuzzException.FATAL, "Bad usage: Advanced and filter flags are mutually exclusive. Only one could be specified.")

	# Check for repeated flags
	l = ["--hc", "--hw", "--hl", "--hh", "--hs", "--sc", "--sw", "--sl", "--sh", "--ss", "--script", "--script-args"]
	if [i for i in l if i in optsd and len(optsd[i]) > 1]:
	    raise FuzzException(FuzzException.FATAL, "Bad usage: Only one filter could be specified at the same time.")

	#HEAD with POST parameters
	if "-d" in optsd.keys() and "-I" in optsd.keys():
	    raise FuzzException(FuzzException.FATAL, "Bad usage: HEAD with POST parameters? Does it makes sense?")

	#-A and script not allowed at the same time
	if "--script" in optsd.keys() and "-A" in optsd.keys():
	    raise FuzzException(FuzzException.FATAL, "Bad usage: --scripts and -A are incompatible options, -A already defines --script=default.")


    def _parse_filters(self, optsd):
	filter_params = dict(
	    active = False,
	    regex_show = None,
	    codes_show = None,
	    codes = [],
	    words = [],
	    lines = [],
	    chars = [],
	    regex = None,
	    filter_string = ""
	    )


	if "--filter" in optsd:
	    if not PYPARSING:
		raise FuzzException(FuzzException.FATAL, "--filter switch needs pyparsing module.")
	    filter_params['filter_string'] = optsd["--filter"][0]

	if "--hc" in optsd:
	    filter_params['codes'] = optsd["--hc"][0].split(",")
	if "--hw" in optsd:
	    filter_params['words'] = optsd["--hw"][0].split(",")
	if "--hl" in optsd:
	    filter_params['lines'] = optsd["--hl"][0].split(",")
	if "--hh" in optsd:
	    filter_params['chars'] = optsd["--hh"][0].split(",")
	if "--hs" in optsd:
	    filter_params['regex'] = re.compile(optsd["--hs"][0], re.MULTILINE|re.DOTALL)

	if filter(lambda x: x in optsd, ["--ss"]):
	    filter_params['regex_show'] = True
	elif filter(lambda x: x in optsd, ["--hs"]):
	    filter_params['regex_show'] = False

	if filter(lambda x: x in optsd, ["--sc", "--sw", "--sh", "--sl"]):
	    filter_params['codes_show'] = True
	elif filter(lambda x: x in optsd, ["--hc", "--hw", "--hh", "--hl"]):
	    filter_params['codes_show'] = False

	if "--sc" in optsd:
	    filter_params['codes'] = optsd["--sc"][0].split(",")
	if "--sw" in optsd:
	    filter_params['words'] = optsd["--sw"][0].split(",")
	if "--sl" in optsd:
	    filter_params['lines'] = optsd["--sl"][0].split(",")
	if "--sh" in optsd:
	    filter_params['chars'] = optsd["--sh"][0].split(",")
	if "--ss" in optsd:
	    filter_params['regex'] = re.compile(optsd["--ss"][0], re.MULTILINE|re.DOTALL)

	if filter_params['regex_show'] is not None or filter_params['codes_show'] is not None or filter_params['filter_string'] != "":
	    filter_params['active'] = True

	return filter_params

    def _parse_payload(self, optsd):
	options = dict(
	    payloads = [],
	    iterator = None,
	)

	if "-z" in optsd:
	    for i in optsd["-z"]:
		vals = i.split(",")
		name, params = vals[:2]

		encoders = None
		if len(vals) == 3:
		    encoders = vals[2].split("-")

		options["payloads"].append((name, params, encoders))

	# Alias por "-z file,Wordlist"
	if "-w" in optsd:
	    for i in optsd["-w"]:
		vals = i.split(",")
		f, = vals[:1]

		encoders = None
		if len(vals) == 2:
		    encoders = vals[1].split("-")

		options["payloads"].append(("file", f, encoders))

	if "-m" in optsd:
	    options["iterator"] = optsd['-m'][0]
	elif len(options["payloads"]) > 1:
	    options["iterator"] = "product"
	else:
	    options["iterator"] = None

	return options


    def _parse_seed(self, url, optsd):
	options = dict(
	    url = url,
	    fuzz_methods = False,
	    auth = (None, None),
	    follow = False,
	    head = False,
	    postdata = None,
	    extraheaders = None,
	    cookie = None,
	    allvars = None,
	)

	options['url'] = url

	if "-X" in optsd:
	    options['fuzz_methods'] = True

	if "--basic" in optsd:
	    options['auth'] = ("basic", optsd["--basic"][0])

	if "--digest" in optsd:
	    options['auth'] = ("digest", optsd["--digest"][0])

	if "--ntlm" in optsd:
	    options['auth'] = ("ntlm", optsd["--ntlm"][0])

	if "--follow" in optsd:
	    options['follow'] = True

	if "-I" in optsd:
	    options['head'] = "HEAD"

	if "-d" in optsd:
	    options['postdata'] = optsd["-d"][0]

	if "-b" in optsd:
	    options['cookie'] = optsd["-b"][0]

	if "-H" in optsd:
	    options['extraheaders'] = str(optsd["-H"][0])

	if "-V" in optsd:
	    varset = str(optsd["-V"][0])
            if varset not in ['allvars','allpost','allheaders']: 
                raise FuzzException(FuzzException.FATAL, "Incorrect all parameters brute forcing type specified, correct values are allvars,allpost or allheaders.")

	    options['allvars'] = varset

	return options

    def _parse_conn_options(self, optsd):
	conn_options = dict(
	    proxy_list = None,
	    max_conn_delay = 90,
	    max_req_delay = None,
	    rlevel = 0,
	    scanmode = False,
	    sleeper = None,
	    max_concurrent = 10,
	)
	
	if "-p" in optsd:
	    proxy = []

	    for p in optsd["-p"][0].split('-'):
		vals = p.split(":")

		if len(vals) == 2:
		    proxy.append((vals[0], vals[1], "HTML"))
		elif len(vals) == 3:
		    if vals[2] not in ("SOCKS5","SOCKS4","HTML"):
			raise FuzzException(FuzzException.FATAL, "Bad proxy type specified, correct values are HTML, SOCKS4 or SOCKS5.")
		    proxy.append((vals[0], vals[1], vals[2]))
		else:
		    raise FuzzException(FuzzException.FATAL, "Bad proxy parameter specified.")

	    conn_options['proxy_list'] = proxy

	if "--conn-delay" in optsd:
	    conn_options['max_conn_delay'] = int(optsd["--conn-delay"][0])

	if "--req-delay" in optsd:
	    conn_options["max_req_delay"] = int(optsd["--req-delay"][0])

	if "-R" in optsd:
	    conn_options["rlevel"] = int(optsd["-R"][0])

	conn_options["scanmode"] = "-Z" in optsd

	if "-s" in optsd:
	    conn_options["sleeper"] = float(optsd["-s"][0])

	if "-t" in optsd:
	    conn_options["max_concurrent"] = int(optsd["-t"][0])

	return conn_options

    def _parse_options(self, optsd):
	options = dict(
	    printer_tool = "default",
	    colour = False,
	    interactive = False,
	)
	
	if "-v" in optsd:
	    options["printer_tool"] = "verbose"

	options["colour"] = "-c" in optsd

	if "-A" in optsd:
	    options["printer_tool"] = "verbose"
	    options["colour"] = True

	if "-o" in optsd:
	    options["printer_tool"] = optsd['-o'][0]

	options["interactive"] = "--interact" in optsd

	return options

    def _parse_scripts(self, optsd):
	options = dict(
	    script_string = "",
	    script_args = [],
	)

	if "-A" in optsd:
	    options["script_string"] = "default"

	if "--script" in optsd:
	    options["script_string"] = "default" if optsd["--script"][0] == "" else optsd["--script"][0]

	if "--script-args" in optsd:
	    options['script_args'] = map(lambda x: x.split("=", 1), optsd["--script-args"][0].split(","))

	return options