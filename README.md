# secret-santa

Simple python script that takes a csv file with Name,Phone and randomly assigns a secret santa to 
everyone and sends a SMS to everyone letting them know. This leverages AWS SNS for sending the text message.

## csv file format

```
Name,Phone Number
John Doe,987654321
```

# AWS -> SNS -> Text messaging (SMS)
Usualy the account will in SMS sandbox mode, to allow to send to any number disable sandbox mode.