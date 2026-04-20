from enum import Enum

class ChangeCode(str, Enum):
    """
    Enumeration representing various types of user account changes.

    This class provides constant values for different types of account-related updates or
    actions. It can be used to standardize the representation of these changes across
    the application, ensuring consistency and readability in the code.

    :ivar PASSWORD_RESET: User password has been reset or changed.
    :ivar EMAIL_CHANGE: User email address has been modified.
    :ivar ADDRESS_UPDATE: User physical or mailing address has been updated.
    :ivar PERMISSION_GRANT: New permissions or access rights have been granted to the user.
    :ivar STATUS_INACTIVE: User account status has been set to inactive.
    :ivar LIMIT_INCREASE: User's operational or financial limit has been increased.
    """
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_CHANGE = "EMAIL_CHANGE"
    ADDRESS_UPDATE = "ADDRESS_UPDATE"
    PERMISSION_GRANT = "PERMISSION_GRANT"
    STATUS_INACTIVE = "STATUS_INACTIVE"
    LIMIT_INCREASE = "LIMIT_INCREASE"
