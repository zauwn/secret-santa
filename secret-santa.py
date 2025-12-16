#!/usr/bin/env python3

import csv
import logging
import os
import random
import sys
from datetime import date

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# ---------------------------------------------------------------------------
# Configuration (can be overridden via environment variables)
# ---------------------------------------------------------------------------

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Let boto3 resolve credentials via normal AWS mechanisms
# (env vars, shared config, instance profile, etc.).

DEFAULT_FILE = "list.csv"
DEFAULT_BUDGET = "20"
DEFAULT_COIN = "€"
DEFAULT_COUNTRY_PREFIX = "+351"
DEFAULT_DRY_RUN = True

EXIT_CODE_ASSIGNMENT_FAILED = 2
EXIT_CODE_SNS_FAILED = 3

# Change to logging.ERROR to be quieter
LOG_LEVEL_NAME = os.getenv("SECRET_SANTA_LOG_LEVEL", "DEBUG").upper()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL_NAME, logging.DEBUG)
    logging.basicConfig(
        filename="results.log",
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_participants(file_path: str):
    """
    Load participants from CSV.

    CSV format:
    Status,Name,Phone Number,[Name],[Phone Number]

    Status = "Single" or "Couple"
    """
    participants = []

    try:
        with open(file_path, mode="r", newline="") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            try:
                next(csv_reader)
            except StopIteration:
                logging.error("CSV file '%s' is empty", file_path)
                sys.exit(EXIT_CODE_ASSIGNMENT_FAILED)

            couple_counter = 0
            for line_number, row in enumerate(csv_reader, start=2):
                if not row:
                    continue

                status = row[0].strip().lower()

                if status == "single":
                    if len(row) < 3:
                        logging.error(
                            "Invalid single entry at line %d: %s",
                            line_number,
                            row,
                        )
                        continue

                    name = row[1].strip()
                    phone = row[2].strip()
                    participants.append(
                        {
                            "name": name,
                            "phone": phone,
                            "is_couple": False,
                            "couple_id": None,
                        }
                    )

                elif status == "couple":
                    if len(row) < 5:
                        logging.error(
                            "Invalid couple entry at line %d: %s",
                            line_number,
                            row,
                        )
                        continue

                    couple_id = f"couple{couple_counter}"
                    couple_counter += 1

                    name1 = row[1].strip()
                    phone1 = row[2].strip()
                    name2 = row[3].strip()
                    phone2 = row[4].strip()

                    participants.append(
                        {
                            "name": name1,
                            "phone": phone1,
                            "is_couple": True,
                            "couple_id": couple_id,
                        }
                    )
                    participants.append(
                        {
                            "name": name2,
                            "phone": phone2,
                            "is_couple": True,
                            "couple_id": couple_id,
                        }
                    )

                else:
                    logging.error("Invalid status '%s' at line %d", row[0], line_number)

    except FileNotFoundError:
        logging.error("CSV file '%s' not found", file_path)
        sys.exit(EXIT_CODE_ASSIGNMENT_FAILED)
    except OSError as exc:
        logging.error("Error reading CSV file '%s': %s", file_path, exc)
        sys.exit(EXIT_CODE_ASSIGNMENT_FAILED)

    if len(participants) < 2:
        logging.error(
            "Need at least two valid participants; found %d", len(participants)
        )
        sys.exit(EXIT_CODE_ASSIGNMENT_FAILED)

    logging.info("Loaded %d participants from '%s'", len(participants), file_path)
    return participants


# ---------------------------------------------------------------------------
# Secret Santa assignment
# ---------------------------------------------------------------------------


def is_valid_assignment(participants, indices):
    """
    Check that a permutation (indices) respects constraints:
    - No one is their own Santa
    - People in the same couple cannot be each other's Santa
    """
    for receiver_idx, santa_idx in enumerate(indices):
        receiver = participants[receiver_idx]
        santa = participants[santa_idx]

        # No self-gifting
        if santa["name"] == receiver["name"]:
            return False

        # No same-couple gifting
        if (
            santa["is_couple"]
            and receiver["is_couple"]
            and santa["couple_id"] == receiver["couple_id"]
        ):
            return False

    return True


def generate_assignments(participants, max_attempts=1000):
    """
    Generate a valid random Secret Santa assignment.

    Returns list of (santa, receiver) dict pairs.
    """
    n = len(participants)
    indices = list(range(n))

    for attempt in range(max_attempts):
        random.shuffle(indices)
        if is_valid_assignment(participants, indices):
            logging.debug("Found valid assignment on attempt %d", attempt + 1)
            return [
                (participants[santa_idx], participants[receiver_idx])
                for receiver_idx, santa_idx in enumerate(indices)
            ]

    logging.error(
        "Could not find a valid Secret Santa assignment "
        "after %d attempts. Try again or adjust constraints.",
        max_attempts,
    )
    sys.exit(EXIT_CODE_ASSIGNMENT_FAILED)


def build_sms_messages(assignments, budget, coin, year):
    """
    Build SMS messages keyed by phone number (without spaces).
    """
    sms_to_send = {}

    for santa, receiver in assignments:
        phone = santa["phone"].replace(" ", "")

        message = (
            f"Secret Santa {year}!!! Congratulations {santa['name']} "
            f"you're the Secret Santa of << {receiver['name']} >>. "
            f"The gift's budget is: {budget}{coin}"
        )

        logging.debug("Message for %s: %s", santa["name"], message)
        logging.info(
            "Sending SMS to %s, phone <***%s>",
            santa["name"],
            phone[-4:] if len(phone) >= 4 else phone,
        )

        sms_to_send[phone] = message

    return sms_to_send


# ---------------------------------------------------------------------------
# AWS SNS
# ---------------------------------------------------------------------------


def create_sns_client():
    try:
        client = boto3.client("sns", region_name=AWS_REGION)
        logging.info("Initialized SNS client in region '%s'", AWS_REGION)
        return client
    except (BotoCoreError, ClientError) as exc:
        logging.error("Failed to create SNS client: %s", exc)
        sys.exit(EXIT_CODE_SNS_FAILED)


def send_sms_messages(client, sms_to_send, country_prefix, dry_run=False):
    sender_id = os.getenv("SECRET_SANTA_SENDER_ID", "SENDER001")
    if not sender_id:
        logging.warning(
            "No SNS SenderId set!"
            "Messages may be filtered or appear from generic originator."
        )
    elif len(sender_id) > 11 or not sender_id.isalnum():
        logging.error(
            "SenderId '%s' invalid for SNS (max 11 alphanumeric chars)", sender_id
        )
        sender_id = sender_id[:11]  # defensive fallback
    logging.info("Using SNS SenderId: %s", sender_id)
    if dry_run:
        logging.info("DRY RUN MODE - No SMS messages will be sent")
        print("\n=== DRY RUN MODE ===")
        print(f"Would send {len(sms_to_send)} SMS messages:\n")

        for phone, message in sms_to_send.items():
            full_number = f"{country_prefix}{phone}"
            print(f"To: {full_number}")
            print(f"Message: {message}\n")

        logging.info(
            "Dry run completed. %d messages would have been sent.", len(sms_to_send)
        )
        return

    for phone, message in sms_to_send.items():
        full_number = f"{country_prefix}{phone}"
        try:
            client.publish(
                PhoneNumber=full_number,
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {
                        "DataType": "String",
                        "StringValue": sender_id,
                    }
                },
            )
            logging.debug("Published SMS to %s", full_number)
        except (BotoCoreError, ClientError) as exc:
            logging.error("Failed to send SMS to %s: %s", full_number, exc)
            # Continue sending to others, but retain non-zero exit code
            # to signal a problem at the end.
            return_code = EXIT_CODE_SNS_FAILED
            # Store last non-zero status in a global variable or return;
            # here we simply exit on first failure:
            sys.exit(return_code)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    configure_logging()

    file_path = os.getenv("SECRET_SANTA_FILE", DEFAULT_FILE)
    budget = os.getenv("SECRET_SANTA_BUDGET", DEFAULT_BUDGET)
    coin = os.getenv("SECRET_SANTA_COIN", DEFAULT_COIN)
    country_prefix = os.getenv("SECRET_SANTA_COUNTRY_PREFIX", DEFAULT_COUNTRY_PREFIX)
    year = os.getenv("SECRET_SANTA_YEAR", str(date.today().year))
    dry_run_env = os.getenv("SECRET_SANTA_DRY_RUN", "").lower()
    dry_run = dry_run_env in ("1", "true", "yes", "on")

    logging.info(
        "Using file='%s', budget=%s%s, year=%s, dry_run=%s",
        file_path,
        budget,
        coin,
        year,
        dry_run,
    )

    participants = load_participants(file_path)
    assignments = generate_assignments(participants)
    sms_to_send = build_sms_messages(assignments, budget, coin, year)

    if not dry_run:
        client = create_sns_client()
    else:
        client = None

    send_sms_messages(client, sms_to_send, country_prefix, dry_run)


if __name__ == "__main__":
    main()
