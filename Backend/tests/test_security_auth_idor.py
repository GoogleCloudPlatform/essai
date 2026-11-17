# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Regression guards for CWE-306 (missing auth), CWE-639 (IDOR), and Cloud Run IaC."""

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.auth as auth_module
import app.crud as crud_pkg
import app.database as database_module
import app.models as models
from app.config import get_settings
from app.main import app
from app.security import reset_rate_limiter

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_AUDIENCE = "https://essai-backend.internal.example"


def sample_inbound_payload(professor_id: str = "prof-1") -> dict:
    return {
        "TokenRedacao": "tok-1",
        "DescDependencia": "Estadual",
        "IdMunicipio": "1",
        "DescMunicipio": "Curitiba",
        "IdNRE": "1",
        "DescNRE": "NRE",
        "IdEscola": "10",
        "DescEscola": "Escola Teste",
        "IdCurso": "1",
        "DescCurso": "Medio",
        "IdTurma": "A",
        "IdTurno": "M",
        "DescTurno": "Manha",
        "IdEtapa": "3",
        "DescEtapa": "3a serie",
        "IdSeriacao": "3",
        "DescSeriacao": "3o ano",
        "IdDisciplina": "LP",
        "DescDisciplina": "Portugues",
        "IdProfessor": professor_id,
        "NomeProfessor": "Prof Teste",
        "IdAluno": "student-1",
        "IdTema": "1",
        "DescTema": "Tema",
        "IdTipo": "1",
        "DescricaoTipo": "ENEM",
        "IdGenero": "1",
        "DescricaoGenero": "Dissertativo",
        "IdProposta": "1",
        "MinPalavras": 100,
        "MaxPalavras": 1000,
        "TitleTema": "Tema Teste",
        "DescricaoPedido": "Escreva uma redacao",
        "TextosMotivadores": "Texto motivador",
        "TituloRedacao": "Titulo",
        "Redacao": "Texto da redacao do estudante " * 10,
    }


def sample_feedback_payload(req_id: uuid.UUID, professor_id: str = "prof-1") -> dict:
    return {
        "idCorrecao": str(req_id),
        "idProfessor": professor_id,
        "criteria_1": {"nota": 160, "justificativa": "Bom", "IsModified": False},
        "criteria_2": {"nota": 160, "justificativa": "Bom", "IsModified": False},
        "criteria_3": {"nota": 120, "justificativa": "Regular", "IsModified": True},
        "criteria_4": {"nota": 160, "justificativa": "Bom", "IsModified": False},
        "criteria_5": {"nota": 200, "justificativa": "Otimo", "IsModified": False},
        "final_reason": {"nota": 640, "justificativa": "Resumo", "IsModified": False},
        "ai_grading": 9,
        "general_feedback_ia": "Boa avaliacao",
    }


def build_unsigned_alg_none_jwt() -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=")
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {
                "iss": "https://accounts.google.com",
                "aud": TEST_AUDIENCE,
                "sub": "forged-attacker",
                "email": "attacker@example.com",
                "email_verified": True,
                "exp": 4102444800,
            }
        ).encode()
    ).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}."


class BackendSecurityAuthAndIDORTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        database_module.set_engine(self.engine)

        self.published_ids: list[str] = []
        self._orig_submit_to_queue = crud_pkg.submit_to_queue
        crud_pkg.submit_to_queue = lambda data: self.published_ids.append(str(data.id))

        self.env_patcher = patch.dict(
            os.environ,
            {
                "OIDC_AUDIENCE": TEST_AUDIENCE,
                "ALLOWED_CALLER_EMAILS": "",
                "RATE_LIMIT_REQUESTS": "60",
                "RATE_LIMIT_WINDOW_SECONDS": "60",
            },
            clear=False,
        )
        self.env_patcher.start()
        get_settings.cache_clear()
        reset_rate_limiter()

        self.client = TestClient(app)

        self.tokens = {
            "token-victim": {
                "iss": "https://accounts.google.com",
                "aud": TEST_AUDIENCE,
                "sub": "sub-victim",
                "email": "victim@school.edu.br",
                "email_verified": True,
            },
            "token-attacker": {
                "iss": "https://accounts.google.com",
                "aud": TEST_AUDIENCE,
                "sub": "sub-attacker",
                "email": "attacker@school.edu.br",
                "email_verified": True,
            },
            "token-unverified-email": {
                "iss": "https://accounts.google.com",
                "aud": TEST_AUDIENCE,
                "sub": "sub-unverified",
                "email": "victim@school.edu.br",
                "email_verified": False,
            },
            "token-bad-issuer": {
                "iss": "https://evil.example",
                "aud": TEST_AUDIENCE,
                "sub": "sub-evil",
            },
        }

    def tearDown(self) -> None:
        crud_pkg.submit_to_queue = self._orig_submit_to_queue
        database_module.set_engine(None)
        self.env_patcher.stop()
        get_settings.cache_clear()
        reset_rate_limiter()

    def _fake_verify(self, token: str, audience: str) -> dict:
        if audience != TEST_AUDIENCE or token not in self.tokens:
            raise ValueError("Invalid token")
        return self.tokens[token]

    def _seed_correcao(self, req_id: uuid.UUID) -> None:
        with Session(self.engine) as session:
            session.add(
                models.Correcao(
                    id_requisicao=req_id,
                    started_at=datetime.now(timezone.utc),
                    competencia_2_nota=160,
                    competencia_2_justificativa='{"compreensao": "Boa compreensao"}',
                    competencia_3_nota=160,
                    competencia_3_justificativa='{"argumentos": "Bons argumentos"}',
                    competencia_4_nota=120,
                    competencia_4_justificativa='{"coesao": "Coesao regular"}',
                    competencia_5_nota=200,
                    competencia_5_justificativa='{"proposta": "Proposta completa"}',
                    justificativa_final_nota=640,
                    justificativa_final_justificativa="Feedback confidencial",
                    Plagio=None,
                    Validacao="Válida",
                )
            )
            session.commit()

    def test_health_endpoint_remains_accessible_with_security_headers(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "running"})
        self.assertEqual(resp.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(resp.headers.get("x-frame-options"), "DENY")
        self.assertEqual(resp.headers.get("cache-control"), "no-store")
        self.assertIn("default-src 'none'", resp.headers.get("content-security-policy", ""))
        self.assertIn("camera=()", resp.headers.get("permissions-policy", ""))

    def test_unauthenticated_requests_rejected_on_all_grading_and_feedback_routes(
        self,
    ) -> None:
        some_id = uuid.uuid4()

        r_post = self.client.post("/grade", json=sample_inbound_payload())
        self.assertEqual(r_post.status_code, 401)
        self.assertEqual(r_post.headers.get("www-authenticate"), "Bearer")
        self.assertEqual(self.published_ids, [])

        r_get = self.client.get(f"/grade/{some_id}")
        self.assertEqual(r_get.status_code, 401)

        r_bulk = self.client.post("/grade/bulk", json=[str(some_id)])
        self.assertEqual(r_bulk.status_code, 401)

        r_fb = self.client.post("/feedback", json=sample_feedback_payload(some_id))
        self.assertEqual(r_fb.status_code, 401)

    def test_fail_closed_when_oidc_audience_unconfigured(self) -> None:
        with patch.dict(os.environ, {"OIDC_AUDIENCE": ""}, clear=False):
            get_settings.cache_clear()
            resp = self.client.get(
                f"/grade/{uuid.uuid4()}",
                headers={"Authorization": "Bearer token-victim"},
            )
        self.assertEqual(resp.status_code, 503)

    def test_alg_none_unsigned_jwt_is_rejected_by_real_verifier(self) -> None:
        forged = build_unsigned_alg_none_jwt()
        resp = self.client.get(
            f"/grade/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {forged}"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_invalid_scheme_and_untrusted_issuer_are_rejected(self) -> None:
        resp_basic = self.client.get(
            f"/grade/{uuid.uuid4()}",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        self.assertEqual(resp_basic.status_code, 401)

        with patch.object(auth_module, "verify_oidc_token", side_effect=self._fake_verify):
            resp_iss = self.client.get(
                f"/grade/{uuid.uuid4()}",
                headers={"Authorization": "Bearer token-bad-issuer"},
            )
        self.assertEqual(resp_iss.status_code, 401)

    def test_allowed_caller_emails_enforces_verified_allowlist(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"ALLOWED_CALLER_EMAILS": "victim@school.edu.br"},
                clear=False,
            ),
            patch.object(auth_module, "verify_oidc_token", side_effect=self._fake_verify),
        ):
            get_settings.cache_clear()

            # Different verified email -> 403
            r_other = self.client.post(
                "/grade",
                json=sample_inbound_payload(),
                headers={"Authorization": "Bearer token-attacker"},
            )
            self.assertEqual(r_other.status_code, 403)

            # Matching email but email_verified=False -> 403
            r_unverified = self.client.post(
                "/grade",
                json=sample_inbound_payload(),
                headers={"Authorization": "Bearer token-unverified-email"},
            )
            self.assertEqual(r_unverified.status_code, 403)

            # Verified allow-listed email -> 201
            r_allowed = self.client.post(
                "/grade",
                json=sample_inbound_payload(),
                headers={"Authorization": "Bearer token-victim"},
            )
            self.assertEqual(r_allowed.status_code, 201)

    def test_cross_caller_idor_blocked_on_get_bulk_and_feedback(self) -> None:
        with patch.object(auth_module, "verify_oidc_token", side_effect=self._fake_verify):
            # Victim submits an essay
            r_create = self.client.post(
                "/grade",
                json=sample_inbound_payload(professor_id="prof-victim"),
                headers={"Authorization": "Bearer token-victim"},
            )
            self.assertEqual(r_create.status_code, 201)
            victim_req_id = uuid.UUID(r_create.json()["id"])

            # Attacker submits their own essay
            r_attacker_create = self.client.post(
                "/grade",
                json=sample_inbound_payload(professor_id="prof-attacker"),
                headers={"Authorization": "Bearer token-attacker"},
            )
            self.assertEqual(r_attacker_create.status_code, 201)
            attacker_req_id = uuid.UUID(r_attacker_create.json()["id"])

            # While still in progress: victim sees IN_PROGRESS, attacker gets 404
            self.assertEqual(
                self.client.get(
                    f"/grade/{victim_req_id}",
                    headers={"Authorization": "Bearer token-victim"},
                ).status_code,
                200,
            )
            self.assertEqual(
                self.client.get(
                    f"/grade/{victim_req_id}",
                    headers={"Authorization": "Bearer token-attacker"},
                ).status_code,
                404,
            )

            # Seed finished grading for victim's essay
            self._seed_correcao(victim_req_id)

            # Victim can read their own grading result
            r_owner_get = self.client.get(
                f"/grade/{victim_req_id}",
                headers={"Authorization": "Bearer token-victim"},
            )
            self.assertEqual(r_owner_get.status_code, 200)
            self.assertEqual(
                r_owner_get.json()["final_reason"]["reason"], "Feedback confidencial"
            )

            # Attacker CANNOT read victim's grading result via GET /grade/{id}
            r_idor_get = self.client.get(
                f"/grade/{victim_req_id}",
                headers={"Authorization": "Bearer token-attacker"},
            )
            self.assertEqual(r_idor_get.status_code, 404)

            # Attacker CANNOT read victim's grading result via POST /grade/bulk
            r_idor_bulk = self.client.post(
                "/grade/bulk",
                json=[str(victim_req_id), str(attacker_req_id)],
                headers={"Authorization": "Bearer token-attacker"},
            )
            self.assertEqual(r_idor_bulk.status_code, 200)
            body = r_idor_bulk.json()
            returned_ids = [item["id"] for item in body["correcoes"]]
            error_ids = [item["id"] for item in body["erros"]]
            self.assertEqual(returned_ids, [str(attacker_req_id)])
            self.assertEqual(error_ids, [str(victim_req_id)])
            self.assertEqual(body["erros"][0]["error_message"], "Id não encontrado")

            # Attacker CANNOT submit feedback on victim's essay
            r_idor_fb = self.client.post(
                "/feedback",
                json=sample_feedback_payload(victim_req_id, professor_id="prof-victim"),
                headers={"Authorization": "Bearer token-attacker"},
            )
            self.assertEqual(r_idor_fb.status_code, 404)

            # Victim CAN submit feedback on their own essay
            r_owner_fb = self.client.post(
                "/feedback",
                json=sample_feedback_payload(victim_req_id, professor_id="prof-victim"),
                headers={"Authorization": "Bearer token-victim"},
            )
            self.assertEqual(r_owner_fb.status_code, 200)
            self.assertEqual(r_owner_fb.json()["status"], "success")

    def test_legacy_unowned_requisicao_fails_closed(self) -> None:
        legacy_req = models.Requisicao(**sample_inbound_payload(), owner_id=None)
        with Session(self.engine) as session:
            session.add(legacy_req)
            session.commit()
            session.refresh(legacy_req)
            legacy_id = legacy_req.id

        self._seed_correcao(legacy_id)

        with patch.object(auth_module, "verify_oidc_token", side_effect=self._fake_verify):
            resp = self.client.get(
                f"/grade/{legacy_id}",
                headers={"Authorization": "Bearer token-victim"},
            )
        self.assertEqual(resp.status_code, 404)

    def test_disallowed_http_methods_are_blocked(self) -> None:
        resp_delete = self.client.delete(f"/grade/{uuid.uuid4()}")
        self.assertEqual(resp_delete.status_code, 405)
        self.assertEqual(resp_delete.headers.get("x-content-type-options"), "nosniff")

        resp_put = self.client.put("/grade")
        self.assertEqual(resp_put.status_code, 405)

    def test_rate_limiting_enforced_per_caller(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"RATE_LIMIT_REQUESTS": "2", "RATE_LIMIT_WINDOW_SECONDS": "60"},
                clear=False,
            ),
            patch.object(auth_module, "verify_oidc_token", side_effect=self._fake_verify),
        ):
            get_settings.cache_clear()
            reset_rate_limiter()

            # 2 allowed requests for victim (even 404s count toward caller quota)
            for _ in range(2):
                r = self.client.get(
                    f"/grade/{uuid.uuid4()}",
                    headers={"Authorization": "Bearer token-victim"},
                )
                self.assertEqual(r.status_code, 404)

            # 3rd request from victim is throttled with 429
            r_limited = self.client.get(
                f"/grade/{uuid.uuid4()}",
                headers={"Authorization": "Bearer token-victim"},
            )
            self.assertEqual(r_limited.status_code, 429)
            self.assertIn("retry-after", r_limited.headers)

            # Distinct caller still has their own bucket
            r_other = self.client.get(
                f"/grade/{uuid.uuid4()}",
                headers={"Authorization": "Bearer token-attacker"},
            )
            self.assertEqual(r_other.status_code, 404)


