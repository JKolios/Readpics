#!/usr/bin/python
import reddit
import pickle
import urllib2
import os
import os.path
import time
from string import replace
import codecs
import argparse
import json
import sys
import traceback
from datetime import datetime


def get_link_type(url):
	## -1 = Unknown, 0 = Direct Single Imgur link, 1 = Non-direct Single Imgur link, 
	##  2 = Imgur album, 3 = Direct non-imgur link
		
		if url.find("imgur")!=-1:
			if url.find("i.")!=-1 or url.find(".jpg")!=-1 or url.find(".png")!=-1 or url.find(".gif")!=-1:
				print "Direct single imgur link"
				return 0

			if url.find("/a/")!=-1:
				print "Imgur album"
				return 2
			
			print "Non-direct Single Imgur link"
			return 1
		
		elif url.find(".jpg")!=-1 or url.find(".png")!=-1 or url.find(".gif")!=-1 :
			print "Direct Non-Imgur Link"
			return 3
		else:
			print "Unknown"
			return -1

def get_image(url,dirName):
	origName = url[url.rfind("/")+1:]
	print  "origName:" +origName
	if os.path.exists(os.path.join(dirName,origName))!= True :
		print "downloading " +  origName +" to " +  os.path.join(dirName,origName)
		try:
			imgData = urllib2.urlopen(url).read()
		except:
			print "Error fetching file!"
			return
		try:					
			output = open(os.path.join(dirName,origName),'wb')
			output.write(imgData)
			output.close()
		except:
			print "Error writing to file!"
		#time.sleep(2)
	else:
		print "file exists!"

def parse_album(hash):
	print "Sending API request: " + "http://api.imgur.com/2/album/"+ hash +".json"
	try:
		api_reply =  urllib2.urlopen("http://api.imgur.com/2/album/"+ hash +".json") 
	except :
		print "An HTTP error occured, skiping album"
		return []

	if api_reply.code != 200:
		print "HTTP Error code " + api_reply.code + " returned, skiping album"
		return []
	
	api_json = json.loads(api_reply.read())
	links = []
	print 'parsing album: "' + str(api_json['album']['title']) + '"'
	for image in api_json['album']['images']:
		links.append(image['links']['original']) 
	return links

def parse_image(url):
	try:
		page = urllib2.urlopen(url).read()
	except:
		print " An HTTP exception occured!"
		return None
	
	#titleStart = page.find("<title>")+7
	#imagename = page[titleStart:page.find('</title>',titleStart)]
	#print "parsing image: %s" % imagename
				
	imageURLstart = page.find("image_src")+17
	imageURL = page[imageURLstart:page.find('"',imageURLstart)]
		
	print imageURL
	return imageURL
			
def get_hot_urls(r,num,subreddit):	
	
	print "Getting Image URLs"
	hot = r.get_subreddit(subreddit).get_hot(limit=num)
	print hot
	links = {}
	counter = 0
	
	#f_posts = re.compile(r'.*[[({]+f[]})]+.*',re.I|re.S)	
	for story in hot:
		#print "Checking title:" + story.title.encode('ascii', 'ignore')
		#if f_posts.search(story.title) : 
			#print "Title " + story.title.encode('ascii', 'ignore') + " matches"
			links[str(story.id)] = story.url		
			counter +=1
	
	print "Got " + str(counter) + " URLs"
	return links

def clear_downloaded(links,old_links):

	common = filter(links.has_key, old_links.keys())
	counter = 0
	for key in common:
		  del links[key]
		  counter +=1
	print str(counter) + " already retrieved URLs removed"
	return links
	
