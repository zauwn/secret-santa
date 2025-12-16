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


def get_env(key, default=None):
    v = os.getenv(key, None)
    return v if v is not None else default


EUM_CHANNEL_ID = get_env("EUM_CHANNEL_ID")
EUM_SENDER_ID = get_env("EUM_SENDER_ID", "SENDER001")
EUM_REGION = get_env("EUM_REGION", "eu-west-1")
DEFAULT_FILE = "list.csv"
DEFAULT_BUDGET = "20"
DEFAULT_COIN = "€"
DEFAULT_COUNTRY_PREFIX = "+351"
DEFAULT_DRY_RUN = True
LOG_LEVEL_NAME = get_env("SECRET_SANTA_LOG_LEVEL", "DEBUG").upper()
EXIT_CODE_ASSIGNMENT_FAILED = 2
EXIT_CODE_EUM_FAILED = 3


def configure_logging():
    level = getattr(logging, LOG_LEVEL_NAME, logging.DEBUG)
    logging.basicConfig(
        filename="results.log",
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def load_participants(file_path: str):
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
                            "Invalid single entry at line %d: %s", line_number, row
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
                            "Invalid couple entry at line %d: %s", line_number, row
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


def is_valid_assignment(participants, indices):
    for receiver_idx, santa_idx in enumerate(indices):
        receiver = participants[receiver_idx]
        santa = participants[santa_idx]
        if santa["name"] == receiver["name"]:
            return False
        if (
            santa["is_couple"]
            and receiver["is_couple"]
            and santa["couple_id"] == receiver["couple_id"]
        ):
            return False
    return True


def generate_assignments(participants, max_attempts=1000):
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
        "Could not find a valid Secret Santa assignment after %d attempts."
        " Try again or adjust constraints.",
        max_attempts,
    )
    sys.exit(EXIT_CODE_ASSIGNMENT_FAILED)


def build_sms_messages(assignments, budget, coin, year):
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
            "Sending EUM SMS to %s, phone <***%s>",
            santa["name"],
            phone[-4:] if len(phone) >= 4 else phone,
        )
        sms_to_send[phone] = message
    return sms_to_send


def create_eum_client():
    try:
        client = boto3.client("eum", region_name=EUM_REGION)
        logging.info("Initialized EUM client in region '%s'", EUM_REGION)
        return client
    except (BotoCoreError, ClientError) as exc:
        logging.error("Failed to create EUM client: %s", exc)
        sys.exit(EXIT_CODE_EUM_FAILED)


def send_eum_sms_messages(client, sms_to_send, country_prefix, dry_run=False):
    if not EUM_CHANNEL_ID:
        logging.error("EUM_CHANNEL_ID must be set for EUM sending.")
        sys.exit(EXIT_CODE_EUM_FAILED)
    sender_id = EUM_SENDER_ID
    if not sender_id:
        logging.warning(
            "No EUM Sender ID set!"
            "Messages may be filtered or appear from generic originator."
        )
    elif (
        len(sender_id) > 11
    ):  # EUM may allow longer, but for SMS some carriers restrict for consistency.
        logging.warning(
            "SenderId '%s' longer than 11 chars; may be truncated by carriers.",
            sender_id,
        )
    logging.info("Using EUM Channel ID: %s, Sender ID: %s", EUM_CHANNEL_ID, sender_id)
    if dry_run:
        logging.info("DRY RUN MODE - No SMS messages will be sent (EUM)")
        print("\n=== DRY RUN MODE (EUM) ===")
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
            response = client.send_message(
                ChannelId=EUM_CHANNEL_ID,
                Destination={"PhoneNumber": full_number},
                Content={"Body": message},
                SenderId=sender_id,
            )
            logging.debug("Published EUM SMS to %s; result: %s", full_number, response)
        except (BotoCoreError, ClientError) as exc:
            logging.error("Failed to send EUM SMS to %s: %s", full_number, exc)
            sys.exit(EXIT_CODE_EUM_FAILED)


def main():
    configure_logging()
    file_path = get_env("SECRET_SANTA_FILE", DEFAULT_FILE)
    budget = get_env("SECRET_SANTA_BUDGET", DEFAULT_BUDGET)
    coin = get_env("SECRET_SANTA_COIN", DEFAULT_COIN)
    country_prefix = get_env("SECRET_SANTA_COUNTRY_PREFIX", DEFAULT_COUNTRY_PREFIX)
    year = get_env("SECRET_SANTA_YEAR", str(date.today().year))
    dry_run_env = get_env("SECRET_SANTA_DRY_RUN", "").lower()
    dry_run = dry_run_env in ("1", "true", "yes", "on")
    logging.info(
        "[EUM] Using file='%s', budget=%s%s, year=%s, dry_run=%s",
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
        client = create_eum_client()
    else:
        client = None
    send_eum_sms_messages(client, sms_to_send, country_prefix, dry_run)


if __name__ == "__main__":
    main()
