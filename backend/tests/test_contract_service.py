import unittest

from hedera.contract_service import _response_code_name


class ResponseCodeNameTests(unittest.TestCase):
    def test_numeric_success_response_code_is_decoded(self) -> None:
        transaction_status = _response_code_name(22)
        self.assertEqual(transaction_status, "SUCCESS")
        self.assertFalse(transaction_status != "SUCCESS")

    def test_none_status_is_reported_as_an_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "did not include a status"):
            _response_code_name(None)


if __name__ == "__main__":
    unittest.main()
