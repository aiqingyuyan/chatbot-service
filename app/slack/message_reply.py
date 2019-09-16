import requests
import logging
from urllib.parse import urlencode
from slack.environment_vars import BOT_USER_OAUTH_ACCESS_TOKEN


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

slack_api_url = 'https://slack.com/api/chat.postMessage'


def reply_with(message, user, channel):
		args = {
				'token': BOT_USER_OAUTH_ACCESS_TOKEN,
				'channel': channel,
				'text': ' '.join(message).capitalize()
		}

		res = requests.post(slack_api_url, data=args)

		return res
