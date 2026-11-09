"""ツールのテスト（LLMもAPIキーも使わない）。"""

import json

from app import tools


def test_glossary_ids_are_unique_and_related_links_exist():
    terms = tools.load_glossary()
    ids = [t["id"] for t in terms]
    assert len(ids) == len(set(ids))
    for t in terms:
        for r in t["related"]:
            assert r in ids, f"{t['id']} の related に存在しない id: {r}"


def test_search_finds_term_by_name_and_alias():
    for query in ["LoRA", "lora", "Low-Rank Adaptation"]:
        hits = json.loads(tools.search_glossary(query))
        assert hits[0]["term"] == "LoRA", query


def test_search_finds_course_specific_term():
    hits = json.loads(tools.search_glossary("lecNN-start"))
    assert hits[0]["term"] == "lecNN-start タグ"


def test_search_limits_number_of_results():
    hits = json.loads(tools.search_glossary("エージェント"))
    assert 1 <= len(hits) <= tools.MAX_RESULTS


def test_search_reports_not_found():
    assert "見つかりませんでした" in tools.search_glossary("存在しない用語xyz")


def test_lecture_summary():
    assert "エージェント" in tools.get_lecture_summary(3)
    assert "まだありません" in tools.get_lecture_summary(99)


def test_make_quiz_picks_term_from_requested_lecture():
    terms_by_lecture = {}
    for t in tools.load_glossary():
        terms_by_lecture.setdefault(t["lecture"], set()).add(t["term"])
    for lecture, terms in terms_by_lecture.items():
        quiz = json.loads(tools.make_quiz(lecture))
        assert quiz["lecture"] == lecture
        assert quiz["term"] in terms
        assert quiz["term"] in quiz["question"]
        assert quiz["answer"]


def test_make_quiz_answer_matches_glossary_definition():
    quiz = json.loads(tools.make_quiz(2))
    hits = json.loads(tools.search_glossary(quiz["term"]))
    assert quiz["answer"] in [h["definition"] for h in hits]


def test_make_quiz_reports_lecture_without_terms():
    message = tools.make_quiz(99)
    assert "用語集にありません" in message
    assert "1" in message  # 問題を作れる回を案内する


def test_default_question_of_lecture1_is_answerable_from_glossary():
    """第1回の既定の質問（app.ask）は、第3回のエージェントが用語集で正しく答えられること。"""
    from app.ask import DEFAULT_QUESTION

    assert "3レベル" in DEFAULT_QUESTION
    hits = json.loads(tools.search_glossary("3レベル"))
    assert hits[0]["term"] == "宿題の3レベル"
