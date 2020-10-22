
import e3db
import sys
import os 
import json
from e3db.types import Search


#$ python3 judge.py round=1 tozny-client-credentials-filepath=./clarence_creds.json

#this file is only able to be opened by judge clarence or alicia for any move 

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



credentials_path= sys.argv[2]
if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))



file.close


#write a query to grab what alice and clarence have in the data storage 

round= sys.argv[1]

query= Search(include_data=True).match(record_types=['rps_move'])
results = client.search(query)

for record in results:
    full_name = "Name: {0} --- Move: {1}".format(record.data['name'], record.data['move'])
    print ("{0} --- Round: {1}".format(full_name, record.data['round']))



alice_play= 'rock'
bruce_play='paper'

'''
record_type = 'rps_winner'



if(alice_play == 'rock' and bruce_play == 'rock'):
    data = {
    'name': 'Tie',
    'round': sys.argv[1],
    }
elif(alice_play == 'rock' and bruce_play == 'paper'):
    data = {
    'name': 'Alicia',
    'round': sys.argv[1],
    }
elif(alice_play == 'rock' and bruce_play == 'scissors'):
    data = {
    'name': 'Alicia',
    'round': sys.argv[1],
    }
elif(alice_play == 'paper' and bruce_play == 'rock'):
    data = {
    'name': "Bruce",
    'round': sys.argv[1],
    }   
elif(alice_play == 'paper' and bruce_play == 'paper'):
    data = {
    'name': "Tie",
    'round': sys.argv[1],
    }
elif(alice_play == 'paper' and bruce_play == 'scissors'):
    data = {
    'name': "Bruce",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and bruce_play == 'rock'):
    data = {
    'name': "Bruce",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and bruce_play == 'paper'):
    data = {
    'name': "Alicia",
    'round': sys.argv[1],
    }
elif(alice_play == 'scissors' and bruce_play == 'scissors'):
    data = {
    'name': "Tie",
    'round': sys.argv[1],
    }
else:
    print("Invalid or Incomplete Data")


record = client.write(record_type, data)
print ('Wrote record ID {0}'.format(record.meta.record_id))
'''