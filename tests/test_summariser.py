from unittest.mock import MagicMock
from summariser import summarise_article


def _make_article(body_text="Full article body about student housing demand."):
    return {
        "url": "https://pbsanews.co.uk/article-1",
        "headline": "Student Demand Rises",
        "body_text": body_text,
        "summary": "",
    }


def test_summarise_returns_gemini_response(mocker):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "Demand for PBSA rose 12% this year."
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    mocker.patch("google.generativeai.configure")
    result = summarise_article(_make_article(), api_key="fake-key")
    assert result["summary"] == "Demand for PBSA rose 12% this year."


def test_summarise_falls_back_on_api_error(mocker):
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API error")
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    mocker.patch("google.generativeai.configure")
    result = summarise_article(_make_article(body_text="A" * 300), api_key="fake-key")
    assert result["summary"] == "A" * 200


def test_summarise_skips_article_with_empty_body(mocker):
    mocker.patch("google.generativeai.configure")
    mock_model = MagicMock()
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    result = summarise_article(_make_article(body_text=""), api_key="fake-key")
    mock_model.generate_content.assert_not_called()
    assert result["summary"] == ""
