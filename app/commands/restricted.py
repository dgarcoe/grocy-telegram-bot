from functools import wraps

def restricted(func):
    @wraps(func)
    def wrapped(self,update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in self._config.TELEGRAM_USER_IDS.value:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(self,update, context, *args, **kwargs)
    return wrapped