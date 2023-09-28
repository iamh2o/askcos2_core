import json
import os
import requests
import time
import unittest

V2_HOST = os.environ.get("V2_HOST", "0.0.0.0")
V2_PORT = os.environ.get("V2_PORT", "9100")


class ReactionClassificationTest(unittest.TestCase):
    """Test class for Site Fast Filter wrapper"""

    @classmethod
    def setUpClass(cls) -> None:
        """This method is run once before all tests in this class."""
        cls.session = requests.Session()
        cls.v2_url = f"http://{V2_HOST}:{V2_PORT}/api/reaction_classification"

    def get_result(self, task_id: str, timeout: int = 20):
        """Retrieve celery task output"""
        # Try to get result 10 times in 2 sec intervals
        for _ in range(timeout // 2):
            response = self.session.get(f"{self.v2_url}/retrieve?task_id={task_id}")
            result = response.json()
            if result.get("complete"):
                return result
            else:
                if result.get("failed"):
                    self.fail("Celery task failed.")
                else:
                    time.sleep(2)

    def test_1(self):
        case_file = "tests/wrappers/reaction_classification/default_test_case_1.json"
        with open(case_file, "r") as f:
            data = json.load(f)

        # get sync response
        response_sync = self.session.post(
            f"{self.v2_url}/call_sync", json=data
        ).json()

        # get async response
        task_id = self.session.post(
            f"{self.v2_url}/call_async", json=data
        ).json()
        time.sleep(10)
        response_async = self.session.get(
            f"{self.v2_url}/retrieve?task_id={task_id}"
        ).json()

        for response in [response_sync, response_async]:
            self.assertEqual(response["status_code"], 200)
            print(response["result"])
            self.assertIsInstance(response["result"], list)

        self.assertEqual(response_sync, response_async)
