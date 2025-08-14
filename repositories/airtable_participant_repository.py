import logging
from typing import Dict, List, Optional, Union
import time

from pyairtable.api.types import RecordDict
from pyairtable.formulas import match

from repositories.participant_repository import BaseParticipantRepository
from models.participant import Participant
from repositories.airtable_client import AirtableClient
from utils.exceptions import (
    ParticipantNotFoundError,
    ValidationError,
    BotException,
    DatabaseError,
)

logger = logging.getLogger(__name__)


class AirtableParticipantRepository(BaseParticipantRepository):
    """Airtable implementation of participant repository."""

    def __init__(self):
        self.client = AirtableClient()
        self.table = self.client.participants_table

    def _participant_to_airtable_fields(self, participant: Participant) -> dict:
        """Convert Participant dataclass to Airtable fields."""
        return {
            'FullNameRU': participant.FullNameRU,
            'FullNameEN': participant.FullNameEN or '',
            'Gender': participant.Gender,
            'Size': participant.Size or '',
            'Church': participant.Church or '',
            'Role': participant.Role or '',
            'Department': participant.Department or '',
            'CountryAndCity': participant.CountryAndCity or '',
            'SubmittedBy': participant.SubmittedBy or '',
            'ContactInformation': participant.ContactInformation or '',
            'PaymentStatus': participant.PaymentStatus or 'Unpaid',
            'PaymentAmount': participant.PaymentAmount or 0,
            'PaymentDate': participant.PaymentDate or '',
        }

    def _airtable_record_to_participant(self, record: RecordDict) -> Participant:
        """Convert Airtable record to Participant dataclass."""
        fields = record.get('fields', {})
        return Participant(
            id=record['id'],  # Airtable record ID
            FullNameRU=fields.get('FullNameRU', ''),
            FullNameEN=fields.get('FullNameEN', ''),
            Gender=fields.get('Gender', 'F'),
            Size=fields.get('Size', ''),
            Church=fields.get('Church', ''),
            Role=fields.get('Role', ''),
            Department=fields.get('Department', ''),
            CountryAndCity=fields.get('CountryAndCity', ''),
            SubmittedBy=fields.get('SubmittedBy', ''),
            ContactInformation=fields.get('ContactInformation', ''),
            PaymentStatus=fields.get('PaymentStatus', 'Unpaid'),
            PaymentAmount=fields.get('PaymentAmount', 0),
            PaymentDate=fields.get('PaymentDate', ''),
        )

    def add(self, participant: Participant) -> int:
        """Add participant to Airtable."""
        logger.info(f"Adding participant to Airtable: {participant.FullNameRU}")

        try:
            fields = self._participant_to_airtable_fields(participant)
            record = self.table.create(fields)

            # Возвращаем Airtable record ID как строку
            record_id = record['id']
            logger.info(f"Successfully added participant with ID: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Error adding participant to Airtable: {e}")
            raise DatabaseError(f"Airtable error on add: {e}") from e

    def get_by_id(self, participant_id: Union[int, str]) -> Optional[Participant]:
        """Get participant by Airtable record ID."""
        participant_id = str(participant_id)
        logger.info(f"Getting participant by ID from Airtable: {participant_id}")

        try:
            record = self.table.get(participant_id)
            return self._airtable_record_to_participant(record)

        except Exception as e:
            if "NOT_FOUND" in str(e) or "Record not found" in str(e):
                logger.debug(f"Participant {participant_id} not found in Airtable")
                return None
            logger.error(f"Error getting participant from Airtable: {e}")
            raise DatabaseError(f"Airtable error on get_by_id: {e}") from e

    def get_by_name(self, full_name_ru: str) -> Optional[Participant]:
        """Get participant by full Russian name."""
        logger.info(f"Getting participant by name from Airtable: {full_name_ru}")

        try:
            # Use Airtable formula to find exact match
            formula = match({"FullNameRU": full_name_ru})
            records = self.table.all(formula=formula)

            if not records:
                return None

            # Return first match
            return self._airtable_record_to_participant(records[0])

        except Exception as e:
            logger.error(f"Error searching participant by name: {e}")
            raise DatabaseError(f"Airtable error on get_by_name: {e}") from e

    def get_all(self) -> List[Participant]:
        """Get all participants from Airtable."""
        logger.info("Getting all participants from Airtable")

        try:
            records = self.table.all()
            participants = []

            for record in records:
                participant = self._airtable_record_to_participant(record)
                participants.append(participant)

            logger.info(f"Retrieved {len(participants)} participants from Airtable")
            return participants

        except Exception as e:
            logger.error(f"Error getting all participants: {e}")
            raise DatabaseError(f"Airtable error on get_all: {e}") from e

    def update(self, participant: Participant) -> bool:
        """Update participant completely."""
        if not participant.id:
            raise ValueError("Participant ID must be set for update operation")

        logger.info(
            f"Updating participant in Airtable: {participant.FullNameRU} (ID: {participant.id})"
        )

        try:
            fields = self._participant_to_airtable_fields(participant)
            self.table.update(participant.id, fields)

            logger.info(f"Successfully updated participant {participant.id}")
            return True

        except Exception as e:
            if "NOT_FOUND" in str(e):
                raise ParticipantNotFoundError(
                    f"Participant with id {participant.id} not found"
                )
            logger.error(f"Error updating participant: {e}")
            raise DatabaseError(f"Airtable error on update: {e}") from e

    def update_fields(self, participant_id: Union[int, str], **fields) -> bool:
        """Update specific fields for a participant."""
        participant_id = str(participant_id)
        self._validate_fields(**fields)

        logger.info(
            f"Updating fields for participant {participant_id}: {list(fields.keys())}"
        )

        try:
            # Convert empty strings to actual empty values for Airtable
            airtable_fields = {}
            for key, value in fields.items():
                airtable_fields[key] = value if value else ''

            self.table.update(participant_id, airtable_fields)

            logger.info(f"Successfully updated fields for participant {participant_id}")
            return True

        except Exception as e:
            if "NOT_FOUND" in str(e):
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found"
                )
            logger.error(f"Error updating participant fields: {e}")
            raise DatabaseError(f"Airtable error on update_fields: {e}") from e

    def delete(self, participant_id: Union[int, str]) -> bool:
        """Delete participant from Airtable."""
        participant_id = str(participant_id)
        logger.info(f"Deleting participant from Airtable: {participant_id}")

        try:
            self.table.delete(participant_id)

            logger.info(f"Successfully deleted participant {participant_id}")
            return True

        except Exception as e:
            if "NOT_FOUND" in str(e):
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found for deletion"
                )
            logger.error(f"Error deleting participant: {e}")
            raise DatabaseError(f"Airtable error on delete: {e}") from e

    def exists(self, participant_id: Union[int, str]) -> bool:
        """Check if participant exists in Airtable."""
        return self.get_by_id(participant_id) is not None

    def update_payment(self, participant_id: Union[int, str], status: str, amount: int, date: str) -> bool:
        """Update payment status for a participant in Airtable."""
        participant_id = str(participant_id)
        logger.info(f"Updating payment for participant {participant_id}: {status}, {amount}₪")

        try:
            payment_fields = {
                'PaymentStatus': status,
                'PaymentAmount': amount,
                'PaymentDate': date,
            }
            self.table.update(participant_id, payment_fields)

            logger.info(f"Successfully updated payment for participant {participant_id}")
            return True

        except Exception as e:
            if "NOT_FOUND" in str(e):
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found"
                )
            logger.error(f"Error updating payment in Airtable: {e}")
            raise DatabaseError(f"Airtable error on update_payment: {e}") from e

    def get_unpaid_participants(self) -> List[Participant]:
        """Get all unpaid participants from Airtable."""
        logger.info("Getting unpaid participants from Airtable")

        try:
            # Use Airtable formula to filter unpaid participants
            formula = match({"PaymentStatus": "Unpaid"})
            records = self.table.all(formula=formula)

            participants = []
            for record in records:
                participant = self._airtable_record_to_participant(record)
                participants.append(participant)

            logger.info(f"Retrieved {len(participants)} unpaid participants from Airtable")
            return participants

        except Exception as e:
            logger.error(f"Error getting unpaid participants from Airtable: {e}")
            raise DatabaseError(f"Airtable error on get_unpaid_participants: {e}") from e

    def get_payment_summary(self) -> Dict:
        """Get payment summary from Airtable."""
        logger.info("Getting payment summary from Airtable")

        try:
            # Get all participants to calculate summary
            all_participants = self.get_all()
            
            status_breakdown = {}
            total_amount = 0
            paid_count = 0
            
            for participant in all_participants:
                status = participant.PaymentStatus
                amount = participant.PaymentAmount
                
                if status not in status_breakdown:
                    status_breakdown[status] = {"count": 0, "total": 0}
                
                status_breakdown[status]["count"] += 1
                status_breakdown[status]["total"] += amount
                total_amount += amount
                
                if status == "Paid":
                    paid_count += 1

            return {
                "status_breakdown": status_breakdown,
                "total_participants": len(all_participants),
                "total_amount": total_amount,
                "paid_count": paid_count,
                "unpaid_count": len(all_participants) - paid_count
            }

        except Exception as e:
            logger.error(f"Error getting payment summary from Airtable: {e}")
            raise DatabaseError(f"Airtable error on get_payment_summary: {e}") from e

    def _handle_rate_limit(self, retry_count: int = 0):
        """Handle Airtable rate limiting with exponential backoff."""
        if retry_count > 3:
            raise DatabaseError("Rate limit exceeded after multiple retries")

        wait_time = (2 ** retry_count) * 0.2  # 0.2, 0.4, 0.8, 1.6 seconds
        logger.warning(f"Rate limited, waiting {wait_time} seconds...")
        time.sleep(wait_time)
