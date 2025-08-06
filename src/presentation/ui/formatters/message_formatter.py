class MessageFormatter:
    @staticmethod
    def format_participant_info(data: dict) -> str:
        lines = [f"{k}: {v}" for k, v in data.items()]
        return "\n".join(lines)
