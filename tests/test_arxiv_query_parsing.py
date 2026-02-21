from qldpcwatch.arxiv import build_search_query, parse_arxiv_id_and_version


def test_parse_arxiv_id_and_version_modern() -> None:
    arxiv_id, version = parse_arxiv_id_and_version("https://arxiv.org/abs/2401.01234v2")
    assert arxiv_id == "2401.01234"
    assert version == "v2"


def test_parse_arxiv_id_and_version_default_v1() -> None:
    arxiv_id, version = parse_arxiv_id_and_version("http://arxiv.org/abs/2401.01234")
    assert arxiv_id == "2401.01234"
    assert version == "v1"


def test_build_search_query_with_categories() -> None:
    query = build_search_query('all:"quantum LDPC" AND all:decoder', ["quant-ph", "cs.IT"])
    assert "cat:quant-ph" in query
    assert "cat:cs.IT" in query
    assert query.startswith("(")
