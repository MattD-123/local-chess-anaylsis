from services.openings import OpeningService


def test_parse_openings_tsv():
    content = "eco\tname\tpgn\tuci\tfen\nA00\tPolish Opening\t1. b4\tb2b4\tfen1\n"
    rows = OpeningService.parse_openings_tsv(content)
    assert rows == [("A00", "Polish Opening", "1. b4", "b2b4", "fen1")]


def test_parse_openings_tsv_with_pgn_only_derives_uci_and_fen():
    content = "eco\tname\tpgn\nA00\tAmar Opening\t1. Nh3\n"
    rows = OpeningService.parse_openings_tsv(content)
    assert rows
    eco, name, pgn, uci, fen = rows[0]
    assert eco == "A00"
    assert name == "Amar Opening"
    assert pgn == "1. Nh3"
    assert uci == "g1h3"
    assert fen.startswith("rnbqkbnr/pppppppp/8/8/8/7N/PPPPPPPP/RNBQKB1R b KQkq -")
