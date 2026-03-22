import os
import re
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

LEETCODE_QUERY = """
query questionOfToday {
  activeDailyCodingChallengeQuestion {
    date
    link
    question {
      frontendQuestionId: questionFrontendId
      title
      difficulty
      topicTags {
        name
      }
      acRate
      isPaidOnly
      content
    }
  }
}
"""


def strip_html(html):
    html = re.sub(r'<pre>(.*?)</pre>', lambda m: '\n```\n' + m.group(1) + '\n```\n', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', '', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&lt;', '<', html)
    html = re.sub(r'&gt;', '>', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&quot;', '"', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()


def fetch_daily_problem():
    response = requests.post(
        "https://leetcode.com/graphql",
        json={"query": LEETCODE_QUERY},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data["data"]["activeDailyCodingChallengeQuestion"]


def build_message(problem_data):
    q = problem_data["question"]
    number = q["frontendQuestionId"]
    title = q["title"]
    difficulty = q["difficulty"]
    link = f"https://leetcode.com{problem_data['link']}"
    tags = ", ".join(tag["name"] for tag in q["topicTags"]) or "N/A"
    acceptance = f"{q['acRate']:.1f}%"
    date = problem_data["date"]
    is_paid = q["isPaidOnly"]
    description = strip_html(q["content"] or "")
    if len(description) > 2900:
        description = description[:2900] + "...\n\n_(truncated — see full problem on LeetCode)_"

    emoji_map = {"Easy": ":large_green_circle:", "Medium": ":large_yellow_circle:", "Hard": ":red_circle:"}
    emoji = emoji_map.get(difficulty, ":white_circle:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Daily LeetCode Problem — {date}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{link}|#{number} — {title}>*",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Difficulty:*\n{emoji} {difficulty}"},
                {"type": "mrkdwn", "text": f"*Acceptance Rate:*\n{acceptance}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Topics:*\n{tags}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": description},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": ("⚠️ Premium problem." if is_paid else "Good luck! 🚀 Solve it today."),
                }
            ],
        },
    ]
    return blocks


def main():
    client = WebClient(token=SLACK_TOKEN)
    data = fetch_daily_problem()
    blocks = build_message(data)
    client.chat_postMessage(channel=CHANNEL_ID, blocks=blocks, text="Daily LeetCode Problem")
    print(f"Posted: {data['question']['title']}")


if __name__ == "__main__":
    main()
