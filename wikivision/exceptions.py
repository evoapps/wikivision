
class IncompleteRevisionHistoryError(Exception):
    """All revisions must be present for recreating article histories."""


class MissingRequiredColumnError(Exception):
    """An expected column was not present."""
