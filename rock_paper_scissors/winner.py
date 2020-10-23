
import e3db
import sys
import os
import json
from e3db.types import Search

#Example command line arguments given by Levi:
# $ python3 winner.py round=1 tozny-client-credentials-filepath=./bruce_creds.json

# Argument Counter Check, Making sure user is passing in all needed arguments 
if len(sys.argv) != 3 :
    sys.exit("Incorrect Arguments:\n python3 winner.py [round] [client-credentials]")



#File opening to grab user's name 
file = open(sys.argv[2], "r")

client_json = json.loads(file.read())

client_name=client_json["name"]

#File closing
file.close


#Checking the user can acces this functionality 
#Based off of Levi's specifications
#TODO: find if E3DB can indeed grant record reading permission to other clients 
if str(client_name).lower() == 'alicia' or str(client_name).lower() == 'clarence' or str(client_name).lower() == 'bruce'  :
    print("Verified Permissions")
else :
    sys.exit("Permisions not valid")


#Credential paths needed for this operation
# Needed clarences records to see who he judged to be the winnner
credentials_path= sys.argv[2]
if os.path.exists(credentials_path):
    client = e3db.Client(json.load(open(credentials_path)))


#Storing round variable passed in for futher use 
#not necssary but more readable
round= sys.argv[1]


# query to go through the round winners 
query= Search(include_data=True, include_all_writers= True).match( record_types=['rps_winner'] )
results = client.search(query) #stores the results 

#Setting to empty to be filled with winner or trrigger the exception of 
#round hasnt happened yet
winner= ""

#go through the results, store the latest result for the round
#to display 
for record in results:
    if str(record.data['round']) == str(round):
        winner= record.data['name']

#check if there is a winner or else give error 
if bool(winner):
    print("{0} is the winner for round {1}".format(winner, round))
else:
    print("Round has not occured yet, Check back soon")
