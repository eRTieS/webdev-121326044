class ServiceError(Exception):
    """A rule refused the request. The message is shown to the user as it is."""


class BlockedUserError(ServiceError):
    pass


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass
