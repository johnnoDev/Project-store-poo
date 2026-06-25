import logging
import functools
from datetime import datetime

logger = logging.getLogger(__name__)


def audit_action(action_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user if request.user.is_authenticated else 'anonymous'
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            timestamp = datetime.now().isoformat()
            msg = (
                f'[AUDIT] action={action_name} user={user} '
                f'ip={ip} method={request.method} '
                f'path={request.path} timestamp={timestamp}'
            )
            logger.info(msg)
            print(msg)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
