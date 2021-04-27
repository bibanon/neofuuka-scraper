#!/usr/bin/python3

import sys
import json
import scraper

CONFIG = "./scraper.json"

def main(argv):
	config = None
	
	try:
		file = open(CONFIG, "r")
		
		config = file.read()
		
		file.close()
		
		config = json.loads(config)
		config = config["scraper"]
	except:
		print("Config syntax error!")
		return 1
	
	app = scraper.Scraper(config, argv)
	
	return app.run()

if __name__ == "__main__":
	sys.exit(main(sys.argv))
