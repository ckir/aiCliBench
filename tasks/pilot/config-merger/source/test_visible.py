from config_merger import deep_merge


def test_strategy_validation():
    try:
        deep_merge({}, {}, list_strategy="invalid")
        assert False, "Should raise ValueError"
    except ValueError:
        pass
