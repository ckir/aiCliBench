from ai_cli import build_parser


def test_cli_imports():
    import ai_cli

    assert ai_cli is not None


def test_cli_parser_commands():
    parser = build_parser()
    assert parser.parse_args(["health"]).command == "health"
    assert parser.parse_args(["tools"]).command == "tools"
