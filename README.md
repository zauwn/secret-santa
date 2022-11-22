# secret-santa

Simple python script that takes a csv file with Name,Phone and randomly assigns a secret santa to 
everyone and sends a SMS to everyone letting them know. There is a restriction where people from same couple cannot be each others secret santa.
This leverages AWS SNS for sending the text message.

## csv file format

```
Status,Name,Phone Number,[Name],[Phone Number]
Single,John Doe,91234561
Couple,Jackie Chan,91234562,Elizabeth,91234563
```

# AWS -> SNS -> Text messaging (SMS)
Usualy the account will in SMS sandbox mode, to allow to send to any number disable sandbox mode.