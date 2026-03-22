import os
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import pytz

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

IST = pytz.timezone("Asia/Kolkata")
client = WebClient(token=SLACK_TOKEN)

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
    }
  }
}
"""


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

    emoji_map = {"Easy": ":large_green_circle:", "Medium": ":large_yellow_circle:", "Hard": ":red_circle:"}
    emoji = emoji_map.get(difficulty, ":white_circle:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":leetcode: Daily LeetCode Problem — {date}",
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


def post_daily_problem():
    try:
        data = fetch_daily_problem()
        blocks = build_message(data)
        client.chat_postMessage(channel=CHANNEL_ID, blocks=blocks, text="Daily LeetCode Problem")
        print(f"Posted daily problem: {data['question']['title']}")
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=IST)
    scheduler.add_job(
        post_daily_problem,
        CronTrigger(hour=11, minute=0, timezone=IST),
    )
    print("Scheduler started — daily problem will post at 11:00 AM IST.")
    post_daily_problem()  # post immediately on startup to verify it works
    scheduler.start()
