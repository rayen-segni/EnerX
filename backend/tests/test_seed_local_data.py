import unittest
from unittest.mock import call, patch

from seed_local_data import API_HOST, SeedError, require_loopback_url, run_seed


class LocalSeedScriptTests(unittest.TestCase):
    def test_default_api_url_targets_local_server(self) -> None:
        self.assertEqual(API_HOST, "http://localhost:8000")

    def test_only_loopback_is_allowed_by_default(self) -> None:
        require_loopback_url("http://localhost:8000", allow_remote=False)

        with self.assertRaisesRegex(SeedError, "only targets localhost"):
            require_loopback_url("https://example.com", allow_remote=False)

        require_loopback_url("https://example.com", allow_remote=True)

    @patch("seed_local_data.request_api")
    def test_seed_uses_live_api_flow_and_never_calls_production(
        self,
        mock_request_api,
    ) -> None:
        def response(_base_url, method, path, payload=None):
            if method == "GET" and path == "/":
                return {"status": "online"}
            if method == "GET" and path.startswith("/auth/"):
                user_id = int(path.rsplit("/", 1)[-1])
                return {"user_id": user_id, "hedera_account_id": f"0.0.{user_id}"}
            if method == "GET" and path == "/project/":
                return []
            if method == "PATCH":
                return {"id": payload["id"]}
            if method == "POST" and path == "/project/":
                return {"id": 42, "token_id": 17, "hedera_token_id": "0.0.123"}
            if method == "POST" and path == "/investment/":
                return {
                    "transaction_id": "0.0.1@1.1",
                    "total_supply": 65 if payload["user_id"] == 2 else 100,
                    "project_status": "funding" if payload["user_id"] == 2 else "active",
                }
            if method == "POST" and path == "/marketplace/list":
                return {"id": 3}
            if method == "POST" and path == "/marketplace/list/buy":
                return {"transaction_id": "0.0.2@2.2"}
            if method == "GET" and path == "/project/1":
                return [{"id": 42}]
            if method == "GET" and path in {"/investment/2", "/investment/3"}:
                return [{"project_id": 42}]
            self.fail(f"Unexpected API request: {method} {path}")

        mock_request_api.side_effect = response
        result = run_seed(
            "http://localhost:8000",
            "Test API Seed Project",
            "10000.00",
            confirmed=True,
        )

        self.assertEqual(result["project_id"], 42)
        self.assertEqual(result["token_supply"], 100)
        self.assertEqual(result["listing_id"], 3)
        self.assertEqual(result["investor_history_counts"], {"2": 1, "3": 1})
        self.assertNotIn("/prod", [request.args[2] for request in mock_request_api.call_args_list])
        self.assertIn(
            call(
                "http://localhost:8000",
                "POST",
                "/marketplace/list/buy",
                {"user_id": 3, "listing_id": 3, "amount": 5},
            ),
            mock_request_api.call_args_list,
        )


if __name__ == "__main__":
    unittest.main()