def download_url_list(url_list,subdir):
	
	image_dir = os.path.join(os.getcwd(),subdir)
	print "image path:" + image_dir
	if not os.path.exists(image_dir) :
		try:
			print "Creating image directory"
			os.mkdir(image_dir)
		except OSError:
			print "Cannot create image directory"
			quit()
		
	counter = 0

	for url in url_list:
			print "Parsing URL: " + url
			
			link_type = get_link_type(url)
			
			if link_type == 0:
				get_image(url,image_dir)
				counter +=1

			elif link_type == 1:
				url = parse_image(url)
				if url is None:
					continue
				get_image(url,image_dir)
				counter +=1

			elif link_type == 2:
				if url[url.rfind("a/")+2:].rfind("#")!=-1:
					hash = url[url.rfind("a/")+2:url.rfind("#")]
					if hash.rfind("/")!=-1:
						hash = hash[:hash.rfind("/")]
					print hash
				else:
					hash = url[url.rfind("a/")+2:]
					if hash.rfind("/")!=-1:
						hash = hash[:hash.rfind("/")]
						print hash
				image_links = parse_album(hash)
				for link in image_links:
					get_image(link,image_dir)
				counter +=len(image_links)

			elif link_type == 3:
				get_image(url,image_dir)
				counter +=1
			
	return counter

def main():

	parser = argparse.ArgumentParser(description='Download images posted to a subreddit')
	parser.add_argument('subreddit')
	parser.add_argument('-l',action='store_true',help='Log output to ./readpics.log',dest='log')
	parser.add_argument('count',default=100,type=int)
	parser.add_argument('subdir',default='images')	
	args = parser.parse_args()
	
	# Redirect output to log file if requested
	if args.log == True:
		log_filename = os.path.join(os.getcwd(),"log.txt")
		try:
			log_file = open(log_filename, "a")

		except IOError:
			print "Cannot create log file."
			quit()
		sys.stdout = log_file
		print "# LOG ENTRY BEGINS: " + str(datetime.now())



	r = reddit.Reddit(user_agent='readpics')
	
	print('Attempting to get ' + str(args.count) + " top links from subreddit:" + args.subreddit)
	print "\nURL Retrieval\n"
	links = get_hot_urls(r,args.count,args.subreddit)
	
	print "\nGot Comparison\n"
	got_filename = os.path.join(os.getcwd(),"got.bin")
	print "got filename:" + got_filename
	try:
		print "Looking for got file"
		got_file = open(got_filename,"rb")
	
	# Initial run
	except IOError:
		try:
			print "Creating got file"
			got_file = open(got_filename,"wb")
		except IOError:
			print "Cannot create got file."
			if args.log == True:print "# LOG ENTRY ENDS: " + str(datetime.now()) + "\n\n"
			quit()
					
		print 'No previous data detected, assuming initial run'
		pickle.dump(links,got_file)
		got_file.close()

		print "\nParsing and downloading\n"
		print str(download_url_list(links.values(),args.subdir)) + ' files downloaded'
		if args.log == True:print "# LOG ENTRY ENDS: " + str(datetime.now()) + "\n\n"
		quit()


	# Later runs
	print "Loading downloaded URLs from got file"
	old_links = pickle.load(got_file)
	print str(len(old_links)) + " URLs loaded" 
	got_file.close()		
	links_to_get = clear_downloaded(links,old_links)
	if len(links_to_get) <= 0:
		print "No new URLs to retrieve"
		return
	print "\nParsing and downloading\n"
	print str(download_url_list(links_to_get.values(),args.subdir)) + ' files downloaded'
	
	try :
		got_file = open(got_filename,"wb")
	except IOError:
		print "Cannot create output file."
		if args.log == True:print "# LOG ENTRY ENDS: " + str(datetime.now()) + "\n\n"
		quit()	
	
	all_links = dict(old_links.items() + links_to_get.items())
	pickle.dump(all_links,got_file)
	print "Writing " + str(len(all_links)) + " URLs to got file"
	got_file.close()
	if args.log == True:print "# LOG ENTRY ENDS: " + str(datetime.now()) + "\n\n"	

if __name__ == '__main__':
  main()
