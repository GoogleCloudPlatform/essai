# API

API Python escrita com FastAPI para registro de requisições de correção, consulta de resultados e envio de feedback.

## Autenticação e Autorização

- Todos os endpoints de negócio (`POST /grade`, `GET /grade/{id}`, `POST /grade/bulk`, `POST /feedback`) exigem um token Google OIDC Bearer (`Authorization: Bearer <id_token>`) validado no servidor com `OIDC_AUDIENCE` obrigatório (fail-closed: retorna `503` se `OIDC_AUDIENCE` não estiver configurado e `401` para tokens ausentes ou inválidos).
- Opcionalmente, `ALLOWED_CALLER_EMAILS` (lista separada por vírgulas) restringe o acesso a e-mails verificados específicos (`403` caso contrário).
- O controle de propriedade (`owner_id`, derivado do claim `sub` do token verificado) é aplicado nas consultas ao banco para impedir acesso entre usuários diferentes (IDOR) em `GET /grade/{id}`, `POST /grade/bulk` e `POST /feedback`.
- No Terraform (`IAC/cloudrun/main.tf`), o serviço Cloud Run utiliza ingress restrito (`internal-and-cloud-load-balancing`) e `roles/run.invoker` apenas para principais explícitos (nunca `allUsers`).

## Testes

```bash
PYTHONPATH=src uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check src tests
```

# DB

PostgreSQL 15 (instâncias existentes devem aplicar `ALTER TABLE requisicao ADD COLUMN owner_id VARCHAR;` e criar índice em `owner_id`).
