from pathlib import Path

from services.action_registry import get_action, get_all_actions
from utils.content import CONTENT_DIR, load_list, load_pairs, load_text, _parse


def test_parser_records_meta_items_and_continuations():
    recs = _parse("# T\n\nintro\n\n## hug\ncategory: affection\nxp: 5\n- one {a}\n  continued\n- two\n")
    r = recs["hug"]
    assert r.meta == {"category": "affection", "xp": "5"}
    assert r.items == ["one {a} continued", "two"]


def test_plain_bullet_file_is_anonymous_section():
    assert _parse("# x\n- a\n- b\n")[""].items == ["a", "b"]


def test_every_action_has_templates_and_valid_placeholders():
    actions = get_all_actions()
    assert len(actions) == 62
    allowed = {"author", "target", "target_mention", "author_pronoun", "author_pronoun_obj", "author_possessive",
               "target_pronoun", "target_pronoun_obj", "target_possessive"}
    import string
    for a in actions.values():
        assert a.response_templates, a.name
        for t in a.response_templates:
            fields = {f for _, f, _, _ in string.Formatter().parse(t) if f}
            assert fields <= allowed, (a.name, fields - allowed)


def test_intimate_actions_are_separated():
    assert get_action("hug").category != "intimate"
    assert any(a.category == "intimate" for a in get_all_actions().values())


def test_pair_content_is_well_formed():
    for path, width in [("couple/would_you_rather.md", 2), ("couple/this_or_that.md", 2), ("couple/emoji_puzzles.md", 2)]:
        rows = load_pairs(path)
        assert len(rows) >= 10 and all(len(r) == width and all(r) for r in rows), path
    for path in ("couple/trivia.md", "couple/compatibility.md", "couple/know_me.md"):
        assert all(len(r) >= 3 for r in load_pairs(path)), path
    for path in ("couple/truth.md", "couple/dare.md", "couple/compliments.md", "couple/daily_questions.md", "couple/words.md"):
        assert len(load_list(path)) >= 8, path


def test_trivia_correct_answer_is_first_column_and_options_distinct():
    for row in load_pairs("couple/trivia.md"):
        assert len(set(row[1:])) == len(row[1:]), row


def test_persona_prompt_loads_with_placeholders():
    text = load_text("persona/system_prompt.md")
    assert text.startswith("You are writing") and "{persona}" in text and "Placeholders" not in text


def test_all_content_files_exist_and_nonempty():
    for p in Path(CONTENT_DIR).rglob("*.md"):
        assert p.read_text(encoding="utf-8").strip(), p


def test_roleplay_has_no_cooldowns():
    import pathlib
    for path in pathlib.Path(CONTENT_DIR, "roleplay").glob("*.md"):
        assert "cooldown" not in path.read_text(encoding="utf-8").lower(), path
    assert not hasattr(next(iter(get_all_actions().values())), "cooldown_seconds")
