from __future__ import division
import requests, time, sys, json

##############
## Settings ##
##############

replace = "no" #change to "yes" if you want it to replace previously bookmarked repos
tags = "github imported-by-script" #max of 100 tags, separated by spaces
skip_limit = 50 # after this many items are skipped, stop importing

pb_token = '' # https://pinboard.in/settings/password
gh_username = ''
gh_token = '' # https://github.com/settings/applications

###############
## Functions ##
###############

if not pb_token or not gh_token:
  print "Login information required"
  sys.exit()

def validate_pb_response(status):
  if status == 200:
    return True
  elif status == 403:
    print "Your Pinboard token didn't seem to work.\nYou should go get it from here: https://pinboard.in/settings/password"
    print "It should look sorta like this: username:XXXXXXXXXXXXXXXXXXXX"
    sys.exit(1)
  elif r_status == 429:
    print "Whoa, Nellie! We're goin' too fast! Hold on, and we'll try again in a moment."
    time.sleep(3) # Pinboard API allows for 1 call every 3 seconds per user.
    return 'retry'
  else:
    return False

def get_current_from_pinboard(pb_token, tags):
  # with open('data.txt', 'r') as file:
  #   return json.load(file)

  payload = {
    'auth_token': pb_token,
    'tag': tags,
    'format': 'json'
  }
  r = requests.get('https://api.pinboard.in/v1/posts/all', params=payload)
  status = validate_pb_response(r.status_code)
  if status == 'retry':
    return get_current_from_pinboard(pb_token, tags)
  elif status:
    bookmarks = json.loads(r.text)
    # with open('data.txt', 'w') as outfile:
    #   json.dump(bookmarks, outfile)
    #   print "done"
    #   sys.exit()
    return bookmarks
  else:
    print "Something went wrong while trying to get bookmarks"
    sys.exit(1)


def post_to_pinboard(pb_token, url, title, long_description, tags, replace):
  payload = {
    'auth_token': pb_token,
    'url': url,
    'description': title,
    'extended': long_description,
    'tags': tags,
    'replace': replace
  }
  r = requests.get('https://api.pinboard.in/v1/posts/add', params=payload)
  status = validate_pb_response(r.status_code)
  if status == 'retry':
    return post_to_pinboard(pb_token, url, title, long_description, tags, replace)
  elif status:
    return 1
  else:
    print "Something went wrong while trying to bookmark " + title + ". I don't know what, but the http status code was " + r_status
    sys.exit(1)


def get_langs(langs_url, gh_token):
  lang_data = requests.get("%s?access_token=%s" % (langs_url, gh_token))
  if lang_data == "{}":
    return None
  lang_data = lang_data.json()
  total_bytes = sum(lang_data.values())
  langs = {}
  for lang,bytes in lang_data.iteritems():
    langs[lang] = round(bytes/total_bytes*100,1)
  return langs



existing = {}
for bookmark in get_current_from_pinboard(pb_token,tags):
  existing[bookmark['href']] = True

print str(len(existing)) + " existing bookmarks found"

page = 1
# Fetches 100 starred repos per page. By default, they are sorted in the order they were starred in
url = 'https://api.github.com/users/' + gh_username + '/starred?per_page=100&page='
stars = []
while True: # iterate through the pages of github starred repos
  r = requests.get(url + str(page) + "&access_token=" + gh_token)
  if r.status_code != 200:
    print "GitHub returned " + str(r.status_code) + " as status code"
    sys.exit(1)
  curr = r.json()
  if not len(curr):
    break
  stars.extend(curr)
  print "Got " + str(len(stars)) + " stars from GitHub so far"
  page+=1




print "Adding your starred repos to Pinboard..."

skip = False # set to True and fill in repo title to skip all repos before it
skip_to = ''
skip_count = 0

count = 0
for star in stars:
  url = star['html_url']

  if url in existing:
    print "Skipping " + url
    skip_count += 1
    if skip_count >= skip_limit:
      print "We've hit the skip limit"
      sys.exit()
    continue

  name = star['name']
  tagline = star['description']

  title = name
  if skip and title != skip_to:
    print "Skipping " + title
    continue;
  skip = False

  if tagline and len(tagline):
    title += ": " + tagline #max 255 characters according to the pinboard api.

  long_description = "Owner: " + star['owner']['login']

  page = star['homepage']
  if not (page == False or page == None or page == "None" or page == "none" or page == ""):
    long_description += "\nHomepage: " + str(page)

  curr_tags = tags

  langs = get_langs(star['languages_url'], gh_token)
  if langs != None:
    langs_str = ''
    for k,v in sorted(langs.iteritems(), key=lambda bytes: bytes[1], reverse=True):
      if v >= 30:
        thislang = k.lower()
        if thislang == 'go':
          thislang = 'golang'
        curr_tags += ' ' + thislang
      if len(langs) > 1:
        langs_str += k+'('+str(v)+'%), '
    if len(langs_str):
      long_description+= "\nLanguages: " + langs_str.strip(' ,') #max 65536 characters according to pinboard api.

  pinboard_add = post_to_pinboard(pb_token, url, title, long_description, curr_tags, replace)
  if pinboard_add == 1:
    print "Pinned " + title
    count +=1

if count == 0:
  print "Whoops. Something went wrong, so we didn't add anything to your Pinboard."
  sys.exit(1)
elif count == 1:
  print "You're all done. You only had one starred repo, so we added that to Pinboard. Go star more repos!"
elif count > 1:
  print "You're all done. All " + str(count) + " repos above have been added to pinboard!"
