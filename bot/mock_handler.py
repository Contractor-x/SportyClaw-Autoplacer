from dataclasses import dataclass


@dataclass
class MockUser:
    id: int
    full_name: str = "Mock User"

    @property
    def first_name(self):
        return self.full_name.split()[0]


class MockMessage:
    def __init__(self, text: str, user_id: int = 42, full_name: str = "Mock User"):
        self.from_user = MockUser(id=user_id, full_name=full_name)
        self.text = text
        self.reply_texts: list[str] = []

    async def reply_text(self, text: str):
        self.reply_texts.append(text)
        return text


class MockUpdate:
    def __init__(self, message: MockMessage):
        self.message = message


def create_mock_update(text: str, user_id: int = 42, full_name: str = "Mock User") -> MockUpdate:
    return MockUpdate(MockMessage(text=text, user_id=user_id, full_name=full_name))
