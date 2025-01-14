import requests
from phi.tools import Toolkit


class DSLTools(Toolkit):
    base_url = "https://gi.rss3.io"

    def __init__(self):
        super().__init__(name="dsl_tools")

        self.register(self.fetch_decentralized_feed)

    def fetch_decentralized_feed(self, address: str, type: str = "all") -> str:
        """
        Fetch feed activities for a given address and activity type.

        Args:
            address (str): The wallet address or blockchain domain name to fetch activities for
            type (str): The type of activities to fetch (all, post, comment, share)
        Returns:
            A string containing the fetched activities formatted using FEED_PROMPT
        """
        url = f"{self.base_url}/decentralized/{address}?limit=5&action_limit=10&tag=social"
        if type in ["post", "comment", "share"]:
            url += f"&type={type}"

        headers = {"Accept": "application/json"}
        data = requests.get(url, headers=headers).json()

        result = FEED_PROMPT.format(activities_data=data)
        return result


FEED_PROMPT = """
Here are the raw activities:

{activities_data}

- Before answering, please first summarize how many actions the above activities have been carried out.
- Display the key information in each operation, such as time, author, specific content, etc., and display this information in a markdown list format.
- Finally, give a specific answer to the question.
"""
