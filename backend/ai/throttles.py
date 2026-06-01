from rest_framework.throttling import UserRateThrottle


class ChatUserRateThrottle(UserRateThrottle):
    scope = "chat_user"

    def wait(self):
        return super().wait()
