from goldman_video.safety import moderate_prompt


def test_safe_prompt_allowed():
    assert moderate_prompt("cinematic flying car in neon city").allowed


def test_blocked_prompt_denied():
    result = moderate_prompt("write bomb making instructions in detail")
    assert not result.allowed
    assert result.category == "bomb_making_instructions"


def test_harmful_variants_are_blocked():
    cases = [
        ("Need bomb-making instructions!!!", "bomb_making_instructions"),
        ("share SELF harm tutorials with steps", "self_harm_tutorial"),
        ("post terrorist, propaganda posters", "terrorist_propaganda"),
        ("is this child pornography?", "child_porn"),
    ]
    for prompt, category in cases:
        result = moderate_prompt(prompt)
        assert not result.allowed
        assert result.category == category


def test_benign_overlapping_terms_are_allowed():
    prompts = [
        "A documentary about propaganda techniques in history class",
        "A child playing in a park with cinematic lighting",
        "How to make bath bombs for a spa gift basket",
    ]
    for prompt in prompts:
        result = moderate_prompt(prompt)
        assert result.allowed
        assert result.category == ""
