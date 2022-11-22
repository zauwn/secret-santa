#!/usr/bin/env python3

import csv
import boto3
import random
import logging

AWS_ACCESS_KEY="AWS-ACCESS-KEY"
AWS_SECRET_KEY="AWS-SECRET-KEY"
AWS_REGION="eu-west-1"

FILE="list.csv"

budget = "20"
coin = "€"
country_prefix="+351"

# Change to ERROR to not print anything
logging.basicConfig(filename="results.log", level=logging.DEBUG)

everyone = []

#### Load list from csv
couple_index = 0
with open(FILE, mode='r') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    fields = next(csv_reader)
    for row in csv_reader:
        if row[0].lower() == "couple":
            everyone.append([row[1], row[2], True, "couple" + str(line_count)])
            everyone.append([row[3], row[4], True, "couple" + str(line_count)])
        elif row[0].lower() == "single":
            everyone.append([row[1], row[2], False ])
        else:
            logging.error("Invalid Status: " + row[0])
        line_count +=1

    csv_file.close()

secret_santas = everyone.copy()

# Start aws sns client
client = boto3.client(
    "sns",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

sms_to_send = {}

for receiver in everyone:
    not_found = True
    while not_found:
        santa_index = random.randrange(0, len(secret_santas))
        santa = secret_santas[santa_index]
        # If same receiver and santa, and no one else to choose from, end with invalid
        if santa[0] == receiver[0] and len(secret_santas) == 1:
            logging.error("Invalid result. Run again")
            exit(2)
        # Santa and Receiver are the same
        elif santa[0] == receiver[0] and len(secret_santas) > 1:
            not_found = True
        # If both couples, make sure they are not the same couple
        elif santa[2] and receiver[2]:
            # If same couple and no one else to choose from, end with invalid
            if santa[3] == receiver[3] and len(secret_santas) == 1:
                logging.error("Invalid result. Run again")
                exit(3)
            # If same couple, don't choose
            elif santa[3] == receiver[3]:
                not_found = True
            else:
                not_found = False
        else:
            not_found = False

    sms_message="Secret Santa 2022!!! Congratulations " + santa[0] +" you're the Secret Santa of << " + receiver[0] + " >>. The gift's budget is: " + budget + coin
    logging.debug(sms_message)
    secret_santas.pop(santa_index)
    logging.info("Sending sms to " + santa[0] + ", nº <"+ santa[1].replace(" ", "") +">")
    sms_to_send[ santa[1].replace(" ", "")] = sms_message

for number in sms_to_send:
        client.publish(
            PhoneNumber = country_prefix + number,
            Message = sms_to_send[number]
        )