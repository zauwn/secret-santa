# secret-santa

Simple Python script that takes a CSV file with participant names and phone numbers, randomly assigns a Secret Santa to everyone, and sends SMS notifications via AWS SNS.

**Key features:**

- Ensures no one is their own Secret Santa
- Prevents people in the same couple from being assigned to each other
- Configurable via environment variables
- Robust error handling and logging

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create your participant list:

```bash
cp list.csv.example list.csv
# Edit list.csv with your actual participants
```

3. Configure AWS credentials using one of these methods:
   - **Environment variables** (recommended):
     ```bash
     export AWS_ACCESS_KEY_ID="your-access-key"
     export AWS_SECRET_ACCESS_KEY="your-secret-key"
     export AWS_REGION="eu-west-1"  # Optional, defaults to eu-west-1
     ```
   - **AWS credentials file** (`~/.aws/credentials`)
   - **IAM instance profile** (if running on EC2)

## CSV File Format

Create a CSV file (default: `list.csv`) with the following structure:

```csv
Status,Name,Phone Number,[Name],[Phone Number]
Single,John Doe,91234561
Couple,Jackie Chan,91234562,Elizabeth,91234563
```

- **Status**: Either `Single` or `Couple`
- **Single**: Requires Name and Phone Number
- **Couple**: Requires two names and two phone numbers (person 1 and person 2)
- **Phone numbers**: Should not include the country prefix (configured separately)

## Configuration

All settings can be customized via environment variables:

| Environment Variable          | Default      | Description                                                             |
| ----------------------------- | ------------ | ----------------------------------------------------------------------- |
| `SECRET_SANTA_FILE`           | `list.csv`   | Path to CSV file with participants                                      |
| `SECRET_SANTA_BUDGET`         | `20`         | Gift budget amount                                                      |
| `SECRET_SANTA_COIN`           | `€`          | Currency symbol                                                         |
| `SECRET_SANTA_COUNTRY_PREFIX` | `+351`       | Country code prefix for phone numbers                                   |
| `SECRET_SANTA_YEAR`           | Current year | Year to display in messages                                             |
| `SECRET_SANTA_DRY_RUN`        | `false`      | Dry run mode - generate assignments without sending SMS (1/true/yes/on) |
| `SECRET_SANTA_LOG_LEVEL`      | `DEBUG`      | Logging level (DEBUG, INFO, ERROR)                                      |
| `AWS_REGION`                  | `eu-west-1`  | AWS region for SNS                                                      |

## Usage

### Basic usage (with defaults):

```bash
python3 secret-santa.py
```

### Dry run (test without sending SMS):

```bash
export SECRET_SANTA_DRY_RUN=true
python3 secret-santa.py
```

This will:

- Load participants and generate assignments
- Display all messages that would be sent
- Skip actual SMS sending
- Useful for testing before running for real

### Custom configuration:

```bash
export SECRET_SANTA_FILE="my_participants.csv"
export SECRET_SANTA_BUDGET="50"
export SECRET_SANTA_COIN="$"
export SECRET_SANTA_COUNTRY_PREFIX="+1"
export SECRET_SANTA_YEAR="2025"

python3 secret-santa.py
```

### Check logs:

```bash
tail -f results.log
```

## AWS SNS Setup

1. **Enable SMS in your AWS account:**
   - Go to AWS SNS console
   - Navigate to "Text messaging (SMS)" → "Sandbox destinations" (if in sandbox mode)
2. **Sandbox mode:**
   - By default, AWS SNS is in sandbox mode
   - You must verify each destination phone number before sending
   - To send to any number, request production access via AWS Support

3. **Required IAM permissions:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "sns:Publish",
         "Resource": "*"
       }
     ]
   }
   ```

## How It Works

1. Loads participants from CSV file
2. Validates entries and handles couples appropriately
3. Generates a random Secret Santa assignment (up to 1000 attempts)
4. Ensures no self-assignments and no same-couple assignments
5. Sends personalized SMS to each participant via AWS SNS
6. Logs all operations to `results.log`

## Troubleshooting

- **Exit code 2**: Assignment failed (e.g., file not found, invalid data, or impossible constraints)
- **Exit code 3**: SNS client creation or SMS sending failed
- Check `results.log` for detailed error messages
- Ensure phone numbers in CSV do not include country prefix
- Verify AWS credentials have SNS publish permissions

