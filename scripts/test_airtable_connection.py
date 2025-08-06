from repositories.airtable_client import AirtableClient
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    try:
        client = AirtableClient()
        if client.test_connection():
            print("✅ Airtable подключение работает!")
        else:
            print("❌ Ошибка подключения к Airtable")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
