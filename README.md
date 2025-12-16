# secret-santa

Simple Python script that takes a CSV file with participant names and phone numbers, randomly assigns a Secret Santa to everyone, and sends SMS notifications via AWS SNS or AWS End User Messaging (EUM).

**Key features:**

- Ensures no one is their own Secret Santa
- Prevents people in the same couple from being assigned to each other
- Configurable via environment variables
- Robust error handling and logging
- **Supports two sending methods:**
    - AWS SNS (with enforced Sender ID)
    - AWS End User Messaging (EUM) (recommended for maximum sender control/delivery)

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

| Environment Variable             | Default      | Description                                                                |
| -------------------------------- | ------------ | -------------------------------------------------------------------------- |
| `SECRET_SANTA_FILE`              | `list.csv`   | Path to CSV file with participants                                         |
| `SECRET_SANTA_BUDGET`            | `20`         | Gift budget amount                                                         |
| `SECRET_SANTA_COIN`              | `€`          | Currency symbol                                                            |
| `SECRET_SANTA_COUNTRY_PREFIX`    | `+351`       | Country code prefix for phone numbers                                      |
| `SECRET_SANTA_YEAR`              | Current year | Year to display in messages                                                |
| `SECRET_SANTA_DRY_RUN`           | `false`      | Dry run mode - generate assignments without sending SMS (1/true/yes/on)    |
| `SECRET_SANTA_LOG_LEVEL`         | `DEBUG`      | Logging level (DEBUG, INFO, ERROR)                                         |
| `AWS_REGION`                     | `eu-west-1`  | AWS region for SNS or EUM                                                  |
| `SECRET_SANTA_SENDER_ID`         | `NATAL2025`  | **(SNS only)** Sender ID for branded SMS (up to 11 alphanumeric chars)     |
| `EUM_CHANNEL_ID`                 | (none)       | **(EUM only)** Channel ID for AWS EUM                                      |
| `EUM_SENDER_ID`                  | `NATAL-22`   | **(EUM only)** Approved Sender ID for EUM                                  |
| `EUM_REGION`                     | `eu-west-1`  | **(EUM only)** Region for EUM client                                       |

## Usage

### Send SMS with SNS (default):

```bash
python3 secret-santa.py
```

This uses AWS SNS to send SMS, enforcing Sender ID (default: NATAL2025).

### Send SMS with End User Messaging (EUM, recommended for delivery):

```bash
python3 secret-santa-eum.py
```
- Set required env vars:
  - `EUM_CHANNEL_ID` (must correspond to your AWS EUM Portuguese SMS channel)
  - `EUM_SENDER_ID` (should be set to approved value, e.g., NATAL-22)
  - `EUM_REGION` (usually eu-west-1 for Portugal)

### Dry run (test without sending SMS):

```bash
export SECRET_SANTA_DRY_RUN=true
python3 secret-santa.py
# Or for EUM:
export SECRET_SANTA_DRY_RUN=true
python3 secret-santa-eum.py
```

This will:
- Load participants and generate assignments
- Display all messages that would be sent
- Skip actual SMS sending
- Useful for testing before running for real

## Vodafone PT and Sender ID guidance

- **For Portugal (Vodafone/PT):** Sender ID is generally supported, but may rarely be ignored by the carrier gate.
- **EUM path** is preferred for maximum deliverability and compliance.
- **SNS path** should now include Sender ID, but you may still observe the occasional network-based override, which is outside AWS’s control!

## Troubleshooting

- **Exit code 2**: Assignment failed (e.g., file not found, invalid data, or impossible constraints)
- **Exit code 3**: SNS/EUM client creation or SMS sending failed
- Check `results.log` for detailed error messages
- Ensure phone numbers in CSV do not include country prefix
- Verify AWS credentials have publish permissions

## AWS Account Requirements

- If using SNS Sender ID: May require production status and AWS support ticket if running at scale.
- If using EUM: Register your Sender ID and Channel via AWS Console and ensure you have the correct region/channel ID/Sender ID set in environment.

## Logs

All logs are written to `results.log` in project root.
