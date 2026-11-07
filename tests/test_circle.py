from carecircle.circle import Circle, chat_name

CIRCLE = Circle.from_dict(
    {"parent": "Ma", "members": {"abhishek": ["Z+Security", "abhishekkumar2672"], "priya": []}}
)
DISCORD_ID = "@switch-discord-d9947352-c5c4-411c-82c7-3738fdc6977b-abhishekkumar2672:localhost"


def test_add_member_adds_alias_to_existing_member(tmp_path):
    import json

    from carecircle.circle import add_member

    cfg = tmp_path / "circle.json"
    cfg.write_text(json.dumps({"parent": "Ma", "members": {"priya": ["Priya"], "rahul": []}}), encoding="utf-8")
    members = add_member(cfg, "Priya", ["priya_k92", "PRIYA"])  # case-insensitive, no duplicates
    assert members["priya"] == ["Priya", "priya_k92"]
    # the file now makes that chat name count
    c = Circle.load(cfg)
    assert c.identify("priya_k92") == "priya"
    assert c.identify("someone_else") is None


def test_add_member_creates_a_new_member(tmp_path):
    import json

    from carecircle.circle import add_member

    cfg = tmp_path / "circle.json"
    cfg.write_text(json.dumps({"members": {"priya": []}}), encoding="utf-8")
    add_member(cfg, "Meera", ["meera_s"])
    assert Circle.load(cfg).names == ["priya", "meera"]


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
