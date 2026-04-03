"""
Plan limits configuration for TaskMan.

This module defines the limits for different subscription plans.
Currently only FREE_PLAN is active. PRO_PLAN is a placeholder for future use.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    """Limits for a subscription plan."""
    max_teams: int
    max_team_members: int
    max_tasks_total: int
    max_personal_statuses: int
    max_team_statuses: int
    max_personal_labels: int
    max_team_labels: int
    max_personal_notes: int
    max_team_notes: int
    max_checklist_items: int


FREE_PLAN = PlanLimits(
    max_teams=3,
    max_team_members=10,
    max_tasks_total=500,
    max_personal_statuses=10,
    max_team_statuses=15,
    max_personal_labels=20,
    max_team_labels=30,
    max_personal_notes=50,
    max_team_notes=100,
    max_checklist_items=20,
)


# PRO_PLAN = PlanLimits(
#     max_teams=-1,
#     max_team_members=-1,
#     max_tasks_total=-1,
#     max_personal_statuses=-1,
#     max_team_statuses=-1,
#     max_personal_labels=-1,
#     max_team_labels=-1,
#     max_personal_notes=-1,
#     max_team_notes=-1,
#     max_checklist_items=-1,
# )


def get_user_limits(user) -> PlanLimits:
    """
    Get plan limits for a user.

    Currently always returns FREE_PLAN.
    TODO: In the future, check user.subscription (or similar field)
    and return PRO_PLAN for paid users.
    """
    return FREE_PLAN
