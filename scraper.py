#!/usr/bin/python3

import sys
import json
import argparse
import scraper

def main(argv):
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument("--cfg", default="./scraper.json", help="config json file path")
	args = parser.parse_known_args(argv[1:])[0]
	
	config = None
	
	try:
		file = open(args.cfg, "r")
		config = file.read()
		file.close()
		
		config = json.loads(config)
		config = config["scraper"]
	except Exception as err:
		print(
			"Config error! {}: {}".format(err.__class__.__qualname__, err),
			file=sys.stderr
		)
		
		return 1
	
	app = scraper.Scraper(config, argv)
	
	return app.run()

if __name__ == "__main__":
	sys.exit(main(sys.argv))
