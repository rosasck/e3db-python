
import e3db
import sys
import os
import json
from e3db.types import Search

# $ python3 winner.py round=1 tozny-client-credentials-filepath=./bruce_creds.json

if len(sys.argv) != 3 :
    sys.exit("Incorrect Arguments:\n python3 winner.py [round] [client-credentials]")


#Look up up bruces results from round and output who won 


file = open(sys.argv[2], "r")

client_json = json.loads(file.read())

client_name=client_json["name"]

if client_name == 'Alicia' or client_name == 'alicia' or client_name == 'Clarence' or client_name == 'clarence' or client_name == 'Bruce' or client_name == 'bruce'  :
    print("Verified Permissions")
else :
    print(sys.argv[2])
    sys.exit("Permisions not valid")


credentials_path= sys.argv[2]
if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))



file.close

round= sys.argv[1]

query= Search(include_data=True).match(record_types=['rps_winner'])
results = client.search(query)

for record in results:
    full_name = "Winner Name: {0} ".format(record.data['name'])
    print ("{0} --- Round: {1}".format(full_name, record.data['round']))

