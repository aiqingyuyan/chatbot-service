import hashlib
import hmac
import logging
from urllib.parse import urlencode
from slack.environment_vars import SLACK_SIGNING_SECRET


logger = logging.getLogger()
logger.setLevel(logging.WARNING)


def isVerifiedSlackRequest(
		slack_signature=None,
		slack_request_timestamp=None,
		req_body=None
):
		basestr =  str.encode('v0:' + str(slack_request_timestamp) + ':') + req_body
		new_signature = 'v0=' + hmac.new(
				str.encode(SLACK_SIGNING_SECRET),
				basestr,
				hashlib.sha256
		).hexdigest()

		if hmac.compare_digest(new_signature, slack_signature):
				return True
		else:
				logger.warning('Verification failed. new_signature: {my_signature}, slack_signature: {slack_signature}')
				return False
