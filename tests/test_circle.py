from carecircle.circle import Circle, chat_name

CIRCLE = Circle.from_dict(
    {"parent": "Ma", "members": {"abhishek": ["Z+Security", "abhishekkumar2672"], "priya": []}}
)
DISCORD_ID = "@switch-discord-d9947352-c5c4-411c-82c7-3738fdc6977b-abhishekkumar2672:localhost"


def test_chat_name_from_discord_participant():
    assert chat_name(DISCORD_ID) == "abhishekkumar2672"


def test_chat_name_falls_back_to_localpart():
    assert chat_name("@switch-user-ab12:localhost") == "switch-user-ab12"


def test_identify_by_participant_id():
    assert CIRCLE.identify(None, DISCORD_ID) == "abhishek"


def test_identify_by_display_name_and_first_word():
    assert CIRCLE.identify("Z+Security") == "abhishek"
    assert CIRCLE.identify("Priya Sharma") == "priya"
    assert CIRCLE.identify("Cousin Vikram", "@x:y") is None