class CloudRunTerraformSecurityGuardTests(unittest.TestCase):
    """Static IaC guards preventing regression back to public allUsers Cloud Run."""

    def test_cloudrun_main_tf_forbids_all_users_and_public_ingress(self) -> None:
        main_tf = (REPO_ROOT / "IAC" / "cloudrun" / "main.tf").read_text(encoding="utf-8")

        self.assertNotIn("allUsers", main_tf)
        self.assertNotIn("allAuthenticatedUsers", main_tf)
        self.assertIsNone(
            re.search(r'"run\.googleapis\.com/ingress"\s*[:=]\s*"all"', main_tf),
            "Backend Cloud Run must not hardcode run.googleapis.com/ingress = all",
        )
        self.assertIn('"run.googleapis.com/ingress" = var.ingress', main_tf)
        self.assertIn("members    = var.invoker_members", main_tf)
        self.assertIn('name  = "OIDC_AUDIENCE"', main_tf)

    def test_cloudrun_variables_validate_ingress_and_invoker_members(self) -> None:
        cloudrun_vars = (REPO_ROOT / "IAC" / "cloudrun" / "variable.tf").read_text(
            encoding="utf-8"
        )
        root_vars = (REPO_ROOT / "IAC" / "variables.tf").read_text(encoding="utf-8")

        for content in (cloudrun_vars, root_vars):
            self.assertIn("internal-and-cloud-load-balancing", content)
            self.assertIn("allUsers", content)  # present in validation rejection guard
            self.assertIn("allAuthenticatedUsers", content)
            self.assertIn("validation {", content)


if __name__ == "__main__":
    unittest.main()
