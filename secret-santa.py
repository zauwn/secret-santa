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

participants_list = []

#### Load list from csv
with open(FILE, mode='r') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    fields = next(csv_reader)
    for row in csv_reader:
        participants_list.append(row)
    participants_number = csv_reader.line_num - 1
    csv_file.close()

# Create an SNS client
client = boto3.client(
    "sns",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

random.shuffle(participants_list)
logging.debug(participants_list)
offset = [participants_list[-1]] + participants_list[:-1]
for santa, receiver in zip(participants_list, offset):
    logging.info(santa[0]+ " buys for " + receiver[0])
    sms_message="Secret Santa 2022!!!\nYou're the Secret Santa of <" + receiver[0] + ">.\nThe gift's budget is: " + budget + coin
    logging.debug(sms_message)
    logging.debug("Sending sms to " + santa[0] + " nº <"+ santa[1].replace(" ", "") +">")
    client.publish(
        PhoneNumber = country_prefix + santa[1].replace(" ", ""),
        Message=sms_message
    )