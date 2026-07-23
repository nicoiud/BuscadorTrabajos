from app.api.v1 import autofill as autofill_api


async def test_answer_form_field_returns_generated_answer(client, monkeypatch):
    async def fake_generate_field_answer(field_label: str, profile_text: str) -> str:
        assert field_label == "¿Por qué te interesa este puesto?"
        assert profile_text == "Dev backend con 5 años de experiencia."
        return "Porque busco un desafío técnico más grande."

    monkeypatch.setattr(autofill_api, "generate_field_answer", fake_generate_field_answer)

    response = await client.post(
        "/api/v1/autofill/answer",
        json={
            "field_label": "¿Por qué te interesa este puesto?",
            "profile_text": "Dev backend con 5 años de experiencia.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "Porque busco un desafío técnico más grande."}
