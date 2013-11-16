from __future__ import division
import requests, time, sys

##############
## Settings ##
##############

replace = "no" #change to "yes" if you want it to replace previously bookmarked repos
tags = "github imported-by-script" #max of 100 tags, separated by spaces

pb_token = '' # https://pinboard.in/settings/password
gh_username = ''
gh_token = '' # https://github.com/settings/applications

###############
## Functions ##
###############

if not pb_token or not gh_token:
  print "Login information required"
  sys.exit()


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
  r_status = r.status_code
  if r_status == 200:
    print "Added " + title
    return 1
  elif r_status == 403:
    print "Your Pinboard token didn't seem to work.\nYou should go get it from here: https://pinboard.in/settings/password"
    print "And paste it below.\nIt should look sorta like this: username:XXXXXXXXXXXXXXXXXXXX"
    pb_token = raw_input()
    return post_to_pinboard(pb_token, url, title, long_description, tags, replace)
  elif r_status == 429:
    print "Whoa, Nellie! We're goin' too fast! Hold on, and we'll try again in a moment."
    time.sleep(3) # Pinboard API allows for 1 call every 3 seconds per user.
    return post_to_pinboard(pb_token, url, title, long_description, tags, replace)
  else:
    print "Something went wrong while trying to bookmark " + title + ". I don't know what, but the http status code was " + r_status
    return 0

def get_langs(langs_url, gh_token):
  lang_data = requests.get("%s?access_token=%s" % (langs_url, gh_token))
  if lang_data == "{}":
    return None
  lang_data = lang_data.json
  total_bytes = sum(lang_data.values())
  langs = {}
  for lang,bytes in lang_data.iteritems():
    langs[lang] = round(bytes/total_bytes*100,1)
  return langs




page = 1
url = 'https://api.github.com/users/' + gh_username + '/starred?per_page=100&page=' # Fetches 100 starred repos per page
stars = []
while True: # iterate through the pages of github starred repos
  r = requests.get(url + str(page) + "&access_token=" + gh_token)
  if r.status_code != 200:
    print "GitHub returned " + str(r.status_code) + " as status code"
    sys.exit()
  curr = r.json
  if not len(curr):
    break
  stars.extend(curr)
  print "Got " + str(len(stars)) + " stars from GitHub so far"
  page+=1




print "Adding your starred repos to Pinboard..."

skip = False # set to True and fill in repo title to skip all repos before it
skip_to = ''


count = 0
for item in range(len(stars)):
  url = stars[item]['html_url']
  name = stars[item]['name']
  tagline = stars[item]['description']

  title = name
  if skip and title != skip_to:
    print "Skipping " + title
    continue;
  skip = False

  if tagline and len(tagline):
    title += ": " + tagline #max 255 characters according to the pinboard api.

  long_description = "Owner: " + stars[item]['owner']['login']

  page = stars[item]['homepage']
  if not (page == False or page == None or page == "None" or page == "none" or page == ""):
    long_description += "\nHomepage: " + str(page)

  curr_tags = tags

  langs = get_langs(stars[item]['languages_url'], gh_token)
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
    count +=1

if count == 0:
  print "Whoops. Something went wrong, so we didn't add anything to your Pinboard."
elif count == 1:
  print "You're all done. You only had one starred repo, so we added that to Pinboard. Go star more repos!"
elif count > 1:
  print "You're all done. All " + str(count) + " repos above have been added to pinboard!"