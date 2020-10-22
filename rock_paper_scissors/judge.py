#Imports needed for this document 
import e3db
import sys
import os 
import json
from e3db.types import Search


#$ python3 judge.py round=1 tozny-client-credentials-filepath=./clarence_creds.json


if len(sys.argv) != 3 :
    sys.exit("Incorrect Arguments:\n python3 play.py [round] [client-credentials]")


file = open(sys.argv[2], "r")

client_json = json.loads(file.read())

client_name=client_json["name"]

if client_name == 'Alicia' or client_name == 'alicia' or client_name == 'Clarence' or client_name == 'clarence' :
    print("Verified Permissions")
else :
    print(sys.argv[2])
    sys.exit("Permisions not valid")


credentials_path= './alice_cred.json'
credentials_path2= './bruce_cred.json'
credentials_path3= './clarence_cred.json'

if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))

if os.path.exists(credentials_path2):
    client2 = e3db.Client(json.load(open(credentials_path2)))

if os.path.exists(credentials_path3):
    client3 = e3db.Client(json.load(open(credentials_path3)))


file.close


#write a query to grab what alice and clarence have in the data storage 

round= sys.argv[1]

query= Search(include_data=True).match(record_types=['rps_move'])
results = client.search(query)
results2= client2.search(query)
bruce_play= "null"
alice_play="null"

#take the last entry incase alicia enters more than one
for record in results:
    if record.data['round'] == round:
        if record.data['name'] == 'Alicia' or record.data['name'] == 'Alicia' :
           alice_play= record.data['move']


for record in results2:
    if record.data['round'] == round:
        if record.data['name'] == 'Bruce' or record.data['name'] == 'bruce': 
           bruce_play= record.data['move']

    #full_name = "Name: {0} --- Move: {1}".format(record.data['name'], record.data['move'])
    #print ("{0} --- Round: {1}".format(full_name, record.data['round']))



if(alice_play == 'rock' and bruce_play == 'rock'):
    record_type='rps_winner'
    data = {
    'name': 'Tie',
    'round': sys.argv[1],
    }
elif(alice_play == 'rock' and bruce_play == 'paper'):
    record_type='rps_winner'
    data = {
    'name': 'Alicia',
    'round': sys.argv[1],
    }
elif(alice_play == 'rock' and bruce_play == 'scissors'):
    record_type='rps_winner'
    data = {
    'name': 'Alicia',
    'round': sys.argv[1],
    }
elif(alice_play == 'paper' and bruce_play == 'rock'):
    record_type='rps_winner'
    data = {
    'name': "Bruce",
    'round': sys.argv[1],
    }   
elif(alice_play == 'paper' and bruce_play == 'paper'):
    record_type='rps_winner'
    data = {
    'name': "Tie",
    'round': sys.argv[1],
    }
elif(alice_play == 'paper' and bruce_play == 'scissors'):
    record_type='rps_winner'
    data = {
    'name': "Bruce",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and bruce_play == 'rock'):
    record_type='rps_winner'
    data = {
    'name': "Bruce",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and bruce_play == 'paper'):
    record_type='rps_winner'
    data = {
    'name': "Alicia",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and bruce_play == 'scissors'):
    record_type='rps_winner'
    data = {
    'name': "Tie",
    'round': sys.argv[1],
    }
else:
    print("Invalid or Incomplete Data")


record = client3.write(record_type, data)
print ('Wrote record ID {0}'.format(record.meta.record_id))


# Read that record back from the server and print the name
record2 = client3.read(record.meta.record_id)
print ('Round "{0}" '.format(record2.data['round']), ' Winner {0} Submitted!'.format(record2.data['name']))
