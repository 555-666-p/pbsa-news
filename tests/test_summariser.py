from unittest.mock import MagicMock
from summariser import summarise_article


def _make_article(body_text="Full article body about student housing demand."):
    return {
        "url": "https://pbsanews.co.uk/article-1",
        "headline": "Student Demand Rises",
        "body_text": body_text,
        "summary": "",
    }


def test_summarise_returns_deepseek_response(mocker):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Demand for PBSA rose 12% this year."
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch("summariser.OpenAI", return_value=mock_client)
    result = summarise_article(_make_article(), api_key="fake-key")
    assert result["summary"] == "Demand for PBSA rose 12% this year."


def test_summarise_falls_back_on_api_error(mocker):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")
    mocker.patch("summariser.OpenAI", return_value=mock_client)
    result = summarise_article(_make_article(body_text="A" * 300), api_key="fake-key")
    assert result["summary"] == "A" * 200


def test_summarise_skips_article_with_empty_body(mocker):
    mock_client = MagicMock()
    mocker.patch("summariser.OpenAI", return_value=mock_client)
    result = summarise_article(_make_article(body_text=""), api_key="fake-key")
    mock_client.chat.completions.create.assert_not_called()
    assert result["summary"] == ""
