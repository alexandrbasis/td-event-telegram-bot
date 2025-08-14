import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.airtable_participant_repository import AirtableParticipantRepository
from models.participant import Participant
from dotenv import load_dotenv

load_dotenv()

# Entry point for manual invocation
if __name__ == "__main__":
    try:
        repo = AirtableParticipantRepository()

        # Test create
        test_participant = Participant(
            FullNameRU="Тест Пользователь",
            Gender="M",
            Size="L",
            Church="Тестовая Церковь",
            Role="CANDIDATE",
        )

        participant_id = repo.add(test_participant)
        print(f"✅ Created participant with ID: {participant_id}")

        # Test get
        retrieved = repo.get_by_id(participant_id)
        if retrieved:
            print(f"✅ Retrieved participant: {retrieved.FullNameRU}")

        # Test delete (cleanup)
        repo.delete(participant_id)
        print("✅ Test participant deleted")

        print("🎉 All Airtable repository tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
