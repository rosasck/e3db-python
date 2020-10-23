#Imports needed for this document 
import e3db
import sys
import os 
import json
from e3db.types import Search

#Example command line arguments given by Levi:
#$ python3 judge.py round=1 tozny-client-credentials-filepath=./clarence_creds.json


#Argument Checker to make sure we have all we need from user 
if len(sys.argv) != 3 :
    sys.exit("Incorrect Arguments:\n python3 play.py [round] [client-credentials]")



#File opening to grab user 
file = open(sys.argv[2], "r")

client_json = json.loads(file.read())

client_name=client_json["name"]

file.close
#Closing file 

#Checking the user can acces this functionality 
#Based off of Levi's specifications
#TODO: find if E3DB can indeed grant record reading permission to other clients 
if (client_name).lower() == 'alicia' or (client_name).lower() == 'clarence' :
    print("Verified Permissions")
else :
    sys.exit("Permisions not valid")

#Credential paths needed for this operation
#we wil need to check alicias and bruces records, and then store the judgement record
# on clarences records 
credentials_path= sys.argv[2]


#Opening all credential paths and assigining to a specific client 
if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))


#Storing round variable passed in for futher use 
#not necssary but more readable 
round= sys.argv[1]


#query to grab all the moves made by alicia and bruce 
#query should be able to be, but ir doesnt work! 

query= Search(include_data=True,include_all_writers= True).match(record_types=['rps_move'])
results = client.search(query)    

#Incase bruce  or alice never submitted a play for the round, needed to be caught at 
#the end exception
bruce_play= "null"  
alice_play="null"

#This for loop goes through all the results pulled from Alicia's records
#then filters by round
#TODO: find out how to use the query value to filter by round needed
# take the last entry incase alicia enters more than one
for record in results:
    if record.data['round'] == round:
        if str(record.data['name']).lower() == 'alicia':
            alice_play= record.data['move']
        if str(record.data['name']).lower() == 'bruce': 
            bruce_play= record.data['move']



#All possible scenarios for possibilities of who would win 
#Decided to be able to tie
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
else:  #catch all for any wierdness
    print("Invalid or Incomplete Data")
    sys.exit("Not enough data to complete")



alicia_client_id="62ec5390-fef9-4003-a61f-617f51b2ceff"
bruces_client_id="cdfd094b-b73d-460f-9c5e-b24411883aa0"
clarence_client_id= "a06e2162-ce38-4cd2-a63e-6837bbbe4c1a"

record_type= 'rps_winner'

if(client_name.lower() == 'alicia') :
    record_type= 'rps_winner'
    client.revoke(record_type, clarence_client_id)
    client.share(record_type, clarence_client_id)
    client.revoke(record_type, bruces_client_id)
    client.share(record_type, bruces_client_id)

if(client_name.lower() == 'clarence'):
    record_type= 'rps_winner'
    client.revoke(record_type, alicia_client_id)
    client.revoke(record_type, bruces_client_id)
    client.share(record_type, alicia_client_id)
    client.share(record_type, bruces_client_id)



#Bruce's record writting to E3DB
record = client.write(record_type, data)
print ('Wrote record ID {0}'.format(record.meta.record_id))

# Read that record back from the server and print the name
record2 = client.read(record.meta.record_id)
print ('Round "{0}" '.format(record2.data['round']), ' Winner {0} Submitted!'.format(record2.data['name']))