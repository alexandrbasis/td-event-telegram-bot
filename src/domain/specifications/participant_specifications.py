from domain.models.participant import Participant


class TeamRoleRequiresDepartmentSpecification:
    """Ensure TEAM role participants specify a department."""

    def is_satisfied_by(self, participant: Participant) -> bool:
        return participant.role != "TEAM" or bool(participant.department)
