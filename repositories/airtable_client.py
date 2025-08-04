"""Airtable API wrapper for the Participants table."""

from pyairtable import Api
import os
import logging

logger = logging.getLogger(__name__)


class AirtableClient:
    def __init__(self):
        self.token = os.getenv("AIRTABLE_TOKEN")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")

        if not self.token or not self.base_id:
            raise ValueError("AIRTABLE_TOKEN and AIRTABLE_BASE_ID must be set")

        self.api = Api(self.token)
        self.participants_table = self.api.table(self.base_id, "Participants")

    def test_connection(self):
        """Test connection to Airtable"""
        try:
            # Try to get first record to test connection
            records = self.participants_table.all(max_records=1)
            logger.info("Airtable connection successful")
            return True
        except Exception as e:
            logger.error(f"Airtable connection failed: {e}")
            return False
