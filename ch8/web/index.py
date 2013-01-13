from flask import Flask, render_template, request
import pymongo
import json, pyelasticsearch
import re
import config

# Setup Flask
app = Flask(__name__)

# Setup Mongo
conn = pymongo.Connection() # defaults to localhost
db = conn.agile_data
emails = db['emails']
addresses_per_email = db['adresses_per_email']

# Setup ElasticSearch
elastic = pyelasticsearch.ElasticSearch(config.ELASTIC_URL)

# Controller: Fetch an email and display it
@app.route("/email/<message_id>")
def email(message_id):
  email = emails.find_one({'message_id': message_id})
  addresses = addresses_per_email.find_one({'message_id': message_id})
  print "Addresses: " + addresses
  return render_template('partials/email.html', email=email, addresses=addresses)
  
# Calculate email offsets for fetchig lists of emails from MongoDB
def get_navigation_offsets(offset1, offset2, increment):
  offsets = {}
  offsets['Next'] = {'top_offset': offset2 + increment, 'bottom_offset': offset1 + increment}
  offsets['Previous'] = {'top_offset': max(offset2 - increment, 0), 'bottom_offset': max(offset1 - increment, 0)} # Don't go < 0
  return offsets

# Process elasticsearch hits and return email records
def process_search(results):
  emails = []
  if results['hits'] and results['hits']['hits']:
    hits = results['hits']['hits']
    for hit in hits:
      email = hit['_source']
      emails.append(hit['_source'])
  return emails

# Controller: Fetch a list of emails and display them
@app.route('/')
@app.route('/emails/')
@app.route("/emails/<int:offset1>/<int:offset2>")
def list_emails(offset1 = 0, offset2 = config.EMAILS_PER_PAGE, query=None):
  query = request.args.get('search')
  if query==None:
    email_list = emails.find()[offset1:offset2]
  else:
    results = elastic.search({'query': {'match': { '_all': query}}, 'sort': {'date': {'order': 'desc'}}, 'from': offset1, 'size': config.EMAILS_PER_PAGE}, index="emails")
    print results
    email_list = process_search(results)
  nav_offsets = get_navigation_offsets(offset1, offset2, config.EMAILS_PER_PAGE)
  return render_template('partials/emails.html', emails=email_list, nav_offsets=nav_offsets, nav_path='/emails/', query=query)

# Display all email addresses for a given message

if __name__ == "__main__":
  app.run(debug=True)
