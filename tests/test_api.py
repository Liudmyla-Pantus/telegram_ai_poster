def test_fastapi_health_and_docs(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "test_mode": True}
    assert client.get("/docs").status_code == 200


def test_sources_and_keywords_crud(client):
    source = client.post("/api/sources/", json={
        "type": "site", "name": "Example", "url": "https://example.com", "language": "uk"
    })
    assert source.status_code == 201
    source_id = source.json()["id"]
    assert client.patch(f"/api/sources/{source_id}", json={"enabled": False}).json()["enabled"] is False
    assert len(client.get("/api/sources/").json()) == 1

    keyword = client.post("/api/keywords/", json={"word": "Python"})
    assert keyword.status_code == 201
    assert client.post("/api/keywords/", json={"word": "Python"}).status_code == 409
    assert client.delete(f"/api/keywords/{keyword.json()['id']}").status_code == 204


def test_news_save_filter_and_duplicate_protection(client):
    client.post("/api/keywords/", json={"word": "штучний інтелект"})
    payload = {
        "title": "Новини штучного інтелекту",
        "url": "https://example.com/ai",
        "summary": "Вийшла нова модель",
        "source": "Example",
        "language": "uk",
    }
    first = client.post("/api/news/", json=payload)
    assert first.status_code == 201
    assert first.json()["is_relevant"] is True
    second = client.post("/api/news/", json=payload)
    assert second.status_code == 409
    assert len(client.get("/api/news/").json()) == 1


def test_generation_in_safe_test_mode(client):
    response = client.post("/api/generate/", json={"title": "Тест", "text": "Текст навчальної новини"})
    assert response.status_code == 200
    body = response.json()
    assert body["test_mode"] is True
    assert "📰 Тест" in body["generated_text"]


def test_language_filter(client):
    response = client.post("/api/news/", json={
        "title": "English language item", "summary": "A sufficiently long summary",
        "source": "Example", "language": "en",
    })
    assert response.status_code == 201
    assert response.json()["is_relevant"] is False
